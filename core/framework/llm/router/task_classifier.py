import re


class TaskClassifier:
    """Pattern-based task classifier using regex fast-path."""

    def __init__(self) -> None:
        """Initialize the task classifier with regex patterns."""
        self.patterns = {
            "math_reasoning": re.compile(
                r"(?i)\b(math|calculate|equation|algebra|calculus|geometry|probability|statistics|solve for|theorem|proof|formula)\b"
            ),
            "coding": re.compile(
                r"(?i)\b(code|function|class|method|variable|loop|array|script|debug|syntax|compiler|python|javascript|java|c\+\+|rust|go|html|css|sql|bash|git|regex)\b"
            ),
            "function_calling": re.compile(
                r"(?i)\b(call|api|endpoint|request|json|payload|response|fetch|post|get|put|delete|tool|execute)\b"
            ),
        }

    def classify(self, prompt: str | list) -> str:
        """Classifies the prompt into a task category based on regex patterns.

        Args:
            prompt: The input prompt string to classify.

        Returns:
            The matched category name or 'general' if none match.
        """
        if not prompt:
            return "general"

        if isinstance(prompt, list):
            # Extract text from multimodal prompt
            text_parts = []
            for item in prompt:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            prompt = " ".join(text_parts)

        if not isinstance(prompt, str):
            prompt = str(prompt)

        for category, pattern in self.patterns.items():
            if pattern.search(prompt):
                return category

        return "general"
