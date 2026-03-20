"""Runtime tracker for MCP tool context usage and token costs."""
import functools
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


def _estimate_tokens(text: str) -> int:
    return len(text) // 4

@dataclass
class ToolContextUsage:
    """Usage stats for a single tool."""
    name: str
    description: str
    registration_tokens: int
    execution_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

class ContextUsageTracker:
    """Tracks token usage across the tool lifecycle."""
    def __init__(self) -> None:
        self.tools: dict[str, ToolContextUsage] = {}

    def record_tool_registration(self, name: str, description: str, schema: Any) -> None:
        """Record the static tokens consumed by a tool's definition."""
        schema_str = json.dumps(schema) if schema else "{}"
        desc_str = description or ""
        total_str = f"{name}{desc_str}{schema_str}"
        tokens = _estimate_tokens(total_str)

        if name not in self.tools:
            self.tools[name] = ToolContextUsage(
                name=name,
                description=desc_str,
                registration_tokens=tokens
            )
        else:
            self.tools[name].description = desc_str
            self.tools[name].registration_tokens = tokens

    def record_execution(self, name: str, input_args: Any, result: Any) -> None:
        """Record the dynamic tokens consumed by a tool execution."""
        if name not in self.tools:
            return

        self.tools[name].execution_count += 1

        args_str = json.dumps(input_args) if input_args else ""
        self.tools[name].input_tokens += _estimate_tokens(args_str)

        output_tokens = 0
        if result:
            if hasattr(result, "content") and result.content:
                for content_item in result.content:
                    if hasattr(content_item, "text") and content_item.text:
                        output_tokens += _estimate_tokens(content_item.text)
                    elif hasattr(content_item, "data") and content_item.data:
                        # Very rough heuristic for images/base64 content
                        output_tokens += _estimate_tokens(content_item.data)
            elif isinstance(result, str):
                output_tokens += _estimate_tokens(result)
            else:
                try:
                    output_tokens += _estimate_tokens(json.dumps(result))
                except Exception:
                    pass
        self.tools[name].output_tokens += output_tokens

    def get_summary(self) -> dict:
        """Get a summary of current context usage."""
        registered = len(self.tools)
        reg_tokens = sum(t.registration_tokens for t in self.tools.values())
        used = sum(1 for t in self.tools.values() if t.execution_count > 0)
        exec_tokens = sum(t.input_tokens + t.output_tokens for t in self.tools.values())
        wasted_tokens = sum(
            t.registration_tokens for t in self.tools.values() if t.execution_count == 0
        )

        total_tokens = reg_tokens + exec_tokens
        # $0.03 per 1K tokens
        cost = (total_tokens / 1000) * 0.03

        tools_list = []
        # Sort by most expensive tools statically
        for name, t in sorted(
            self.tools.items(), key=lambda x: x[1].registration_tokens, reverse=True
        ):
            tools_list.append({
                "name": name,
                "registration_tokens": t.registration_tokens,
                "execution_count": t.execution_count,
                "input_tokens": t.input_tokens,
                "output_tokens": t.output_tokens,
            })

        return {
            "total_tools_registered": registered,
            "total_registration_tokens": reg_tokens,
            "tools_used": used,
            "total_execution_tokens": exec_tokens,
            "wasted_registration_tokens": wasted_tokens,
            "estimated_cost_usd": round(cost, 6),
            "tools": tools_list
        }


# Global singleton instance for the session
_tracker = ContextUsageTracker()

def get_tracker() -> ContextUsageTracker:
    """Get the active context usage tracker."""
    return _tracker

def track_tool_execution(tool_name: str, fn: Callable) -> Callable:
    """Decorator to track dynamic execution of an MCP tool function."""
    is_async = inspect.iscoroutinefunction(fn)

    if is_async:
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            # Convert args to string dict representation
            input_data = {"args": args, "kwargs": kwargs}
            try:
                result = await fn(*args, **kwargs)
                _tracker.record_execution(tool_name, input_data, result)
                return result
            except Exception as e:
                _tracker.record_execution(tool_name, input_data, {"error": str(e)})
                raise
        return async_wrapper
    else:
        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            input_data = {"args": args, "kwargs": kwargs}
            try:
                result = fn(*args, **kwargs)
                _tracker.record_execution(tool_name, input_data, result)
                return result
            except Exception as e:
                _tracker.record_execution(tool_name, input_data, {"error": str(e)})
                raise
        return sync_wrapper
