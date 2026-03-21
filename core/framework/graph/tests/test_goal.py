from framework.graph.goal import EvolutionScope, Goal, SuccessCriterion


def test_evolution_scope_to_prompt_context():
    goal = Goal(
        id="test-1",
        name="Test Goal",
        description="A goal with evolution scope",
        success_criteria=[
            SuccessCriterion(
                id="sc1", description="Test success", metric="custom", target="none", weight=1.0
            )
        ],
        evolution_scope=EvolutionScope(
            allowed=["prompt phrasing", "tool selection"],
            forbidden=["external API credentials", "budget limits"],
        ),
    )

    prompt = goal.to_prompt_context()
    assert "## Evolution Scope:" in prompt
    assert "Allowed to evolve:" in prompt
    assert "- prompt phrasing" in prompt
    assert "- tool selection" in prompt
    assert "Forbidden to evolve:" in prompt
    assert "- external API credentials" in prompt
    assert "- budget limits" in prompt


def test_evolution_scope_optional():
    goal = Goal(
        id="test-1",
        name="Test Goal",
        description="A goal without evolution scope",
        success_criteria=[
            SuccessCriterion(
                id="sc1", description="Test success", metric="custom", target="none", weight=1.0
            )
        ],
    )

    prompt = goal.to_prompt_context()
    assert "Evolution Scope" not in prompt
