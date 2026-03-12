"""
Tests for human-in-the-loop approval breakpoints.

Tests the breakpoint mechanism that pauses execution before sensitive nodes
and waits for human approval.
"""

import pytest

from framework.graph.breakpoint_types import (
    ApprovalDecision,
    BreakpointRequest,
    BreakpointResult,
)
from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.graph.goal import Goal
from framework.graph.node import NodeSpec
from framework.runtime.core import Runtime
from framework.schemas.session_state import SessionStatus


class TestBreakpointTypes:
    """Tests for breakpoint request and result types."""

    def test_breakpoint_request_creation(self):
        """Test creating a breakpoint request."""
        request = BreakpointRequest(
            breakpoint_id="bp_test_123",
            node_id="delete_files",
            node_name="Delete Files",
            action_description="Delete temporary files from /tmp",
            context={"files_to_delete": ["/tmp/a.txt", "/tmp/b.txt"]},
            tools_to_execute=["delete_file"],
            session_id="session_123",
        )

        assert request.breakpoint_id == "bp_test_123"
        assert request.node_id == "delete_files"
        assert request.node_name == "Delete Files"
        assert request.action_description == "Delete temporary files from /tmp"
        assert len(request.context) == 1
        assert request.tools_to_execute == ["delete_file"]

    def test_breakpoint_request_to_prompt(self):
        """Test generating a human-readable prompt."""
        request = BreakpointRequest(
            breakpoint_id="bp_123",
            node_id="send_email",
            node_name="Send Email",
            action_description="Send notification email to user",
            tools_to_execute=["send_email"],
        )

        prompt = request.to_prompt()

        assert "APPROVAL REQUIRED" in prompt
        assert "Send Email" in prompt
        assert "send_email" in prompt
        assert "[a] Approve" in prompt
        assert "[r] Reject" in prompt
        assert "[x] Abort" in prompt

    def test_breakpoint_result_approve(self):
        """Test creating an approval result."""
        result = BreakpointResult.approve("bp_123", "Looks good")

        assert result.breakpoint_id == "bp_123"
        assert result.decision == ApprovalDecision.APPROVE
        assert result.reason == "Looks good"
        assert result.is_approved is True
        assert result.is_rejected is False
        assert result.is_aborted is False

    def test_breakpoint_result_reject(self):
        """Test creating a rejection result."""
        result = BreakpointResult.reject("bp_123", "Too risky")

        assert result.breakpoint_id == "bp_123"
        assert result.decision == ApprovalDecision.REJECT
        assert result.reason == "Too risky"
        assert result.is_approved is False
        assert result.is_rejected is True
        assert result.is_aborted is False

    def test_breakpoint_result_abort(self):
        """Test creating an abort result."""
        result = BreakpointResult.abort("bp_123", "User cancelled")

        assert result.breakpoint_id == "bp_123"
        assert result.decision == ApprovalDecision.ABORT
        assert result.reason == "User cancelled"
        assert result.is_approved is False
        assert result.is_rejected is False
        assert result.is_aborted is True


class TestNodeSpecBreakpoint:
    """Tests for NodeSpec breakpoint configuration."""

    def test_node_spec_default_no_breakpoint(self):
        """Test that nodes are not breakpoints by default."""
        node = NodeSpec(
            id="test_node",
            name="Test Node",
            description="A test node",
        )

        assert node.is_breakpoint is False
        assert node.action_description is None

    def test_node_spec_with_breakpoint(self):
        """Test creating a node with breakpoint enabled."""
        node = NodeSpec(
            id="delete_files",
            name="Delete Files",
            description="Deletes files from the filesystem",
            is_breakpoint=True,
            action_description="Delete specified files from disk",
            tools=["delete_file", "move_to_trash"],
        )

        assert node.is_breakpoint is True
        assert node.action_description == "Delete specified files from disk"
        assert "delete_file" in node.tools


class TestGraphSpecApprovalNodes:
    """Tests for GraphSpec approval_nodes configuration."""

    def test_graph_spec_default_no_approval_nodes(self):
        """Test that graphs have no approval nodes by default."""
        graph = GraphSpec(
            id="test_graph",
            goal_id="goal_123",
            entry_node="start",
            nodes=[
                NodeSpec(id="start", name="Start", description="Entry point"),
            ],
        )

        assert graph.approval_nodes == []

    def test_graph_spec_with_approval_nodes(self):
        """Test creating a graph with approval nodes."""
        graph = GraphSpec(
            id="test_graph",
            goal_id="goal_123",
            entry_node="start",
            approval_nodes=["delete_files", "send_email"],
            nodes=[
                NodeSpec(id="start", name="Start", description="Entry point"),
                NodeSpec(
                    id="delete_files",
                    name="Delete Files",
                    description="Delete files",
                    is_breakpoint=True,
                ),
                NodeSpec(
                    id="send_email",
                    name="Send Email",
                    description="Send email",
                ),
            ],
        )

        assert len(graph.approval_nodes) == 2
        assert "delete_files" in graph.approval_nodes
        assert "send_email" in graph.approval_nodes


class TestExecutionResultBreakpoint:
    """Tests for ExecutionResult breakpoint fields."""

    def test_execution_result_waiting_for_approval(self):
        """Test ExecutionResult with waiting_for_approval_at."""
        result = ExecutionResult(
            success=False,
            waiting_for_approval_at="delete_files",
            breakpoint_id="bp_delete_files_abc123",
            error="Execution paused for approval at breakpoint",
            session_state={
                "waiting_for_approval_at": "delete_files",
                "breakpoint_id": "bp_delete_files_abc123",
            },
        )

        assert result.success is False
        assert result.waiting_for_approval_at == "delete_files"
        assert result.breakpoint_id == "bp_delete_files_abc123"
        assert result.is_waiting_for_approval is True

    def test_execution_result_not_waiting(self):
        """Test ExecutionResult without breakpoint."""
        result = ExecutionResult(
            success=True,
            output={"result": "completed"},
        )

        assert result.success is True
        assert result.waiting_for_approval_at is None
        assert result.breakpoint_id is None
        assert result.is_waiting_for_approval is False


class TestSessionStatusApproval:
    """Tests for SessionStatus WAITING_FOR_APPROVAL."""

    def test_session_status_waiting_for_approval_exists(self):
        """Test that WAITING_FOR_APPROVAL status exists."""
        assert hasattr(SessionStatus, "WAITING_FOR_APPROVAL")
        assert SessionStatus.WAITING_FOR_APPROVAL == "waiting_for_approval"

    def test_session_status_values(self):
        """Test all session status values."""
        statuses = [s.value for s in SessionStatus]

        assert "active" in statuses
        assert "paused" in statuses
        assert "waiting_for_approval" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "cancelled" in statuses


class TestBreakpointIntegration:
    """Integration tests for breakpoint functionality with GraphExecutor."""

    @pytest.fixture
    def runtime(self):
        """Create a runtime for testing."""
        return Runtime()

    @pytest.fixture
    def goal(self):
        """Create a goal for testing."""
        return Goal(
            id="test_goal",
            name="Test Goal",
            description="A test goal for breakpoint testing",
            success_criteria=[],
        )

    @pytest.fixture
    def graph_with_breakpoint(self):
        """Create a graph with a breakpoint node."""
        return GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            approval_nodes=["sensitive_action"],
            nodes=[
                NodeSpec(
                    id="start",
                    name="Start",
                    description="Entry point",
                    output_keys=["initialized"],
                ),
                NodeSpec(
                    id="sensitive_action",
                    name="Sensitive Action",
                    description="A sensitive action requiring approval",
                    is_breakpoint=True,
                    action_description="Delete files and send emails",
                    input_keys=["initialized"],
                    output_keys=["action_completed"],
                ),
                NodeSpec(
                    id="end",
                    name="End",
                    description="Terminal node",
                    input_keys=["action_completed"],
                ),
            ],
            edges=[
                EdgeSpec(id="e1", source="start", target="sensitive_action"),
                EdgeSpec(id="e2", source="sensitive_action", target="end"),
            ],
            terminal_nodes=["end"],
        )

    def test_graph_validation_with_approval_nodes(self, graph_with_breakpoint):
        """Test that graphs with approval_nodes validate correctly."""
        result = graph_with_breakpoint.validate()

        assert result["errors"] == []

    def test_graph_validation_catches_invalid_approval_node(self):
        """Test that validation catches invalid approval node IDs."""
        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="start",
            approval_nodes=["nonexistent_node"],
            nodes=[
                NodeSpec(id="start", name="Start", description="Entry"),
            ],
        )

        result = graph.validate()

        assert len(result["errors"]) >= 1

    def test_execution_result_waiting_for_approval(self):
        """Test ExecutionResult.is_waiting_for_approval property."""
        result = ExecutionResult(
            success=False,
            waiting_for_approval_at="sensitive_action",
            breakpoint_id="bp_123",
            error="Execution paused for approval at breakpoint",
        )

        assert result.is_waiting_for_approval is True
        assert result.waiting_for_approval_at == "sensitive_action"
        assert result.breakpoint_id == "bp_123"

    def test_execution_result_not_waiting(self):
        """Test ExecutionResult when not waiting for approval."""
        result = ExecutionResult(
            success=True,
            output={"result": "completed"},
        )

        assert result.is_waiting_for_approval is False

    def test_session_status_waiting_for_approval(self):
        """Test that SessionStatus includes WAITING_FOR_APPROVAL."""
        assert hasattr(SessionStatus, "WAITING_FOR_APPROVAL")
        assert SessionStatus.WAITING_FOR_APPROVAL.value == "waiting_for_approval"
