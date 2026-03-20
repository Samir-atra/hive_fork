from aden_tools.monitoring.context_tracker import ContextUsageTracker, _estimate_tokens


def test_estimate_tokens():
    text = "01234567"
    assert _estimate_tokens(text) == 2


def test_record_tool_registration():
    tracker = ContextUsageTracker()
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    tracker.record_tool_registration("my_tool", "my description", schema)

    assert "my_tool" in tracker.tools
    tool_usage = tracker.tools["my_tool"]
    assert tool_usage.name == "my_tool"
    assert tool_usage.description == "my description"
    # Estimate calculation verification
    # total_str = "my_tool" + "my description" + json.dumps(schema)
    assert tool_usage.registration_tokens > 0


def test_record_execution():
    tracker = ContextUsageTracker()
    tracker.record_tool_registration("my_tool", "my desc", {})

    class MockContent:
        def __init__(self, text):
            self.text = text

    class MockResult:
        def __init__(self, content):
            self.content = content

    args = {"arg1": "value"}
    result = MockResult([MockContent("hello world")])

    tracker.record_execution("my_tool", args, result)

    tool_usage = tracker.tools["my_tool"]
    assert tool_usage.execution_count == 1
    assert tool_usage.input_tokens > 0
    assert tool_usage.output_tokens == len("hello world") // 4


def test_get_summary():
    tracker = ContextUsageTracker()
    tracker.record_tool_registration("tool1", "desc1", {})
    tracker.record_tool_registration("tool2", "desc2", {})

    tracker.record_execution("tool1", {}, None)

    summary = tracker.get_summary()
    assert summary["total_tools_registered"] == 2
    assert summary["tools_used"] == 1
    assert "estimated_cost_usd" in summary
    assert len(summary["tools"]) == 2
