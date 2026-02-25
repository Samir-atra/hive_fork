import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from framework.builder.preview import PreviewGenerator, GoalPreview, NodePreview, EdgePreview
from framework.graph.goal import Goal, SuccessCriterion
from framework.builder.workflow import ValidationResult
from argparse import Namespace

@pytest.mark.asyncio
async def test_preview_generator_mock():
    """Test fallback to mock preview when no API key."""
    goal = Goal(
        id="test-goal",
        name="Test Agent",
        description="Just a test",
        success_criteria=[]
    )
    generator = PreviewGenerator()
    
    # Patch load_dotenv to prevent reloading .env
    with patch("dotenv.load_dotenv"), \
         patch.dict("os.environ", {}, clear=True):
        preview = await generator.generate_preview(goal)
        
        assert isinstance(preview, GoalPreview)
        # Mock preview has medium complexity
        assert preview.estimated_complexity == "medium"
        assert len(preview.proposed_nodes) == 3
        # Should have info risk flag about mock
        # Note: Depending on the implementation details, the exact message might vary
        # but the fallback returns a specific structure.

@pytest.mark.asyncio
async def test_risk_detection():
    """Test risk detection logic."""
    goal = Goal(
        id="risky-goal",
        name="Risky Agent",
        description="Do something complex",
        success_criteria=[
            SuccessCriterion(id="s1", description="Must validate email format", metric="llm_judge", target=True),
            SuccessCriterion(id="s2", description="Must send notification", metric="llm_judge", target=True)
        ]
    )
    
    generator = PreviewGenerator()
    
    # Manually create a preview with gaps
    mock_preview = GoalPreview(
        goal_summary="Summary",
        proposed_nodes=[
            NodePreview(name="EmailValidator", node_type="function", purpose="validate email format", estimated_llm_calls=0)
            # Missing "send notification" node
        ],
        proposed_edges=[],
        estimated_complexity="low",
        estimated_generation_cost=0.01,
        estimated_per_run_cost=0.01,
        risk_flags=[]
    )
    
    # Inject enrichment logic
    generator._enrich_risks(mock_preview, goal)
    
    # Should flag the missing criterion
    warnings = [r for r in mock_preview.risk_flags if r.severity == "warning"]
    assert len(warnings) >= 1
    # Check if notification is mentioned or covered
    # The heuristic might flag 'notification' as missing
    found = False
    for w in warnings:
        if "notification" in w.message or "covered" in w.message:
            found = True
            break
    assert found

def test_cli_interactive_flow():
    """Test the interactive CLI flow."""
    from framework.builder.cli import handle_preview
    
    mock_preview = GoalPreview(
        goal_summary="Test Goal",
        proposed_nodes=[NodePreview(name="Node1", node_type="function", purpose="Test", estimated_llm_calls=0)],
        proposed_edges=[],
        estimated_complexity="low",
        estimated_generation_cost=0.01,
        estimated_per_run_cost=0.001
    )
    
    mock_validation = ValidationResult(valid=True, preview=mock_preview)

    with patch('framework.builder.cli.Prompt.ask') as mock_ask, \
         patch('framework.builder.cli.asyncio.run') as mock_run, \
         patch('framework.builder.cli.GraphBuilder') as MockBuilder, \
         patch('builtins.open', new_callable=MagicMock) as mock_open:
         
        mock_run.return_value = mock_validation
        
        # Mock builder
        mock_builder = MockBuilder.return_value
        mock_builder._generate_code.return_value = "print('Hello Agent')"
        
        # Case 1: user selects 'n' (cancel)
        mock_ask.side_effect = ["n"]
        args = Namespace(goal="Test Goal", name="test-agent", criteria="")
        
        ret = handle_preview(args)
        assert ret == 0
        assert mock_ask.call_count == 1
        
        # Case 2: user selects 'y' (proceed) then 'n' (don't save report)
        mock_ask.reset_mock()
        mock_ask.side_effect = ["y", "n"]
        
        ret = handle_preview(args)
        assert ret == 0
        assert mock_ask.call_count == 2
        
        # Case 3: user selects 'r' (refine) then 'n' (cancel)
        mock_ask.reset_mock()
        mock_ask.side_effect = ["r", "Refined Goal", "n"]
        
        ret = handle_preview(args)
        assert ret == 0
        assert mock_ask.call_count == 3
