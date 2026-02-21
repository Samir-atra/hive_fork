"""
Test hallucination detection in SharedMemory and OutputValidator.

These tests verify that code detection works correctly across the entire
string content, not just the first 500 characters.
"""

import pytest

from framework.graph.node import MemoryWriteError, SharedMemory
from framework.graph.validator import OutputValidator, ValidationResult


class TestSharedMemoryHallucinationDetection:
    """Test the SharedMemory hallucination detection."""

    def test_detects_code_at_start(self):
        """Code at the start of the string should be detected."""
        memory = SharedMemory()
        code_content = "```python\nimport os\ndef hack(): pass\n```" + "A" * 6000

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", code_content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_code_in_middle(self):
        """Code in the middle of the string should be detected (was previously missed)."""
        memory = SharedMemory()
        # 600 chars of padding, then code, then more padding to exceed 5000 chars
        padding_start = "A" * 600
        code = "\n```python\nimport os\ndef malicious(): pass\n```\n"
        padding_end = "B" * 5000
        content = padding_start + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_code_at_end(self):
        """Code at the end of the string should be detected (was previously missed)."""
        memory = SharedMemory()
        padding = "A" * 5500
        code = "\n```python\nclass Exploit:\n    pass\n```"
        content = padding + code

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_javascript_code(self):
        """JavaScript code patterns should be detected."""
        memory = SharedMemory()
        padding = "A" * 600
        code = "\nfunction malicious() { require('child_process'); }\n"
        padding_end = "B" * 5000
        content = padding + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_sql_injection(self):
        """SQL patterns should be detected."""
        memory = SharedMemory()
        padding = "A" * 600
        code = "\nDROP TABLE users; SELECT * FROM passwords;\n"
        padding_end = "B" * 5000
        content = padding + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_script_injection(self):
        """HTML script injection should be detected."""
        memory = SharedMemory()
        padding = "A" * 600
        code = "\n<script>alert('xss')</script>\n"
        padding_end = "B" * 5000
        content = padding + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_allows_short_strings_without_validation(self):
        """Strings under 5000 chars should not trigger validation."""
        memory = SharedMemory()
        content = "def hello(): pass"  # Contains code indicator but short

        # Should not raise - too short to validate
        memory.write("output", content)
        assert memory.read("output") == content

    def test_allows_long_strings_without_code(self):
        """Long strings without code indicators should be allowed."""
        memory = SharedMemory()
        content = "This is a long text document. " * 500  # ~15000 chars, no code

        memory.write("output", content)
        assert memory.read("output") == content

    def test_validate_false_bypasses_check(self):
        """Using validate=False should bypass the check."""
        memory = SharedMemory()
        code_content = "```python\nimport os\n```" + "A" * 6000

        # Should not raise when validate=False
        memory.write("output", code_content, validate=False)
        assert memory.read("output") == code_content

    def test_sampling_for_very_long_strings(self):
        """Very long strings (>10KB) should be sampled at multiple positions."""
        memory = SharedMemory()
        # Create a 50KB string with code at the 75% mark
        size = 50000
        code_position = int(size * 0.75)
        content = (
            "A" * code_position + "def hidden_code(): pass" + "B" * (size - code_position - 25)
        )

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)


class TestOutputValidatorHallucinationDetection:
    """Test the OutputValidator hallucination detection."""

    def test_detects_code_anywhere_in_output(self):
        """Code anywhere in the output value should trigger a warning."""
        validator = OutputValidator()
        padding = "Normal text content. " * 50
        code = "\ndef suspicious_function():\n    pass\n"
        output = {"result": padding + code}

        # The method logs a warning but doesn't fail
        result = validator.validate_no_hallucination(output)
        # The warning is logged - we can't easily test logging, but the method should work
        assert isinstance(result, ValidationResult)

    def test_contains_code_indicators_full_check(self):
        """_contains_code_indicators should check the entire string."""
        validator = OutputValidator()

        # Code at position 600 (was previously missed with [:500] check)
        padding = "A" * 600
        code = "import os"
        content = padding + code

        assert validator._contains_code_indicators(content) is True

    def test_contains_code_indicators_sampling(self):
        """_contains_code_indicators should sample for very long strings."""
        validator = OutputValidator()

        # 50KB string with code at 75% position
        size = 50000
        code_position = int(size * 0.75)
        content = "A" * code_position + "class HiddenClass:" + "B" * (size - code_position - 18)

        assert validator._contains_code_indicators(content) is True

    def test_no_false_positive_for_clean_text(self):
        """Clean text without code should not trigger false positives."""
        validator = OutputValidator()

        # Long text without any code indicators
        content = "This is a perfectly normal document. " * 300

        assert validator._contains_code_indicators(content) is False

    def test_detects_multiple_languages(self):
        """Should detect code patterns from multiple programming languages."""
        validator = OutputValidator()

        test_cases = [
            "function test() {}",  # JavaScript
            "const x = 5;",  # JavaScript
            "SELECT * FROM users",  # SQL
            "DROP TABLE data",  # SQL
            "<script>",  # HTML
            "<?php",  # PHP
        ]

        for code in test_cases:
            assert validator._contains_code_indicators(code) is True, f"Failed to detect: {code}"


class TestEdgeCases:
    """Test edge cases for hallucination detection."""

    def test_empty_string(self):
        """Empty strings should not cause errors."""
        memory = SharedMemory()
        memory.write("output", "")
        assert memory.read("output") == ""

    def test_non_string_values(self):
        """Non-string values should not be validated for code."""
        memory = SharedMemory()

        # These should all work without validation
        memory.write("number", 12345)
        memory.write("list", [1, 2, 3])
        memory.write("dict", {"key": "value"})
        memory.write("bool", True)

        assert memory.read("number") == 12345
        assert memory.read("list") == [1, 2, 3]

    def test_exactly_5000_chars(self):
        """String of exactly 5000 chars should not trigger validation."""
        memory = SharedMemory()
        content = "def code(): pass" + "A" * (5000 - 16)  # Exactly 5000 chars

        # Should not raise - exactly at threshold, not over
        memory.write("output", content)
        assert len(memory.read("output")) == 5000

    def test_5001_chars_triggers_validation(self):
        """String of 5001 chars with code should trigger validation."""
        memory = SharedMemory()
        content = "def code(): pass" + "A" * (5001 - 16)  # 5001 chars

        with pytest.raises(MemoryWriteError):
            memory.write("output", content)


class TestSharedMemoryReadAllDeepCopy:
    """Test that read_all() returns a deep copy to prevent unintended mutation."""

    def test_read_all_returns_deep_copy_of_list(self):
        """Modifying a list in the returned dict should not affect shared memory."""
        memory = SharedMemory()
        memory.write("items", [1, 2, 3])

        data = memory.read_all()
        data["items"].append(4)

        assert memory.read("items") == [1, 2, 3]
        assert data["items"] == [1, 2, 3, 4]

    def test_read_all_returns_deep_copy_of_dict(self):
        """Modifying a nested dict in the returned dict should not affect shared memory."""
        memory = SharedMemory()
        memory.write("config", {"nested": {"value": 42}})

        data = memory.read_all()
        data["config"]["nested"]["value"] = 999

        assert memory.read("config") == {"nested": {"value": 42}}
        assert data["config"]["nested"]["value"] == 999

    def test_read_all_returns_deep_copy_of_nested_structure(self):
        """Modifying deeply nested structures should not affect shared memory."""
        memory = SharedMemory()
        memory.write("data", {"list": [{"id": 1}, {"id": 2}]})

        data = memory.read_all()
        data["data"]["list"][0]["id"] = 100

        assert memory.read("data") == {"list": [{"id": 1}, {"id": 2}]}
        assert data["data"]["list"][0]["id"] == 100

    def test_read_all_dict_keys_are_independent(self):
        """Adding/removing keys in returned dict should not affect shared memory."""
        memory = SharedMemory()
        memory.write("key1", "value1")

        data = memory.read_all()
        data["key2"] = "value2"
        del data["key1"]

        assert memory.read("key1") == "value1"
        assert memory.read("key2") is None
        assert "key1" not in data
        assert "key2" in data

    def test_read_all_with_permissions_returns_deep_copy(self):
        """read_all with permissions should also return deep copy."""
        memory = SharedMemory()
        memory.write("allowed", {"nested": [1, 2, 3]})
        memory.write("restricted", {"secret": "data"})

        scoped = memory.with_permissions(read_keys=["allowed"], write_keys=[])
        data = scoped.read_all()

        data["allowed"]["nested"].append(4)
        data["allowed"]["nested"] = "modified"

        assert memory.read("allowed") == {"nested": [1, 2, 3]}
        assert "restricted" not in data

    def test_read_all_with_mutable_set(self):
        """Modifying a set in returned dict should not affect shared memory."""
        memory = SharedMemory()
        memory.write("tags", {"a", "b", "c"})

        data = memory.read_all()
        data["tags"].add("d")

        assert memory.read("tags") == {"a", "b", "c"}
        assert "d" in data["tags"]
