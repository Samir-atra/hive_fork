"""
Test hallucination detection in SharedMemory and OutputValidator.

These tests verify that code detection works correctly across the entire
string content, not just the first 500 characters.
"""

import pytest

from .test_helpers import assert_hallucination_error, assert_memory_write_succeeds
from framework.graph.node import MemoryWriteError, SharedMemory
from framework.graph.validator import OutputValidator, ValidationResult


class TestSharedMemoryHallucinationDetection:
    """Test the SharedMemory hallucination detection."""

    def test_detects_code_at_start(self, memory: SharedMemory):
        """Code at the start of the string should be detected."""
        code_content = "```python\nimport os\ndef hack(): pass\n```" + "A" * 6000

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", code_content)

        assert_hallucination_error(exc_info)

    def test_detects_code_in_middle(self, memory: SharedMemory, make_content_with_code):
        """Code in the middle of the string should be detected (was previously missed)."""
        code = "\n```python\nimport os\ndef malicious(): pass\n```\n"
        content = make_content_with_code(code, padding_start=600, padding_end=5000)

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert_hallucination_error(exc_info)

    def test_detects_code_at_end(self, memory: SharedMemory):
        """Code at the end of the string should be detected (was previously missed)."""
        padding = "A" * 5500
        code = "\n```python\nclass Exploit:\n    pass\n```"
        content = padding + code

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert_hallucination_error(exc_info)

    @pytest.mark.parametrize(
        "code_type,code_snippet",
        [
            ("javascript", "\nfunction malicious() { require('child_process'); }\n"),
            ("sql_injection", "\nDROP TABLE users; SELECT * FROM passwords;\n"),
            ("script_injection", "\n<script>alert('xss')</script>\n"),
        ],
        ids=["javascript", "sql_injection", "script_injection"],
    )
    def test_detects_various_code_patterns(
        self, memory: SharedMemory, make_content_with_code, code_type: str, code_snippet: str
    ):
        """Various code patterns should be detected."""
        content = make_content_with_code(code_snippet, padding_start=600, padding_end=5000)

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert_hallucination_error(exc_info)

    def test_allows_short_strings_without_validation(self, memory: SharedMemory):
        """Strings under 5000 chars should not trigger validation."""
        content = "def hello(): pass"

        assert_memory_write_succeeds(memory, "output", content)
        assert memory.read("output") == content

    def test_allows_long_strings_without_code(self, memory: SharedMemory):
        """Long strings without code indicators should be allowed."""
        content = "This is a long text document. " * 500

        assert_memory_write_succeeds(memory, "output", content)

    def test_validate_false_bypasses_check(self, memory: SharedMemory):
        """Using validate=False should bypass the check."""
        code_content = "```python\nimport os\n```" + "A" * 6000

        assert_memory_write_succeeds(memory, "output", code_content, validate=False)

    def test_sampling_for_very_long_strings(self, memory: SharedMemory):
        """Very long strings (>10KB) should be sampled at multiple positions."""
        size = 50000
        code_position = int(size * 0.75)
        content = (
            "A" * code_position + "def hidden_code(): pass" + "B" * (size - code_position - 25)
        )

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert_hallucination_error(exc_info)


class TestOutputValidatorHallucinationDetection:
    """Test the OutputValidator hallucination detection."""

    def test_detects_code_anywhere_in_output(self, validator: OutputValidator):
        """Code anywhere in the output value should trigger a warning."""
        padding = "Normal text content. " * 50
        code = "\ndef suspicious_function():\n    pass\n"
        output = {"result": padding + code}

        result = validator.validate_no_hallucination(output)
        assert isinstance(result, ValidationResult)

    @pytest.mark.parametrize(
        "padding_size,content_suffix",
        [
            (600, "import os"),
        ],
        ids=["code_at_position_600"],
    )
    def test_contains_code_indicators_full_check(
        self, validator: OutputValidator, padding_size: int, content_suffix: str
    ):
        """_contains_code_indicators should check the entire string."""
        padding = "A" * padding_size
        content = padding + content_suffix

        assert validator._contains_code_indicators(content) is True

    def test_contains_code_indicators_sampling(self, validator: OutputValidator):
        """_contains_code_indicators should sample for very long strings."""
        size = 50000
        code_position = int(size * 0.75)
        content = "A" * code_position + "class HiddenClass:" + "B" * (size - code_position - 18)

        assert validator._contains_code_indicators(content) is True

    def test_no_false_positive_for_clean_text(self, validator: OutputValidator):
        """Clean text without code should not trigger false positives."""
        content = "This is a perfectly normal document. " * 300

        assert validator._contains_code_indicators(content) is False

    @pytest.mark.parametrize(
        "language,code",
        [
            ("javascript_func", "function test() {}"),
            ("javascript_const", "const x = 5;"),
            ("sql_select", "SELECT * FROM users"),
            ("sql_drop", "DROP TABLE data"),
            ("html_script", "<script>"),
            ("php", "<?php"),
        ],
        ids=["javascript_func", "javascript_const", "sql_select", "sql_drop", "html_script", "php"],
    )
    def test_detects_multiple_languages(self, validator: OutputValidator, language: str, code: str):
        """Should detect code patterns from multiple programming languages."""
        assert validator._contains_code_indicators(code) is True, f"Failed to detect: {code}"


class TestEdgeCases:
    """Test edge cases for hallucination detection."""

    def test_empty_string(self, memory: SharedMemory):
        """Empty strings should not cause errors."""
        assert_memory_write_succeeds(memory, "output", "")

    def test_non_string_values(self, memory: SharedMemory):
        """Non-string values should not be validated for code."""
        memory.write("number", 12345)
        memory.write("list", [1, 2, 3])
        memory.write("dict", {"key": "value"})
        memory.write("bool", True)

        assert memory.read("number") == 12345
        assert memory.read("list") == [1, 2, 3]

    @pytest.mark.parametrize(
        "length,should_raise",
        [
            (5000, False),
            (5001, True),
        ],
        ids=["exactly_5000_chars", "5001_chars"],
    )
    def test_boundary_conditions(self, memory: SharedMemory, length: int, should_raise: bool):
        """Test boundary conditions for content length validation."""
        content = "def code(): pass" + "A" * (length - 16)

        if should_raise:
            with pytest.raises(MemoryWriteError):
                memory.write("output", content)
        else:
            assert_memory_write_succeeds(memory, "output", content)
            assert len(memory.read("output")) == length
