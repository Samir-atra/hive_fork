"""Tests for agent health monitoring."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framework.runner.agent_health import (
    AgentHealthMonitor,
    ErrorTrend,
    HealthMetrics,
    HealthReport,
    HealthStatus,
    HealthThresholds,
    LatencyMetrics,
    NodeMetrics,
    send_webhook,
)


@pytest.fixture
def temp_agent_dir():
    """Create a temporary agent directory with mock session data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_path = Path(tmpdir) / "test_agent"
        agent_path.mkdir(parents=True)

        hive_base = Path.home() / ".hive" / "agents" / "test_agent"
        sessions_dir = hive_base / "sessions"
        runs_dir = hive_base / "runs"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        runs_dir.mkdir(parents=True, exist_ok=True)

        yield agent_path, sessions_dir, runs_dir


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestLatencyMetrics:
    """Tests for LatencyMetrics dataclass."""

    def test_default_values(self):
        metrics = LatencyMetrics()
        assert metrics.avg_ms == 0.0
        assert metrics.p50_ms == 0.0
        assert metrics.p95_ms == 0.0
        assert metrics.p99_ms == 0.0
        assert metrics.min_ms == 0.0
        assert metrics.max_ms == 0.0

    def test_custom_values(self):
        metrics = LatencyMetrics(
            avg_ms=100.0,
            p50_ms=80.0,
            p95_ms=200.0,
            p99_ms=300.0,
            min_ms=50.0,
            max_ms=400.0,
        )
        assert metrics.avg_ms == 100.0
        assert metrics.p95_ms == 200.0
        assert metrics.p99_ms == 300.0


class TestNodeMetrics:
    """Tests for NodeMetrics dataclass."""

    def test_default_values(self):
        metrics = NodeMetrics(node_id="test_node", node_name="Test Node")
        assert metrics.node_id == "test_node"
        assert metrics.executions == 0
        assert metrics.failures == 0
        assert metrics.success_rate == 0.0

    def test_success_rate_calculation(self):
        metrics = NodeMetrics(
            node_id="test_node",
            node_name="Test Node",
            executions=10,
            failures=2,
        )
        assert metrics.success_rate == 0.8


class TestHealthMetrics:
    """Tests for HealthMetrics dataclass."""

    def test_default_values(self):
        metrics = HealthMetrics()
        assert metrics.total_runs == 0
        assert metrics.success_rate == 0.0
        assert metrics.latency.avg_ms == 0.0
        assert len(metrics.node_metrics) == 0
        assert len(metrics.error_trends) == 0


class TestHealthReport:
    """Tests for HealthReport dataclass."""

    def test_health_report_creation(self):
        metrics = HealthMetrics()
        report = HealthReport(
            agent_name="test_agent",
            status=HealthStatus.HEALTHY,
            last_run="2026-01-26T12:00:00",
            metrics=metrics,
        )
        assert report.agent_name == "test_agent"
        assert report.status == HealthStatus.HEALTHY
        assert len(report.issues) == 0
        assert len(report.recommendations) == 0


class TestAgentHealthMonitor:
    """Tests for AgentHealthMonitor class."""

    def test_init(self, temp_agent_dir):
        agent_path, sessions_dir, runs_dir = temp_agent_dir
        monitor = AgentHealthMonitor(agent_path)
        assert monitor.agent_name == "test_agent"
        assert monitor.sessions_dir == sessions_dir
        assert monitor.runs_dir == runs_dir

    def test_analyze_no_runs(self, temp_agent_dir):
        agent_path, _, _ = temp_agent_dir
        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert report.status == HealthStatus.UNKNOWN
        assert report.metrics.total_runs == 0

    def test_analyze_with_sessions(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        session_dir = sessions_dir / "session_20260126_120000_abc12345"
        session_dir.mkdir(parents=True)

        now = datetime.now()
        session_data = {
            "session_id": "session_20260126_120000_abc12345",
            "goal_id": "test_goal",
            "status": "completed",
            "timestamps": {
                "started_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "completed_at": now.isoformat(),
            },
            "result": {"success": True, "output": {}},
            "progress": {
                "steps_executed": 5,
                "total_latency_ms": 1000,
                "total_tokens": 100,
            },
            "metrics": {
                "decision_count": 3,
                "nodes_executed": ["node1", "node2"],
            },
        }
        (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert report.metrics.total_runs == 1
        assert report.metrics.successful_runs == 1
        assert report.metrics.success_rate == 1.0

    def test_analyze_with_legacy_runs(self, temp_agent_dir):
        agent_path, _, runs_dir = temp_agent_dir

        now = datetime.now()
        run_data = {
            "run_id": "run_001",
            "goal_id": "test_goal",
            "started_at": now.isoformat(),
            "status": "COMPLETED",
            "output_data": {"result": "success"},
        }
        (runs_dir / "run_001.json").write_text(json.dumps(run_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert report.metrics.total_runs == 1
        assert report.metrics.successful_runs == 1

    def test_compute_latency_percentiles(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        for i, latency in enumerate(latencies):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now()
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "completed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": True},
                "progress": {"total_latency_ms": latency},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert report.metrics.latency.p50_ms > 0
        assert report.metrics.latency.p95_ms >= report.metrics.latency.p50_ms
        assert report.metrics.latency.p99_ms >= report.metrics.latency.p95_ms

    def test_status_determination_healthy(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        for i in range(10):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now()
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "completed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": True},
                "progress": {"total_latency_ms": 100},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert report.status == HealthStatus.HEALTHY
        assert report.metrics.success_rate == 1.0

    def test_status_determination_degraded(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        for i in range(10):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now()
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "completed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": i < 8},
                "progress": {"total_latency_ms": 100},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert report.status == HealthStatus.DEGRADED
        assert report.metrics.success_rate == 0.8

    def test_status_determination_unhealthy(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        for i in range(10):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now()
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "failed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": i < 3},
                "progress": {"total_latency_ms": 100},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert report.status == HealthStatus.UNHEALTHY
        assert report.metrics.success_rate == 0.3

    def test_node_metrics(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        for i in range(5):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now()
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "completed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": True},
                "progress": {"total_latency_ms": 100, "nodes_with_failures": []},
                "metrics": {"nodes_executed": ["node1", "node2"]},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert len(report.metrics.node_metrics) == 2
        node_ids = [n.node_id for n in report.metrics.node_metrics]
        assert "node1" in node_ids
        assert "node2" in node_ids

    def test_error_trends(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        for i in range(5):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now() - timedelta(days=i)
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "failed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": False, "error": f"Error: Connection timeout (ID: abc123)"},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert len(report.metrics.error_trends) >= 1

    def test_to_json(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        session_dir = sessions_dir / "session_001"
        session_dir.mkdir(parents=True)
        now = datetime.now()
        session_data = {
            "session_id": "session_001",
            "goal_id": "test_goal",
            "status": "completed",
            "timestamps": {
                "started_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
            "result": {"success": True},
            "progress": {"total_latency_ms": 100},
        }
        (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)
        json_output = monitor.to_json(report)

        parsed = json.loads(json_output)
        assert parsed["agent_name"] == "test_agent"
        assert parsed["status"] == "healthy"
        assert "metrics" in parsed
        assert "latency" in parsed["metrics"]

    def test_to_prometheus(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        session_dir = sessions_dir / "session_001"
        session_dir.mkdir(parents=True)
        now = datetime.now()
        session_data = {
            "session_id": "session_001",
            "goal_id": "test_goal",
            "status": "completed",
            "timestamps": {
                "started_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
            "result": {"success": True},
            "progress": {"total_latency_ms": 100},
        }
        (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)
        prom_output = monitor.to_prometheus(report)

        assert "hive_agent_health_status" in prom_output
        assert "hive_agent_total_runs" in prom_output
        assert "hive_agent_success_rate" in prom_output
        assert "hive_agent_latency_p95_ms" in prom_output
        assert 'agent="test_agent"' in prom_output

    def test_identify_issues_low_success_rate(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        for i in range(10):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now()
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "completed" if i < 5 else "failed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": i < 5},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert any("Low success rate" in issue for issue in report.issues)

    def test_identify_issues_high_latency(self, temp_agent_dir):
        agent_path, sessions_dir, _ = temp_agent_dir

        for i in range(10):
            session_dir = sessions_dir / f"session_{i:03d}"
            session_dir.mkdir(parents=True)
            now = datetime.now()
            session_data = {
                "session_id": f"session_{i:03d}",
                "goal_id": "test_goal",
                "status": "completed",
                "timestamps": {
                    "started_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "result": {"success": True},
                "progress": {"total_latency_ms": 40000},
            }
            (session_dir / "state.json").write_text(json.dumps(session_data))

        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        assert any("High P95 latency" in issue for issue in report.issues)


class TestSendWebhook:
    """Tests for webhook notification functionality."""

    @pytest.mark.asyncio
    async def test_send_webhook_success(self, temp_agent_dir):
        agent_path, _, _ = temp_agent_dir
        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await send_webhook("https://example.com/webhook", report, HealthStatus.HEALTHY)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_webhook_failure(self, temp_agent_dir):
        agent_path, _, _ = temp_agent_dir
        monitor = AgentHealthMonitor(agent_path)
        report = monitor.analyze(days=7)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Network error")
            )

            result = await send_webhook("https://example.com/webhook", report, HealthStatus.HEALTHY)
            assert result is False


class TestHealthThresholds:
    """Tests for configurable health thresholds."""

    def test_threshold_constants(self):
        assert HealthThresholds.SUCCESS_RATE_HEALTHY == 0.90
        assert HealthThresholds.SUCCESS_RATE_DEGRADED == 0.80
        assert HealthThresholds.RECENT_DEGRADATION_THRESHOLD == 0.15
        assert HealthThresholds.HIGH_LATENCY_P95_MS == 30000


class TestWatchMode:
    """Tests for real-time watch mode."""

    @pytest.mark.asyncio
    async def test_watch_mode_stops_on_signal(self, temp_agent_dir):
        agent_path, _, _ = temp_agent_dir
        monitor = AgentHealthMonitor(agent_path)

        monitor.stop_watch()

        callback_called = []

        def callback(report):
            callback_called.append(True)

        await monitor.watch(interval=0.1, days=7, on_update=callback)

        assert len(callback_called) == 1

    def test_add_watch_callback(self, temp_agent_dir):
        agent_path, _, _ = temp_agent_dir
        monitor = AgentHealthMonitor(agent_path)

        callback_called = []

        def callback(report):
            callback_called.append(report.agent_name)

        monitor.add_watch_callback(callback)

        assert len(monitor._watch_callbacks) == 1
