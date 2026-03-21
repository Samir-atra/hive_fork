with open("core/tests/test_failure_conditions.py", "w") as f:
    f.write('''from framework.testing.failure_conditions import (
    ErrorTypeCondition,
    MetricRangeCondition,
    StringMatchCondition,
)

def test_string_match_condition():
    cond_contain = StringMatchCondition(description="test", substring="hello", should_contain=True)
    assert cond_contain.evaluate("hello world") is False  # it matches, so it's NOT a failure
    assert cond_contain.evaluate("hi world") is True

    cond_not_contain = StringMatchCondition(
        description="test", substring="error", should_contain=False
    )
    assert cond_not_contain.evaluate("hello world") is False  # "error" not found, so not a failure
    assert cond_not_contain.evaluate("an error occurred") is True

def test_error_type_condition():
    cond = ErrorTypeCondition(description="test", error_type="ValueError")
    assert cond.evaluate(None, ValueError("test")) is True
    assert cond.evaluate(None, TypeError("test")) is False
    assert cond.evaluate(None, None) is False

def test_metric_range_condition():
    cond = MetricRangeCondition(description="test", min_value=1.0, max_value=5.0)
    assert cond.evaluate(3.0) is False  # Within range, so not a failure
    assert cond.evaluate(0.5) is True  # Outside range, so failure
    assert cond.evaluate(6.0) is True  # Outside range, so failure
    assert cond.evaluate("abc") is True  # Invalid type, so failure
    assert cond.evaluate(None, ValueError("test")) is True  # Error occurred, so failure

def test_metric_range_condition_only_min():
    cond = MetricRangeCondition(description="test", min_value=1.0)
    assert cond.evaluate(3.0) is False
    assert cond.evaluate(0.5) is True

def test_metric_range_condition_only_max():
    cond = MetricRangeCondition(description="test", max_value=5.0)
    assert cond.evaluate(3.0) is False
    assert cond.evaluate(6.0) is True
''')
