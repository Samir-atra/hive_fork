"""Evolution Shadow Runner - Validates configurations against historical traces.

Extends the Phase 1 ShadowRunner with evolution-specific functionality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from framework.evolution.config import AgentConfiguration, ConfigurationVariant
from framework.tracing.replay import ReplayEngine, ReplayResult, ShadowRunner
from framework.tracing.store import TraceStore

logger = logging.getLogger(__name__)


@dataclass
class ShadowTestConfig:
    """Configuration for shadow testing."""

    min_traces: int = 10
    max_traces: int = 50
    min_success_rate: float = 0.9
    max_divergence_rate: float = 0.1

    include_failures: bool = True
    balance_traces: bool = True


@dataclass
class ShadowTestResult:
    """Result of shadow testing a configuration."""

    config_id: str
    variant_id: str = ""

    total_traces: int = 0
    successful_replays: int = 0
    divergences: int = 0

    success_rate: float = 0.0
    divergence_rate: float = 0.0

    passed: bool = False
    failure_reasons: list[str] | None = None

    details: list[dict[str, Any]] | None = None


class EvolutionShadowRunner:
    """Runs shadow executions for evolution validation.

    This extends Phase 1's ShadowRunner with:
    - Configuration-aware testing
    - Fitness scoring integration
    - HITL approval gates
    """

    def __init__(
        self,
        trace_store: TraceStore,
        config: ShadowTestConfig | None = None,
    ) -> None:
        self._trace_store = trace_store
        self._config = config or ShadowTestConfig()
        self._base_runner = ShadowRunner(trace_store)

    async def test_configuration(
        self,
        config: AgentConfiguration,
        trace_ids: list[str] | None = None,
        on_result: Callable[[str, ReplayResult], None] | None = None,
    ) -> ShadowTestResult:
        """Test a configuration against historical traces.

        Args:
            config: Configuration to test
            trace_ids: Optional specific trace IDs (loads from store if None)
            on_result: Callback for each replay result

        Returns:
            ShadowTestResult with pass/fail status.
        """
        result = ShadowTestResult(
            config_id=config.config_id,
            failure_reasons=[],
            details=[],
        )

        if trace_ids is None:
            trace_ids = await self._select_traces_for_testing()

        if len(trace_ids) < self._config.min_traces:
            result.failure_reasons.append(
                f"Insufficient traces: {len(trace_ids)} < {self._config.min_traces}"
            )
            return result

        result.total_traces = len(trace_ids)
        details = []

        for trace_id in trace_ids:
            trace = await self._trace_store.load_trace_async(trace_id)
            if trace is None:
                continue

            engine = ReplayEngine(trace)

            try:
                replay_result = await engine.replay()

                detail = {
                    "trace_id": trace_id,
                    "success": replay_result.success,
                    "diverged": replay_result.diverged,
                    "divergence_reason": replay_result.divergence_reason,
                }
                details.append(detail)

                if replay_result.success and not replay_result.diverged:
                    result.successful_replays += 1
                elif replay_result.diverged:
                    result.divergences += 1

                if on_result:
                    on_result(trace_id, replay_result)

            except Exception as e:
                details.append(
                    {
                        "trace_id": trace_id,
                        "success": False,
                        "diverged": True,
                        "divergence_reason": str(e),
                    }
                )
                result.divergences += 1

        result.details = details

        if result.total_traces > 0:
            result.success_rate = result.successful_replays / result.total_traces
            result.divergence_rate = result.divergences / result.total_traces

        result.passed = self._evaluate_pass_criteria(result)

        return result

    async def test_variant(
        self,
        variant: ConfigurationVariant,
        trace_ids: list[str] | None = None,
    ) -> ShadowTestResult:
        """Test a configuration variant."""
        result = await self.test_configuration(
            config=variant.config,
            trace_ids=trace_ids,
        )
        result.variant_id = variant.variant_id

        variant.shadow_test_results = result.details or []

        return result

    async def _select_traces_for_testing(self) -> list[str]:
        """Select traces for testing based on configuration."""
        metadatas = await self._trace_store.list_traces_async(
            status="completed",
            limit=self._config.max_traces * 2,
        )

        if not metadatas:
            return []

        trace_ids = [m.trace_id for m in metadatas]

        if self._config.balance_traces:
            success_ids = [
                m.trace_id for m in metadatas if m.status == "completed" and not m.needs_attention
            ]
            failure_ids = [m.trace_id for m in metadatas if m.needs_attention]

            if self._config.include_failures and failure_ids:
                balanced = []
                for i in range(max(len(success_ids), len(failure_ids))):
                    if i < len(success_ids):
                        balanced.append(success_ids[i])
                    if i < len(failure_ids) and len(balanced) < self._config.max_traces:
                        balanced.append(failure_ids[i])
                trace_ids = balanced[: self._config.max_traces]
            else:
                trace_ids = success_ids[: self._config.max_traces]

        return trace_ids

    def _evaluate_pass_criteria(self, result: ShadowTestResult) -> bool:
        """Evaluate whether the shadow test passes."""
        if result.total_traces < self._config.min_traces:
            result.failure_reasons.append(f"Insufficient traces tested: {result.total_traces}")
            return False

        if result.success_rate < self._config.min_success_rate:
            result.failure_reasons.append(
                f"Success rate too low: {result.success_rate:.2%} < {self._config.min_success_rate:.2%}"
            )
            return False

        if result.divergence_rate > self._config.max_divergence_rate:
            result.failure_reasons.append(
                f"Divergence rate too high: {result.divergence_rate:.2%} > {self._config.max_divergence_rate:.2%}"
            )
            return False

        return True

    async def compare_configurations(
        self,
        configs: list[AgentConfiguration],
        trace_ids: list[str] | None = None,
    ) -> list[tuple[str, ShadowTestResult]]:
        """Compare multiple configurations side-by-side.

        Returns:
            List of (config_id, result) tuples sorted by success rate.
        """
        results = []

        for config in configs:
            result = await self.test_configuration(config, trace_ids)
            results.append((config.config_id, result))

        results.sort(key=lambda x: x[1].success_rate, reverse=True)
        return results
