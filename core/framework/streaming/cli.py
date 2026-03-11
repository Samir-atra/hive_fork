"""
CLI Dashboard for real-time execution monitoring.

Provides a terminal-based dashboard for watching agent executions in real-time.

Example:
    # Watch all executions
    python -m framework.streaming.cli

    # Watch specific stream
    python -m framework.streaming.cli --stream webhook

    # Watch specific execution
    python -m framework.streaming.cli --execution exec_12345

    # JSON output for piping
    python -m framework.streaming.cli --format json | jq '.event.type'
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box

from framework.runtime.agent_runtime import AgentRuntime
from framework.streaming.protocol import (
    FilterType,
    MessageType,
    StreamType,
    create_message,
)
from framework.streaming.server import StreamingServer
from framework.runtime.event_bus import EventBus

logger = logging.getLogger(__name__)
console = Console()


class Stream:
    """Websocket stream connection."""

    def __init__(self, stream_id: str, url: str, use_ssl: bool = False):
        """
        Initialize stream.

        Args:
            stream_id: Stream identifier
            url: WebSocket URL
            use_ssl: Use HTTPS for connections
        """
        self.stream_id = stream_id
        self.url = url
        self.use_ssl = use_ssl
        self.running = False
        self.websocket = None

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        import websockets

        ws_url = f"wss://localhost:8765" if self.use_ssl else f"ws://localhost:8765"

        self.websocket = await websockets.connect(ws_url)
        self.running = True

        # Subscribe to stream
        await self.websocket.send(
            json.dumps(
                {
                    "type": MessageType.SUBSCRIBE,
                    "streams": [self.stream_id],
                    "events": ["all"],
                }
            )
        )

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


class CLIDashboard:
    """CLI dashboard for real-time execution monitoring."""

    def __init__(
        self,
        stream_id: str | None = None,
        execution_id: str | None = None,
        format_type: str = "default",
        stream_url: str = "localhost",
        port: int = 8765,
    ):
        """
        Initialize CLI dashboard.

        Args:
            stream_id: Filter by stream ID
            execution_id: Filter by execution ID
            format_type: Output format (default, verbose, json)
            stream_url: WebSocket server host
            port: WebSocket server port
        """
        self.stream_id = stream_id
        self.execution_id = execution_id
        self.format_type = format_type
        self.stream_url = stream_url
        self.port = port
        self.active_executions: dict[str, dict[str, Any]] = {}
        self.event_log: list[dict[str, Any]] = []
        self.max_event_log_size = 50
        self.max_execution_display = 5

        self._event_bus = EventBus()
        self._event_bus.subscribe(
            event_types=list(self._event_bus.EventType),
            handler=self._on_event,
            filter_execution=execution_id,
        )

    async def _on_event(self, event: Any) -> None:
        """Handle event from EventBus.

        Args:
            event: Event from EventBus
        """
        event_dict = event.to_dict()

        if self.execution_id and event_dict.get("execution_id") != self.execution_id:
            return

        if self.stream_id and event_dict.get("stream_id") != self.stream_id:
            return

        # Update active executions
        execution_id = event_dict.get("execution_id", "unknown")
        if execution_id not in self.active_executions:
            self.active_executions[execution_id] = {
                "stream_id": event_dict.get("stream_id", "unknown"),
                "status": "running",
                "node_id": "",
                "node_name": "",
                "started_at": None,
                "completed_at": None,
            }

        # Update execution state
        event_type = event_dict.get("type")

        if event_type == "execution_started":
            self.active_executions[execution_id] = {
                "stream_id": event_dict.get("stream_id", "unknown"),
                "status": "running",
                "node_id": "",
                "node_name": "",
                "started_at": datetime.now(),
                "completed_at": None,
            }
        elif event_type == "node_started":
            self.active_executions[execution_id]["node_id"] = event_dict.get("node_id", "")
            self.active_executions[execution_id]["node_name"] = event_dict.get("data", {}).get(
                "node_name", ""
            )
        elif event_type == "node_completed":
            execution = self.active_executions.get(execution_id, {})
            execution["status"] = "completed"
            execution["completed_at"] = datetime.now()
        elif event_type == "node_failed":
            execution = self.active_executions.get(execution_id, {})
            execution["status"] = "failed"
            execution["completed_at"] = datetime.now()

        # Add to event log
        self.event_log.append(
            {
                "timestamp": datetime.now(),
                "stream_id": event_dict.get("stream_id", ""),
                "event_type": event_type,
                "execution_id": execution_id,
                "data": event_dict.get("data", {}),
            }
        )

        if len(self.event_log) > self.max_event_log_size:
            self.event_log = self.event_log[-self.max_event_log_size :]

    def render_default(self) -> Any:
        """Render dashboard in default format."""
        layout = Layout()

        # Active executions table
        executions_table = Table(
            title="Active Executions",
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE,
        )
        executions_table.add_column("Execution ID", style="cyan", no_wrap=True)
        executions_table.add_column("Stream", style="green")
        executions_table.add_column("Node", style="yellow", no_wrap=True)
        executions_table.add_column("Status", style="bold")
        executions_table.add_column("Duration", style="white")

        # Add active executions
        for exec_id, exec_data in sorted(
            self.active_executions.items(),
            key=lambda x: x[1].get("started_at", datetime.now()),
            reverse=True,
        )[: self.max_execution_display]:
            duration = "-"
            if exec_data.get("started_at"):
                if exec_data.get("completed_at"):
                    duration = str(exec_data["completed_at"] - exec_data["started_at"])
                else:
                    duration = str(datetime.now() - exec_data["started_at"])

            executions_table.add_row(
                exec_id[:20],
                exec_data["stream_id"][:8],
                exec_data["node_name"][:20] or "idle",
                exec_data["status"].upper(),
                duration,
            )

        # Recent events table
        events_table = Table(
            title="Recent Events",
            show_header=True,
            header_style="bold blue",
            box=box.SIMPLE,
        )
        events_table.add_column("Time", style="dim")
        events_table.add_column("Stream", style="green")
        events_table.add_column("Event Type", style="bold yellow")
        events_table.add_column("Execution", style="cyan")

        for event in reversed(self.event_log[-10:]):
            time_str = event["timestamp"].strftime("%H:%M:%S") if event["timestamp"] else ""
            events_table.add_row(
                time_str,
                event["stream_id"][:6],
                event["event_type"][:20],
                event["execution_id"][:12],
            )

        # Layout
        layout.split_column(
            Layout(name="executions"),
            Layout(name="events"),
        )

        layout["executions"].update(executions_table)
        layout["events"].update(events_table)

        return layout

    def render_verbose(self) -> Any:
        """Render dashboard in verbose format."""
        console.print(f"\n{'=' * 80}")
        console.print(f"HIVE AGENT MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"{'=' * 80}\n")

        # Active executions
        console.print("\n[bold magenta]Active Executions:[/bold magenta]")
        for exec_id, exec_data in sorted(
            self.active_executions.items(),
            key=lambda x: x[1].get("started_at", datetime.now()),
            reverse=True,
        ):
            console.print(f"\n  Execution ID: {exec_id}")
            console.print(f"  Stream: {exec_data['stream_id']}")
            console.print(f"  Status: [bold green]{exec_data['status']}[/bold green]")
            console.print(f"  Node: {exec_data['node_name'] or 'idle'}")
            console.print(f"  Started: {exec_data['started_at']}")
            console.print(f"  Completed: {exec_data['completed_at']}")

        # Recent events
        console.print(f"\n\n[bold blue]Recent Events:[/bold blue]")
        for event in reversed(self.event_log[-15:]):
            console.print(
                f"\n  [{event['timestamp'].strftime('%H:%M:%S')}] {event['stream_id']} -> {event['event_type']}"
            )
            if event["data"]:
                console.print(f"    Data: {json.dumps(event['data'], indent=4)}")

        console.print(f"\n{'=' * 80}\n")

    def render_json(self) -> None:
        """Render dashboard in JSON format."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "format": self.format_type,
            "active_executions": self.active_executions,
            "event_log": [
                {
                    "timestamp": e["timestamp"].isoformat() if e["timestamp"] else None,
                    "stream_id": e["stream_id"],
                    "event_type": e["event_type"],
                    "execution_id": e["execution_id"],
                    "data": e["data"],
                }
                for e in reversed(self.event_log[-10:])
            ],
        }

        console.print(json.dumps(output, indent=2))

    async def run(self) -> None:
        """Run the CLI dashboard."""
        if self.format_type == "json":
            # Just emit events once and exit
            console.print(
                json.dumps(
                    {
                        "status": "connected",
                        "active_executions": self.active_executions,
                        "event_log": [],
                    }
                )
            )
            return

        console.print(f"\n🐝 HIVE AGENT MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"\nStream: {self.stream_id or 'all'}")
        console.print(f"Execution: {self.execution_id or 'all'}")
        console.print(f"Format: {self.format_type}")
        console.print(f"\n[bold green]Listening for events...[/bold green]\n")

        # Start background event processing
        asyncio.create_task(self._event_processor())

        try:
            if self.format_type == "default":
                with Live(self.render_default(), refresh_per_second=4) as live:
                    while True:
                        await asyncio.sleep(0.25)
                        live.update(self.render_default())
            elif self.format_type == "verbose":
                while True:
                    await asyncio.sleep(0.5)
                    self.render_verbose()
            else:
                console.print(f"\n[bold red]Unknown format: {self.format_type}[/bold red]")
                sys.exit(1)

        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]Stopping dashboard...[/bold yellow]")

    async def _event_processor(self) -> None:
        """Process events from EventBus."""
        while True:
            await asyncio.sleep(0.01)


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Hive Agent Monitor - Real-time execution dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch all executions
  python -m framework.streaming.cli

  # Watch specific stream
  python -m framework.streaming.cli --stream webhook

  # Watch specific execution
  python -m framework.streaming.cli --execution exec_12345

  # Verbose output
  python -m framework.streaming.cli --format verbose

  # JSON output for piping
  python -m framework.streaming.cli --format json | jq '.'
        """,
    )

    parser.add_argument(
        "--stream",
        type=str,
        help="Filter by stream ID (e.g., webhook, api)",
    )
    parser.add_argument(
        "--execution",
        type=str,
        help="Filter by execution ID",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["default", "verbose", "json"],
        default="default",
        help="Output format (default: auto, verbose: human, json: machine)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="WebSocket server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)",
    )

    args = parser.parse_args()

    dashboard = CLIDashboard(
        stream_id=args.stream,
        execution_id=args.execution,
        format_type=args.format,
        stream_url=args.host,
        port=args.port,
    )

    await dashboard.run()


if __name__ == "__main__":
    asyncio.run(main())
