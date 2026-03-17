"""Feedback store for persistent developer preferences."""

import json
from pathlib import Path


class FeedbackStore:
    """Singleton feedback store backed by a local JSON file."""

    _instance = None
    _store_path = Path.home() / ".hive" / "feedback.json"

    def __new__(cls) -> "FeedbackStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_store()
        return cls._instance

    def _init_store(self) -> None:
        """Initialize the storage directory and file if they don't exist."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._store_path.exists():
            self._store_path.write_text("[]", encoding="utf-8")

    def add_feedback(self, content: str, scope: str = "global") -> None:
        """Add a new feedback item.

        Args:
            content: The instruction or preference string.
            scope: The scope of the feedback. Defaults to "global".
        """
        import time

        feedbacks = self.get_all_feedback()
        feedbacks.append(
            {
                "scope": scope,
                "content": content,
                "timestamp": int(time.time()),
            }
        )
        self._store_path.write_text(json.dumps(feedbacks, indent=2), encoding="utf-8")

    def get_all_feedback(self) -> list[dict]:
        """Retrieve all feedback items."""
        try:
            return json.loads(self._store_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def get_global_feedback(self) -> list[str]:
        """Retrieve all global feedback content strings."""
        feedbacks = self.get_all_feedback()
        return [f["content"] for f in feedbacks if f.get("scope") == "global"]
