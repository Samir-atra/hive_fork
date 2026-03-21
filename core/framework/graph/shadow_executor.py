"""
Shadow Executor - Runs two graphs in parallel and compares their outputs.

This allows safe graph evolution by testing a candidate graph against a baseline
using the same inputs, then evaluating both outcomes before deciding whether
to promote the candidate.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.graph.goal import Goal
from framework.llm.provider import LLMProvider
from framework.runtime.core import Runtime

logger = logging.getLogger(__name__)


@dataclass
class ShadowComparisonResult:
    """Result of a shadow mode comparison between two graphs."""

    winner: str  # "baseline", "candidate", or "tie"
    should_promote: bool
    baseline_result: ExecutionResult
    candidate_result: ExecutionResult
    metrics: dict[str, Any] = field(default_factory=dict)


class VersionComparator:
    """Evaluates two execution results against a goal to determine a winner."""

    def __init__(self, llm: LLMProvider, goal: Goal) -> None:
        """Initialize the VersionComparator.

        Args:
            llm: LLM provider for evaluating execution quality
            goal: The goal both graphs were trying to achieve
        """
        self._llm = llm
        self._goal = goal

    async def compare(
        self, baseline_result: ExecutionResult, candidate_result: ExecutionResult
    ) -> dict[str, Any]:
        """Compare the two results and calculate metrics.

        Args:
            baseline_result: The result from the baseline graph
            candidate_result: The result from the candidate graph

        Returns:
            A dictionary containing the comparison metrics, including 'winner'
        """
        metrics = {
            "baseline_success": baseline_result.success,
            "candidate_success": candidate_result.success,
            "baseline_tokens": baseline_result.total_tokens,
            "candidate_tokens": candidate_result.total_tokens,
            "baseline_latency": baseline_result.total_latency_ms,
            "candidate_latency": candidate_result.total_latency_ms,
        }

        # 1. Hard failure check
        if baseline_result.success and not candidate_result.success:
            metrics["winner"] = "baseline"
            metrics["reason"] = "Candidate failed to complete successfully"
            return metrics

        if candidate_result.success and not baseline_result.success:
            metrics["winner"] = "candidate"
            metrics["reason"] = "Candidate succeeded while baseline failed"
            return metrics

        if not baseline_result.success and not candidate_result.success:
            metrics["winner"] = "tie"
            metrics["reason"] = "Both graphs failed"
            return metrics

        # 2. Quality evaluation using LLM
        system_prompt = (
            "You are an impartial judge evaluating the output of two different versions "
            "of an AI agent graph. Your task is to determine which version better achieved "
            "the provided goal and success criteria."
        )

        user_prompt = f"""Compare the outputs of two agent versions.

GOAL: {self._goal.name}
DESCRIPTION: {self._goal.description}
SUCCESS CRITERIA:
{self._goal.to_prompt_context()}

BASELINE OUTPUT:
{baseline_result.output}

CANDIDATE OUTPUT:
{candidate_result.output}

Based on the goal and success criteria, which output is better?
Respond in exactly this format:
WINNER: BASELINE or CANDIDATE or TIE
REASON: (brief explanation of your choice)"""

        try:
            response = await self._llm.acomplete(
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                max_tokens=500,
                max_retries=1,
            )
            content = response.content or ""
            winner_str = "TIE"
            reason_str = "No specific reason provided"

            for line in content.strip().split("\n"):
                line = line.strip()
                if line.startswith("WINNER:"):
                    winner_str = line.split(":", 1)[1].strip().upper()
                elif line.startswith("REASON:"):
                    reason_str = line.split(":", 1)[1].strip()

            if winner_str in ("BASELINE", "CANDIDATE", "TIE"):
                metrics["winner"] = winner_str.lower()
                metrics["reason"] = reason_str
            else:
                metrics["winner"] = "tie"
                metrics["reason"] = "Could not parse judge verdict"

        except Exception as e:
            logger.warning(f"Version comparison failed during LLM evaluation: {e}")
            metrics["winner"] = "tie"
            metrics["reason"] = "LLM evaluation failed"

        # 3. Tie-breaker based on tokens/latency
        if metrics.get("winner") == "tie":
            if candidate_result.total_tokens < baseline_result.total_tokens * 0.9:
                metrics["winner"] = "candidate"
                metrics["reason"] = "Tie-breaker: Candidate uses significantly fewer tokens"
            elif candidate_result.total_latency_ms < baseline_result.total_latency_ms * 0.9:
                metrics["winner"] = "candidate"
                metrics["reason"] = "Tie-breaker: Candidate is significantly faster"
            elif baseline_result.total_tokens < candidate_result.total_tokens * 0.9:
                metrics["winner"] = "baseline"
                metrics["reason"] = "Tie-breaker: Baseline uses significantly fewer tokens"

        return metrics


class ShadowExecutor:
    """Runs a candidate graph alongside a baseline graph for safe evolution.

    Both graphs are executed concurrently in completely isolated states with
    the exact same input. Their results are then compared using a VersionComparator.
    """

    def __init__(
        self,
        baseline: GraphSpec,
        candidate: GraphSpec,
        llm: LLMProvider,
        runtime: Runtime,
        confidence_threshold: float = 0.8,
    ) -> None:
        """Initialize the ShadowExecutor.

        Args:
            baseline: The current, proven GraphSpec
            candidate: The new, evolving GraphSpec
            llm: LLM provider for evaluation
            runtime: The runtime providing state, isolation, and observability
            confidence_threshold: Not currently used directly by LLM judge, but reserved
                                  for future scoring thresholds (e.g. 0.8 to promote)
        """
        self._baseline = baseline
        self._candidate = candidate
        self._llm = llm
        self._runtime = runtime
        self._confidence_threshold = confidence_threshold

    async def execute(
        self,
        goal: Goal,
        input_data: dict[str, Any] | None = None,
        session_state: dict[str, Any] | None = None,
    ) -> ShadowComparisonResult:
        """Execute both graphs and compare their outcomes.

        Args:
            goal: The Goal driving the execution
            input_data: The identical input provided to both graphs
            session_state: Initial shared state data

        Returns:
            A ShadowComparisonResult detailing the outcome of the comparison
        """
        # Create separate executors. Note that GraphExecutor enforces ISOLATED state
        # correctly so long as each gets its own unique stream_id.
        baseline_executor = GraphExecutor(
            runtime=self._runtime,
            llm=self._llm,
            stream_id="shadow_baseline",
        )

        candidate_executor = GraphExecutor(
            runtime=self._runtime,
            llm=self._llm,
            stream_id="shadow_candidate",
        )

        # Run both simultaneously
        baseline_task = baseline_executor.execute(
            graph=self._baseline,
            goal=goal,
            input_data=input_data,
            session_state=session_state,
        )

        candidate_task = candidate_executor.execute(
            graph=self._candidate,
            goal=goal,
            input_data=input_data,
            session_state=session_state,
        )

        baseline_result, candidate_result = await asyncio.gather(baseline_task, candidate_task)

        # Compare outputs
        comparator = VersionComparator(llm=self._llm, goal=goal)
        metrics = await comparator.compare(baseline_result, candidate_result)

        winner = metrics.get("winner", "tie")

        # In this implementation, candidate must clearly win to be promoted
        should_promote = winner == "candidate"

        result = ShadowComparisonResult(
            winner=winner,
            should_promote=should_promote,
            baseline_result=baseline_result,
            candidate_result=candidate_result,
            metrics=metrics,
        )

        # Emit the shadow comparison event to the EventBus
        if hasattr(self._runtime, "event_bus") and self._runtime.event_bus:
            await self._runtime.event_bus.emit_shadow_comparison_completed(
                baseline_graph_id=self._baseline.id,
                candidate_graph_id=self._candidate.id,
                winner=result.winner,
                should_promote=result.should_promote,
                metrics=result.metrics,
            )

        return result
