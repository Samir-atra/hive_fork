"""
Agent Health Monitor - Real-time monitoring and health analysis.

Provides comprehensive health analysis with:
- Real-time watch mode with live metrics streaming
- P95/P99 latency percentiles
- Node-level performance breakdown
- Error rate trends over time
- Webhook notifications on health changes
- Prometheus/StatsD export support
"""

import asyncio
import json
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

import httpx


class HealthStatus(StrEnum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class LatencyMetrics:
    """Latency percentile metrics."""

    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0


@dataclass
class NodeMetrics:
    """Performance metrics for a single node."""

    node_id: str
    node_name: str
    executions: int = 0
    failures: int = 0
    avg_duration_ms: float = 0.0
    success_rate: float = 0.0
    total_tokens: int = 0


@dataclass
class ErrorTrend:
    """Error occurrence trend over time."""

    error_pattern: str
    count: int = 0
    first_seen: str | None = None
    last_seen: str | None = None
    trend: str = "stable"  # "increasing", "decreasing", "stable"


@dataclass
class HealthMetrics:
    """Comprehensive health metrics for an agent."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    recent_runs_24h: int = 0
    recent_success_rate_24h: float = 0.0
    avg_decisions: float = 0.0
    latency: LatencyMetrics = field(default_factory=LatencyMetrics)
    node_metrics: list[NodeMetrics] = field(default_factory=list)
    error_trends: list[ErrorTrend] = field(default_factory=list)
    cost_per_success: float = 0.0
    total_cost: float = 0.0


@dataclass
class HealthReport:
    """Complete health report for an agent."""

    agent_name: str
    status: HealthStatus
    last_run: str | None
    metrics: HealthMetrics
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class HealthThresholds:
    """Configurable health thresholds."""

    SUCCESS_RATE_HEALTHY = 0.90
    SUCCESS_RATE_DEGRADED = 0.80
    RECENT_DEGRADATION_THRESHOLD = 0.15
    HIGH_LATENCY_P95_MS = 30000
    HIGH_COST_THRESHOLD = 1.0
    ERROR_SPIKE_THRESHOLD = 3


class AgentHealthMonitor:
    """
    Real-time agent health monitoring with live updates.

    Features:
    - Historical analysis of agent runs
    - Real-time watch mode with live metrics
    - P95/P99 latency percentiles
    - Node-level performance breakdown
    - Error rate trends over time
    - Webhook notifications on health changes
    - Prometheus-compatible metrics export
    """

    def __init__(
        self,
        agent_path: str | Path,
        webhook_url: str | None = None,
        prometheus_port: int | None = None,
    ):
        self.agent_path = Path(agent_path)
        self.agent_name = self.agent_path.name
        self.webhook_url = webhook_url
        self.prometheus_port = prometheus_port
        self._previous_status: HealthStatus | None = None
        self._watch_callbacks: list[Callable[[HealthReport], None]] = []
        self._stop_watch = asyncio.Event()

        base_path = Path.home() / ".hive" / "agents" / self.agent_name
        self.sessions_dir = base_path / "sessions"
        self.runs_dir = base_path / "runs"

    def analyze(self, days: int = 7) -> HealthReport:
        """
        Analyze agent health over the specified time period.

        Args:
            days: Number of days to analyze

        Returns:
            HealthReport with comprehensive metrics
        """
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_24h = datetime.now() - timedelta(hours=24)

        runs = self._load_runs(cutoff)
        recent_runs = [r for r in runs if self._get_run_timestamp(r) >= cutoff_24h]

        metrics = self._compute_metrics(runs, recent_runs)
        issues = self._identify_issues(metrics, recent_runs)
        recommendations = self._generate_recommendations(metrics, issues)
        status = self._determine_status(metrics, issues)
        alerts = self._generate_alerts(status, metrics)

        last_run = None
        if runs:
            last_run = self._get_run_timestamp(runs[-1]).isoformat()

        report = HealthReport(
            agent_name=self.agent_name,
            status=status,
            last_run=last_run,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations,
            alerts=alerts,
        )

        if self._previous_status and self._previous_status != status:
            self._trigger_status_change(report)

        self._previous_status = status
        return report

    def _load_runs(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Load runs from both new sessions and legacy runs storage."""
        runs = []

        runs_from_sessions = self._load_sessions(cutoff)
        runs.extend(runs_from_sessions)

        legacy_runs = self._load_legacy_runs(cutoff)
        runs.extend(legacy_runs)

        runs.sort(key=lambda r: self._get_run_timestamp(r))
        return runs

    def _load_sessions(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Load runs from new session storage (sessions/*/state.json)."""
        runs = []

        if not self.sessions_dir.exists():
            return runs

        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            state_path = session_dir / "state.json"
            if not state_path.exists():
                continue

            try:
                data = json.loads(state_path.read_text())
                ts = data.get("timestamps", {})
                updated_at = ts.get("updated_at") or ts.get("started_at")
                if updated_at:
                    run_time = datetime.fromisoformat(updated_at)
                    if run_time >= cutoff:
                        runs.append(data)
            except (json.JSONDecodeError, ValueError, KeyError):
                continue

        return runs

    def _load_legacy_runs(self, cutoff: datetime) -> list[dict[str, Any]]:
        """Load runs from legacy runs storage (runs/*.json)."""
        runs = []

        if not self.runs_dir.exists():
            return runs

        for run_file in self.runs_dir.glob("*.json"):
            try:
                data = json.loads(run_file.read_text())
                started_at = data.get("started_at")
                if started_at:
                    if isinstance(started_at, str):
                        run_time = datetime.fromisoformat(started_at)
                    else:
                        run_time = started_at
                    if run_time >= cutoff:
                        runs.append(data)
            except (json.JSONDecodeError, ValueError, KeyError):
                continue

        return runs

    def _get_run_timestamp(self, run: dict[str, Any]) -> datetime:
        """Extract timestamp from a run."""
        ts = run.get("timestamps", {})
        updated = ts.get("updated_at") or ts.get("started_at")
        if updated:
            return datetime.fromisoformat(updated)

        started = run.get("started_at")
        if started:
            if isinstance(started, str):
                return datetime.fromisoformat(started)
            return started

        return datetime.now()

    def _compute_metrics(
        self, runs: list[dict[str, Any]], recent_runs: list[dict[str, Any]]
    ) -> HealthMetrics:
        """Compute comprehensive health metrics."""
        metrics = HealthMetrics()

        if not runs:
            return metrics

        total_runs = len(runs)
        successful = sum(1 for r in runs if self._is_successful(r))
        failed = total_runs - successful

        metrics.total_runs = total_runs
        metrics.successful_runs = successful
        metrics.failed_runs = failed
        metrics.success_rate = successful / total_runs if total_runs > 0 else 0.0

        recent_total = len(recent_runs)
        recent_successful = sum(1 for r in recent_runs if self._is_successful(r))
        metrics.recent_runs_24h = recent_total
        metrics.recent_success_rate_24h = (
            recent_successful / recent_total if recent_total > 0 else 0.0
        )

        metrics.avg_decisions = self._compute_avg_decisions(runs)
        metrics.latency = self._compute_latency_metrics(runs)
        metrics.node_metrics = self._compute_node_metrics(runs)
        metrics.error_trends = self._compute_error_trends(runs)
        metrics.total_cost = self._compute_total_cost(runs)
        metrics.cost_per_success = metrics.total_cost / successful if successful > 0 else 0.0

        return metrics

    def _is_successful(self, run: dict[str, Any]) -> bool:
        """Check if a run was successful."""
        result = run.get("result", {})
        success = result.get("success")

        if success is not None:
            return success

        status = run.get("status", "")
        return status in ("completed", "COMPLETED")

    def _compute_avg_decisions(self, runs: list[dict[str, Any]]) -> float:
        """Compute average decision count."""
        decisions_list = []
        for run in runs:
            metrics = run.get("metrics", {})
            decisions = metrics.get("decision_count", 0)
            if decisions > 0:
                decisions_list.append(decisions)

        return statistics.mean(decisions_list) if decisions_list else 0.0

    def _compute_latency_metrics(self, runs: list[dict[str, Any]]) -> LatencyMetrics:
        """Compute latency percentiles (P50, P95, P99)."""
        latencies = []

        for run in runs:
            progress = run.get("progress", {})
            latency = progress.get("total_latency_ms", 0)

            if latency <= 0:
                latency = run.get("duration_ms", 0)

            if latency > 0:
                latencies.append(latency)

        if not latencies:
            return LatencyMetrics()

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        def percentile(p: float) -> float:
            idx = int(n * p / 100)
            idx = min(idx, n - 1)
            return sorted_latencies[idx]

        return LatencyMetrics(
            avg_ms=statistics.mean(sorted_latencies),
            p50_ms=percentile(50),
            p95_ms=percentile(95),
            p99_ms=percentile(99),
            min_ms=min(sorted_latencies),
            max_ms=max(sorted_latencies),
        )

    def _compute_node_metrics(self, runs: list[dict[str, Any]]) -> list[NodeMetrics]:
        """Compute per-node performance metrics."""
        node_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "executions": 0,
                "failures": 0,
                "durations": [],
                "tokens": 0,
                "name": "",
            }
        )

        for run in runs:
            metrics = run.get("metrics", {})
            nodes_executed = metrics.get("nodes_executed", [])
            progress = run.get("progress", {})
            nodes_with_failures = set(progress.get("nodes_with_failures", []))

            for node_id in nodes_executed:
                node_data[node_id]["executions"] += 1
                if node_id in nodes_with_failures:
                    node_data[node_id]["failures"] += 1
                node_data[node_id]["name"] = node_id

        result = []
        for node_id, data in node_data.items():
            executions = data["executions"]
            failures = data["failures"]
            success_rate = (executions - failures) / executions if executions > 0 else 0.0

            result.append(
                NodeMetrics(
                    node_id=node_id,
                    node_name=data["name"] or node_id,
                    executions=executions,
                    failures=failures,
                    avg_duration_ms=statistics.mean(data["durations"])
                    if data["durations"]
                    else 0.0,
                    success_rate=success_rate,
                    total_tokens=data["tokens"],
                )
            )

        result.sort(key=lambda n: n.executions, reverse=True)
        return result

    def _compute_error_trends(self, runs: list[dict[str, Any]]) -> list[ErrorTrend]:
        """Analyze error patterns and trends over time."""
        error_patterns: dict[str, list[datetime]] = defaultdict(list)

        for run in runs:
            if self._is_successful(run):
                continue

            error = self._extract_error(run)
            if error:
                error_key = self._normalize_error(error)
                ts = self._get_run_timestamp(run)
                error_patterns[error_key].append(ts)

        trends = []
        now = datetime.now()
        half_period = timedelta(days=3.5)

        for pattern, occurrences in error_patterns.items():
            if not occurrences:
                continue

            occurrences.sort()
            first_seen = occurrences[0].isoformat()
            last_seen = occurrences[-1].isoformat()

            recent = [o for o in occurrences if o >= now - half_period]
            older = [o for o in occurrences if o < now - half_period]

            recent_rate = len(recent) / 3.5 if recent else 0
            older_rate = len(older) / 3.5 if older else 0

            if recent_rate > older_rate * 1.5:
                trend = "increasing"
            elif recent_rate < older_rate * 0.67:
                trend = "decreasing"
            else:
                trend = "stable"

            trends.append(
                ErrorTrend(
                    error_pattern=pattern[:100],
                    count=len(occurrences),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    trend=trend,
                )
            )

        trends.sort(key=lambda t: t.count, reverse=True)
        return trends[:10]

    def _extract_error(self, run: dict[str, Any]) -> str | None:
        """Extract error message from a failed run."""
        result = run.get("result", {})
        error = result.get("error")
        if error:
            return str(error)

        problems = run.get("problems", [])
        if problems:
            return problems[0].get("message", str(problems[0]))

        return None

    def _normalize_error(self, error: str) -> str:
        """Normalize error message for pattern matching."""
        import re

        normalized = re.sub(r"\b[0-9a-f]{8,}\b", "<ID>", error)
        normalized = re.sub(r"\b\d+\.\d+\.\d+\.\d+\b", "<IP>", normalized)
        normalized = re.sub(r"\b\d{4,}\b", "<NUM>", normalized)
        return normalized[:200]

    def _compute_total_cost(self, runs: list[dict[str, Any]]) -> float:
        """Compute total cost from runs."""
        total = 0.0
        for run in runs:
            metrics = run.get("metrics", {})
            cost = metrics.get("cost", 0)
            if cost:
                total += float(cost)
        return total

    def _identify_issues(
        self, metrics: HealthMetrics, recent_runs: list[dict[str, Any]]
    ) -> list[str]:
        """Identify health issues based on metrics."""
        issues = []

        if metrics.success_rate < HealthThresholds.SUCCESS_RATE_DEGRADED:
            issues.append(
                f"Low success rate: {metrics.success_rate:.1%} "
                f"(target: >{HealthThresholds.SUCCESS_RATE_DEGRADED:.0%})"
            )

        if metrics.recent_runs_24h >= 3:
            overall_rate = metrics.success_rate
            recent_rate = metrics.recent_success_rate_24h
            degradation = overall_rate - recent_rate

            if degradation > HealthThresholds.RECENT_DEGRADATION_THRESHOLD:
                issues.append(
                    f"Recent degradation: success rate dropped from "
                    f"{overall_rate:.1%} to {recent_rate:.1%}"
                )

        if metrics.latency.p95_ms > HealthThresholds.HIGH_LATENCY_P95_MS:
            issues.append(
                f"High P95 latency: {metrics.latency.p95_ms:.0f}ms "
                f"(threshold: {HealthThresholds.HIGH_LATENCY_P95_MS}ms)"
            )

        increasing_errors = [e for e in metrics.error_trends if e.trend == "increasing"]
        if increasing_errors:
            issues.append(f"Rising error patterns: {len(increasing_errors)} error types increasing")

        problematic_nodes = [
            n for n in metrics.node_metrics if n.success_rate < 0.8 and n.executions >= 3
        ]
        if problematic_nodes:
            node_names = [n.node_id for n in problematic_nodes[:3]]
            issues.append(
                f"Problematic nodes: {', '.join(node_names)}"
                f"{' and others' if len(problematic_nodes) > 3 else ''}"
            )

        return issues

    def _generate_recommendations(self, metrics: HealthMetrics, issues: list[str]) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if metrics.success_rate < HealthThresholds.SUCCESS_RATE_DEGRADED:
            recommendations.append("Review failed runs to identify common failure patterns")
            recommendations.append("Consider improving error handling in agent nodes")

        if metrics.latency.p95_ms > HealthThresholds.HIGH_LATENCY_P95_MS:
            recommendations.append("Investigate slow nodes and consider adding timeouts or caching")

        increasing_errors = [e for e in metrics.error_trends if e.trend == "increasing"]
        if increasing_errors:
            recommendations.append("Address rising error patterns before they escalate")
            for error in increasing_errors[:2]:
                recommendations.append(f"Fix recurring error: {error.error_pattern[:60]}...")

        problematic_nodes = [
            n for n in metrics.node_metrics if n.success_rate < 0.8 and n.executions >= 3
        ]
        if problematic_nodes:
            for node in problematic_nodes[:2]:
                recommendations.append(
                    f"Improve node '{node.node_id}' reliability (current: {node.success_rate:.0%})"
                )

        if not recommendations:
            recommendations.append("Agent is performing well - continue monitoring")

        return recommendations

    def _determine_status(self, metrics: HealthMetrics, issues: list[str]) -> HealthStatus:
        """Determine overall health status."""
        if metrics.total_runs == 0:
            return HealthStatus.UNKNOWN

        critical_issues = [
            i for i in issues if "Low success rate" in i and metrics.success_rate < 0.5
        ]

        if critical_issues or metrics.success_rate < 0.5:
            return HealthStatus.UNHEALTHY

        if metrics.success_rate < HealthThresholds.SUCCESS_RATE_HEALTHY or len(issues) >= 2:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _generate_alerts(self, status: HealthStatus, metrics: HealthMetrics) -> list[str]:
        """Generate alert messages for significant changes."""
        alerts = []

        if self._previous_status is None:
            return alerts

        if status != self._previous_status:
            status_icons = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️",
                HealthStatus.UNHEALTHY: "🚨",
                HealthStatus.UNKNOWN: "❓",
            }
            icon = status_icons.get(status, "")
            alerts.append(
                f"{icon} Health status changed from {self._previous_status.value} to {status.value}"
            )

        return alerts

    async def _trigger_status_change(self, report: HealthReport) -> None:
        """Trigger webhook notification on status change."""
        if self.webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.webhook_url,
                        json={
                            "agent_name": report.agent_name,
                            "status": report.status.value,
                            "previous_status": (
                                self._previous_status.value if self._previous_status else None
                            ),
                            "issues": report.issues,
                            "timestamp": report.timestamp,
                        },
                        timeout=10.0,
                    )
            except Exception:
                pass

    def add_watch_callback(self, callback: Callable[[HealthReport], None]) -> None:
        """Add a callback for watch mode updates."""
        self._watch_callbacks.append(callback)

    async def watch(
        self,
        interval: float = 5.0,
        days: int = 7,
        on_update: Callable[[HealthReport], None] | None = None,
    ) -> None:
        """
        Start real-time watch mode with live updates.

        Args:
            interval: Update interval in seconds
            days: Number of days to analyze
            on_update: Optional callback for each update
        """
        self._stop_watch.clear()

        print(f"\n🔍 Watching agent: {self.agent_name}")
        print(f"   Update interval: {interval}s")
        print(f"   Analysis window: {days} days")
        print("   Press Ctrl+C to stop\n")

        try:
            while not self._stop_watch.is_set():
                report = self.analyze(days)

                self._display_report(report, live=True)

                if on_update:
                    on_update(report)

                for callback in self._watch_callbacks:
                    try:
                        callback(report)
                    except Exception:
                        pass

                try:
                    await asyncio.wait_for(self._stop_watch.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass

        except KeyboardInterrupt:
            print("\n\nWatch mode stopped.")

    def stop_watch(self) -> None:
        """Stop watch mode."""
        self._stop_watch.set()

    def _display_report(self, report: HealthReport, live: bool = False) -> None:
        """Display health report in terminal."""
        if live:
            print("\033[2J\033[H", end="")

        status_icons = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNHEALTHY: "🚨",
            HealthStatus.UNKNOWN: "❓",
        }

        icon = status_icons.get(report.status, "")
        print("=" * 60)
        print(f"Agent Health Report: {report.agent_name}")
        print("=" * 60)
        print()
        print(f"Status: {icon} {report.status.value.upper()}")
        print(f"Last Run: {report.last_run or 'N/A'}")
        if live:
            print(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

        m = report.metrics
        print()
        print("Metrics:")
        print(f"  Total Runs: {m.total_runs}")
        print(f"  Successful: {m.successful_runs}")
        print(f"  Failed: {m.failed_runs}")
        print(f"  Success Rate: {m.success_rate:.1%}")
        print(f"  Recent (24h): {m.recent_runs_24h} runs, {m.recent_success_rate_24h:.1%} success")
        print(f"  Avg Decisions: {m.avg_decisions:.1f}")

        print()
        print("Latency:")
        print(f"  Avg: {m.latency.avg_ms:.0f}ms")
        print(f"  P50: {m.latency.p50_ms:.0f}ms")
        print(f"  P95: {m.latency.p95_ms:.0f}ms")
        print(f"  P99: {m.latency.p99_ms:.0f}ms")

        if m.node_metrics:
            print()
            print("Top Nodes by Executions:")
            for node in m.node_metrics[:5]:
                status = (
                    "✓" if node.success_rate >= 0.9 else "⚠" if node.success_rate >= 0.7 else "✗"
                )
                print(
                    f"  {status} {node.node_id}: {node.executions} runs, "
                    f"{node.success_rate:.0%} success"
                )

        if m.error_trends:
            print()
            print("Error Trends:")
            for trend in m.error_trends[:5]:
                trend_icon = (
                    "📈"
                    if trend.trend == "increasing"
                    else "📉"
                    if trend.trend == "decreasing"
                    else "➡️"
                )
                print(f"  {trend_icon} {trend.count}x: {trend.error_pattern[:50]}...")

        if report.issues:
            print()
            print("Issues:")
            for issue in report.issues:
                print(f"  ⚠️  {issue}")

        if report.alerts:
            print()
            print("Alerts:")
            for alert in report.alerts:
                print(f"  🔔 {alert}")

        if report.recommendations:
            print()
            print("Recommendations:")
            for rec in report.recommendations:
                print(f"  • {rec}")

        print()

    def to_json(self, report: HealthReport) -> str:
        """Export health report as JSON."""
        return json.dumps(
            {
                "agent_name": report.agent_name,
                "status": report.status.value,
                "last_run": report.last_run,
                "timestamp": report.timestamp,
                "metrics": {
                    "total_runs": report.metrics.total_runs,
                    "successful_runs": report.metrics.successful_runs,
                    "failed_runs": report.metrics.failed_runs,
                    "success_rate": report.metrics.success_rate,
                    "recent_runs_24h": report.metrics.recent_runs_24h,
                    "recent_success_rate_24h": report.metrics.recent_success_rate_24h,
                    "avg_decisions": report.metrics.avg_decisions,
                    "latency": {
                        "avg_ms": report.metrics.latency.avg_ms,
                        "p50_ms": report.metrics.latency.p50_ms,
                        "p95_ms": report.metrics.latency.p95_ms,
                        "p99_ms": report.metrics.latency.p99_ms,
                        "min_ms": report.metrics.latency.min_ms,
                        "max_ms": report.metrics.latency.max_ms,
                    },
                    "node_metrics": [
                        {
                            "node_id": n.node_id,
                            "node_name": n.node_name,
                            "executions": n.executions,
                            "failures": n.failures,
                            "avg_duration_ms": n.avg_duration_ms,
                            "success_rate": n.success_rate,
                            "total_tokens": n.total_tokens,
                        }
                        for n in report.metrics.node_metrics
                    ],
                    "error_trends": [
                        {
                            "error_pattern": e.error_pattern,
                            "count": e.count,
                            "first_seen": e.first_seen,
                            "last_seen": e.last_seen,
                            "trend": e.trend,
                        }
                        for e in report.metrics.error_trends
                    ],
                    "cost_per_success": report.metrics.cost_per_success,
                    "total_cost": report.metrics.total_cost,
                },
                "issues": report.issues,
                "recommendations": report.recommendations,
                "alerts": report.alerts,
            },
            indent=2,
        )

    def to_prometheus(self, report: HealthReport) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        prefix = "hive_agent"

        lines.append(
            f"# HELP {prefix}_health_status Agent health status (0=unknown, 1=healthy, 2=degraded, 3=unhealthy)"
        )
        lines.append(f"# TYPE {prefix}_health_status gauge")
        status_values = {
            HealthStatus.UNKNOWN: 0,
            HealthStatus.HEALTHY: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.UNHEALTHY: 3,
        }
        lines.append(
            f'{prefix}_health_status{{agent="{report.agent_name}"}} '
            f"{status_values.get(report.status, 0)}"
        )

        m = report.metrics
        metrics_to_export = [
            ("total_runs", m.total_runs),
            ("successful_runs", m.successful_runs),
            ("failed_runs", m.failed_runs),
            ("success_rate", m.success_rate),
            ("recent_runs_24h", m.recent_runs_24h),
            ("recent_success_rate_24h", m.recent_success_rate_24h),
            ("avg_decisions", m.avg_decisions),
            ("latency_avg_ms", m.latency.avg_ms),
            ("latency_p50_ms", m.latency.p50_ms),
            ("latency_p95_ms", m.latency.p95_ms),
            ("latency_p99_ms", m.latency.p99_ms),
            ("total_cost", m.total_cost),
            ("cost_per_success", m.cost_per_success),
        ]

        for name, value in metrics_to_export:
            lines.append(f"# TYPE {prefix}_{name} gauge")
            lines.append(f'{prefix}_{name}{{agent="{report.agent_name}"}} {value}')

        for node in m.node_metrics[:10]:
            labels = f'agent="{report.agent_name}",node="{node.node_id}"'
            lines.append(f"# TYPE {prefix}_node_executions gauge")
            lines.append(f"{prefix}_node_executions{{{labels}}} {node.executions}")
            lines.append(f"# TYPE {prefix}_node_success_rate gauge")
            lines.append(f"{prefix}_node_success_rate{{{labels}}} {node.success_rate}")

        return "\n".join(lines)


async def send_webhook(
    webhook_url: str, report: HealthReport, previous_status: HealthStatus | None
) -> bool:
    """Send webhook notification for health status change."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={
                    "agent_name": report.agent_name,
                    "status": report.status.value,
                    "previous_status": previous_status.value if previous_status else None,
                    "issues": report.issues,
                    "timestamp": report.timestamp,
                    "metrics_summary": {
                        "success_rate": report.metrics.success_rate,
                        "total_runs": report.metrics.total_runs,
                        "recent_success_rate": report.metrics.recent_success_rate_24h,
                    },
                },
                timeout=10.0,
            )
            return response.status_code < 400
    except Exception:
        return False
