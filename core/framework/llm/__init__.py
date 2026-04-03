"""LLM provider abstraction."""

from framework.llm.provider import LLMProvider, LLMResponse
from framework.llm.stream_events import (
    FinishEvent,
    ReasoningDeltaEvent,
    ReasoningStartEvent,
    StreamErrorEvent,
    StreamEvent,
    TextDeltaEvent,
    TextEndEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from framework.llm.versioning import ModelVersion, ModelVersionManager

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "StreamEvent",
    "TextDeltaEvent",
    "TextEndEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ReasoningStartEvent",
    "ReasoningDeltaEvent",
    "FinishEvent",
    "StreamErrorEvent",
    "ModelVersionManager",
    "ModelVersion",
]

try:
    from framework.llm.anthropic import AnthropicProvider  # noqa: F401

    __all__.append("AnthropicProvider")
except ImportError:
    pass

try:
    from framework.llm.litellm import LiteLLMProvider  # noqa: F401

    __all__.append("LiteLLMProvider")
except ImportError:
    pass

try:
    from framework.llm.mock import MockLLMProvider  # noqa: F401

    __all__.append("MockLLMProvider")
except ImportError:
    pass
