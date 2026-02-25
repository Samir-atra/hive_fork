"""Quick model switcher modal for runtime model changes."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Label, OptionList
from textual.widgets._option_list import Option

if TYPE_CHECKING:
    from framework.runtime.agent_runtime import AgentRuntime


PRESETS = [
    {
        "key": "1",
        "model_id": "claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "desc": "best quality",
        "env_var": "ANTHROPIC_API_KEY",
        "emoji": "*",
    },
    {
        "key": "2",
        "model_id": "groq/llama-3.3-70b-versatile",
        "name": "Groq Llama 3.3 70B",
        "desc": "fastest",
        "env_var": "GROQ_API_KEY",
        "emoji": "!",
    },
    {
        "key": "3",
        "model_id": "groq/llama3-8b-8192",
        "name": "Groq Llama 3 8B",
        "desc": "cheapest",
        "env_var": "GROQ_API_KEY",
        "emoji": "$",
    },
    {
        "key": "4",
        "model_id": "gemini/gemini-2.0-flash-exp",
        "name": "Gemini 2.0 Flash",
        "desc": "1M context",
        "env_var": "GEMINI_API_KEY",
        "emoji": "+",
    },
]


class QuickModelSwitcher(ModalScreen[dict | None]):
    """Quick model switcher with preset models."""

    BINDINGS = [
        Binding("escape", "dismiss_switcher", "Cancel"),
        Binding("1", "select_preset_1", "Claude"),
        Binding("2", "select_preset_2", "Groq 70B"),
        Binding("3", "select_preset_3", "Groq 8B"),
        Binding("4", "select_preset_4", "Gemini"),
    ]

    DEFAULT_CSS = """
    QuickModelSwitcher {
        align: center middle;
    }
    #switcher-dialog {
        width: 80;
        max-width: 90;
        height: auto;
        background: $surface;
        border: heavy $primary;
        padding: 1 2;
    }
    #switcher-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        color: $text;
        margin-bottom: 1;
    }
    #current-model {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }
    #preset-list {
        height: auto;
        max-height: 12;
        margin-bottom: 1;
    }
    #persist-checkbox {
        margin-bottom: 1;
    }
    #switcher-footer {
        text-align: center;
        width: 100%;
    }
    OptionList > .option-list--option {
        padding: 0 1;
    }
    """

    def __init__(self, runtime: AgentRuntime):
        super().__init__()
        self._runtime = runtime
        self._current_model = runtime.current_model

    def compose(self) -> ComposeResult:
        with Vertical(id="switcher-dialog"):
            yield Label("Quick Model Switch", id="switcher-title")
            yield Label(f"Current: [cyan]{self._current_model}[/cyan]", id="current-model")

            option_list = OptionList(id="preset-list")
            for preset in PRESETS:
                api_key_ok = bool(os.environ.get(preset["env_var"]))
                status = "[green]+[/green]" if api_key_ok else "[red]x[/red]"
                current = (
                    " [dim](current)[/dim]" if preset["model_id"] == self._current_model else ""
                )

                option_text = Text.from_markup(
                    f"[{preset['key']}] {preset['emoji']} {preset['name']} "
                    f"([dim]{preset['desc']}[/dim]) {status}{current}"
                )
                option_list.add_option(Option(option_text, id=preset["model_id"]))

            option_list.add_option(
                Option(
                    Text.from_markup("[5] ... More options (full selector)"),
                    id="__more__",
                )
            )
            yield option_list
            yield Checkbox("Save to configuration file", id="persist-checkbox")
            yield Label(
                "[dim][1-4] Select  [5] Full selector  [Esc] Cancel[/dim]",
                id="switcher-footer",
            )

    def _get_persist(self) -> bool:
        checkbox = self.query_one("#persist-checkbox", Checkbox)
        return checkbox.value

    def _select_model(self, model_id: str) -> None:
        if model_id == "__more__":
            self.dismiss({"model_id": None, "show_full_selector": True, "persist": False})
        else:
            self.dismiss(
                {"model_id": model_id, "show_full_selector": False, "persist": self._get_persist()}
            )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._select_model(str(event.option.id))

    def action_dismiss_switcher(self) -> None:
        self.dismiss(None)

    def action_select_preset_1(self) -> None:
        self._select_model(PRESETS[0]["model_id"])

    def action_select_preset_2(self) -> None:
        self._select_model(PRESETS[1]["model_id"])

    def action_select_preset_3(self) -> None:
        self._select_model(PRESETS[2]["model_id"])

    def action_select_preset_4(self) -> None:
        self._select_model(PRESETS[3]["model_id"])
