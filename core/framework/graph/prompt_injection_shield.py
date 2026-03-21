import re
from dataclasses import dataclass
from enum import StrEnum


class ShieldMode(StrEnum):
    OFF = "off"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class ScanResult:
    detected: bool
    patterns_found: list[str]


class InjectionDetected(Exception):
    """Exception raised when prompt injection is detected in block mode."""

    pass


class PromptInjectionShield:
    """Scans and wraps tool results to defend against indirect prompt injection."""

    # 16 regex patterns across 5 categories
    PATTERNS = {
        "instruction_override": [
            r"(?i)\bignore\s+(all\s+)?previous\s+instructions\b",
            r"(?i)\bforget\s+(all\s+)?(your\s+)?instructions\b",
            r"(?i)\bdisregard\s+(all\s+)?previous\b",
            r"(?i)\bnew\s+instructions?:",
        ],
        "role_hijacking": [
            r"(?i)\byou\s+are\s+now(\s+a)?\b",
            r"(?i)\bact\s+as\s+(\w+)\b",
            r"(?i)\bswitch\s+to\s+(\w+)\s+mode\b",
            r"(?i)\b(system|assistant|user):\s*$",
        ],
        "information_extraction": [
            r"(?i)\blist\s+all\s+system\b",
            r"(?i)\boutput\s+(the\s+)?system\s+prompt\b",
            r"(?i)\bprint\s+(your\s+)?instructions\b",
        ],
        "delimiter_escape": [r"(?i)</?tool_result>", r"(?i)\[/?END\]", r"(?i)</?source>"],
        "command_injection": [
            r"(?i)\bexecute\s+the\s+following\b",
            r"(?i)\brun\s+this\s+(code|command)\b",
        ],
    }

    def __init__(self):
        self._compiled_patterns = {}
        for category, patterns in self.PATTERNS.items():
            self._compiled_patterns[category] = [re.compile(p) for p in patterns]

    def _scan(self, content: str) -> ScanResult:
        patterns_found = []
        for category, compiled_list in self._compiled_patterns.items():
            for compiled in compiled_list:
                if compiled.search(content):
                    patterns_found.append(category)
                    break
        return ScanResult(detected=len(patterns_found) > 0, patterns_found=patterns_found)

    def scan_and_wrap(self, content: str, tool_name: str, mode: str) -> str:
        if mode == ShieldMode.OFF or mode is None or str(mode).lower() == "none":
            return content

        try:
            scan_result = self._scan(content)
        except Exception:
            # Fail-open design: if scanning crashes, we just return the content
            return content

        if scan_result.detected:
            if mode == ShieldMode.BLOCK:
                raise InjectionDetected("Prompt injection detected in tool result.")

            # WARN mode
            categories = ", ".join(scan_result.patterns_found)
            return (
                f'<tool_result source="{tool_name}" trust="untrusted" '
                f'injection_warning="{categories} found">\n{content}\n</tool_result>'
            )
        else:
            return f'<tool_result source="{tool_name}" trust="external">\n{content}\n</tool_result>'
