import logging
from collections.abc import AsyncIterator
from typing import Any

from framework.graph.node import NodeContext, NodeSpec
from framework.llm.litellm import LiteLLMProvider
from framework.llm.router.constraint_evaluator import ConstraintEvaluator, Constraints
from framework.llm.router.fallback_chain import FallbackChainBuilder
from framework.llm.router.model_registry import ModelRegistry
from framework.llm.router.routing_metrics import RoutingMetricsLogger
from framework.llm.router.task_classifier import TaskClassifier
from framework.llm.stream_events import StreamErrorEvent, StreamEvent

logger = logging.getLogger(__name__)


class MultiModelRouterNode:
    """A task-aware multi-model router node.

    This node classifies tasks and routes requests to the optimal LLM
    (balancing cost, speed, and capability) without using an LLM for the
    routing decision itself.

    If a primary model fails, it retries with the next option in the chain.
    """

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        classifier: TaskClassifier | None = None,
        evaluator: ConstraintEvaluator | None = None,
        metrics_logger: RoutingMetricsLogger | None = None,
    ) -> None:
        """Initialize the multi-model router node."""
        self.registry = registry or ModelRegistry()
        self.classifier = classifier or TaskClassifier()
        self.evaluator = evaluator or ConstraintEvaluator()
        self.metrics_logger = metrics_logger or RoutingMetricsLogger()
        self.fallback_builder = FallbackChainBuilder(self.registry, self.evaluator)

    def _determine_fallback_chain(
        self,
        prompt: str | list,
        constraints: Constraints,
        preferred_tier: str,
        force_model: str | None,
    ) -> tuple[str, list[str], list[dict[str, str]]]:
        """Determine the fallback chain of models to use.

        Returns:
            A tuple of (task_category, model_chain, rejected_candidates).
        """
        task_category = self.classifier.classify(prompt)

        # Build fallback chain
        model_chain: list[str] = []
        rejected: list[dict[str, str]] = []

        if force_model:
            model_chain = [force_model]
        else:
            # Re-evaluate all candidate models across all tiers
            # so we can track exact rejection reasons for top-2 metrics
            candidates = self.registry._profiles.values()

            for candidate in candidates:
                # Require task capability for consideration if it's not general
                if task_category != "general" and task_category not in candidate.capabilities:
                    rejected.append(
                        {
                            "model": candidate.name,
                            "reason": f"Missing required capability: {task_category}",
                        }
                    )
                    continue

                is_valid, reason = self.evaluator.evaluate(candidate, constraints)
                if not is_valid and reason:
                    rejected.append({"model": candidate.name, "reason": reason})

            # Build exact chain order via fallback builder
            profiles = self.fallback_builder.build_chain(task_category, constraints, preferred_tier)
            model_chain = [p.name for p in profiles]

        # Ensure we have at least one fallback
        if not model_chain and not force_model:
            logger.warning("[router] No models met constraints, falling back to gpt-3.5-turbo.")
            model_chain = ["gpt-3.5-turbo"]

        return task_category, model_chain, rejected

    async def execute(
        self,
        ctx: NodeContext,
        spec: NodeSpec,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        constraints: Constraints | None = None,
        preferred_tier: str = "balanced",
        force_model: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """Execute the multi-model routing and streaming process.

        This method acts as a drop-in streaming equivalent for the `LiteLLMProvider`.
        It iterates over the fallback chain in case of model failure.

        Args:
            ctx: Execution context containing event_bus.
            spec: The node spec executing the operation.
            messages: Conversation messages.
            system: System prompt.
            tools: Available tools.
            constraints: Budget, latency, context constraints.
            preferred_tier: Default preferred tier ('simple', 'balanced', 'premium').
            force_model: Explicit override model.
            **kwargs: Additional args passed to `LiteLLMProvider`.

        Yields:
            StreamEvents (TextDelta, ToolCall, FinishEvent, etc.).
        """
        constraints = constraints or Constraints()

        # Determine the user prompt for classification
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

        task_category, model_chain, rejected = self._determine_fallback_chain(
            last_user_msg, constraints, preferred_tier, force_model
        )

        # Attach event bus to metrics logger if present
        if ctx.event_bus and not self.metrics_logger.event_bus:
            self.metrics_logger.event_bus = ctx.event_bus

        self.metrics_logger.log_decision(
            node_id=spec.id,
            task_category=task_category,
            selected_model=model_chain[0] if model_chain else "unknown",
            rejected_candidates=rejected,
            fallback_chain=model_chain,
        )

        # Execute fallback sequence
        for i, model in enumerate(model_chain):
            provider = LiteLLMProvider(model=model)
            logger.info(f"[router] Attempting execution with model: {model}")

            try:
                stream = provider.stream(messages=messages, system=system, tools=tools, **kwargs)

                success = True
                async for event in stream:
                    if isinstance(event, StreamErrorEvent) and not event.recoverable:
                        logger.error(
                            f"[router] Model {model} encountered fatal stream error: {event.error}"
                        )
                        success = False
                        break  # break the inner event loop to retry outer fallback
                    elif isinstance(event, StreamErrorEvent) and event.recoverable:
                        logger.warning(
                            f"[router] Model {model} encountered recoverable "
                            f"stream error: {event.error}"
                        )
                        success = False
                        break  # Break to fallback, DO NOT yield the error to the client
                    yield event

                if success:
                    # Successful generation, return early
                    return

            except Exception as e:
                logger.error(f"[router] Exception during execution with {model}: {e}")
                # We catch exceptions to allow the fallback to the next model in chain

            if i < len(model_chain) - 1:
                logger.info(f"[router] Falling back to next model: {model_chain[i + 1]}")
            else:
                logger.error("[router] All fallback models exhausted.")
                yield StreamErrorEvent(error="All fallback models exhausted.", recoverable=False)
