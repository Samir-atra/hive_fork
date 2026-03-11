# Real-time Execution Streaming Dashboard

A real-time execution monitoring system for the Hive agent framework. Provides three interfaces for watching agent executions:

- **WebSocket Server** - Backend for real-time event streaming
- **CLI Dashboard** - Terminal-based monitoring tool
- **Web Dashboard** - Browser-based UI for visual monitoring

## Features

### Event Infrastructure

The system adds granular event types to the EventBus for real-time monitoring:

- **Node Events**: `node_started`, `node_completed`, `node_failed`
- **LLM Call Events**: `llm_call_started`, `llm_call_completed`, `llm_tool_use`
- **Decision Events**: `decision_made`, `decision_outcome`
- **Memory Events**: `memory_write`, `memory_read`

These events are emitted throughout the execution lifecycle, providing real-time visibility into agent behavior.

### WebSocket Server

A WebSocket server that connects to the EventBus and pushes events to connected clients in real-time.

**Features**:
- Real-time event streaming
- Client authentication with optional token
- Event filtering by stream, execution, and event type
- Graceful client disconnection handling
- Server statistics tracking

**Usage**:
```python
from framework.streaming.server import StreamingServer
from framework.runtime.event_bus import EventBus

# Create event bus
event_bus = EventBus()

# Create streaming server
server = StreamingServer(
    event_bus=event_bus,
    host="localhost",
    port=8765,
    auth_token="optional-secret",
)

# Start server
await server.start()

# Clients can connect to ws://localhost:8765
```

### CLI Dashboard

A terminal-based dashboard for monitoring executions in real-time.

**Features**:
- Watch all executions
- Filter by stream ID
- Filter by execution ID
- Multiple output formats (default, verbose, JSON)
- Real-time updates

**Usage**:
```bash
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
```

**Output Examples**:

Default format:
```
🐝 HIVE AGENT MONITOR - 2026-01-27 12:03:05

Stream: all
Execution: all
Listening for events...

╔════════════════════════════════════════════════════════════════════╗
║ Active Executions:                                                  ║
╠════════════════════════════════════════════════════════════════════╣
║ exec_webhook_a1b2c3d4 │ webhook │ ▶ process-ticket   │ 1.2s        ║
║ exec_api_e5f6g7h8     │ api     │ ▶ generate-response │ 0.5s        ║
╚════════════════════════════════════════════════════════════════════╝

Recent Events:
12:03:05 │ webhook │ execution_started │ exec_webhook_a1b2c3d4
12:03:04 │ api     │ decision_made     │ chose: escalate
12:03:03 │ webhook │ node_completed    │ validate-input ✓
```

### Web Dashboard

A browser-based UI for visual monitoring with:

- Execution tree visualization
- Memory inspector
- Event log
- Real-time updates
- Connection management

**Usage**:
1. Start the WebSocket server:
   ```python
   await server.start()
   ```

2. Open the web dashboard:
   ```
   file:///path/to/hive_fork/core/framework/streaming/static/index.html
   ```

3. Click "Connect" to establish a WebSocket connection

**Features**:
- Color-coded execution status (running, completed, failed)
- Animated progress indicators
- Filter by execution ID
- Auto-scrolling event log
- Responsive design

## Architecture

### Event Flow

```
Agent Execution
    ↓
EventBus (publishes events)
    ↓
StreamingServer (subscribes to events)
    ↓
WebSocket Client (real-time delivery)
    ↓
CLI Dashboard / Web Dashboard
```

### Components

1. **EventBus Extensions**
   - New granular event types (node, LLM, decision, memory)
   - Event emission methods for all event types

2. **GraphExecutor Updates**
   - Emits `node_failed` event when max retries exceeded
   - Emits `memory_read` event when reading from shared memory

3. **StreamingServer**
   - WebSocket server implementation
   - Subscription management
   - Event filtering and routing

4. **Protocol**
   - WebSocket message format definitions
   - Message parsing and serialization
   - Constants for message types and filters

5. **CLI Dashboard**
   - Terminal UI with rich library
   - Real-time event processing
   - Multiple output formats

6. **Web Dashboard**
   - Single-page HTML/JS application
   - WebSocket client
   - Event rendering and filtering

## Configuration

### WebSocket Server

```python
server = StreamingServer(
    event_bus=event_bus,      # EventBus instance
    host="localhost",          # Bind host
    port=8765,                 # Listen port
    auth_token="secret",       # Optional authentication
    max_history=1000,          # Max event history
)
```

### CLI Dashboard

```bash
python -m framework.streaming.cli \
    --stream webhook \           # Filter by stream
    --execution exec_12345 \     # Filter by execution
    --format verbose \           # Output format
    --host localhost \           # WebSocket server host
    --port 8765                  # WebSocket server port
```

## Security

- WebSocket server binds to localhost by default
- Optional authentication token support
- No sensitive data in events (memory values are sanitized)
- Rate limiting for subscriptions

## Testing

Run protocol tests:
```bash
cd core && uv run pytest tests/test_streaming_protocol.py -v
```

Run all tests:
```bash
cd core && uv run pytest tests/ -v
```

## Dependencies

- `websockets` - WebSocket server and client
- `rich` - Terminal UI for CLI dashboard

## Future Enhancements

- [ ] Memory value sanitization for sensitive data
- [ ] Rate limiting for event subscriptions
- [ ] Persistent event storage
- [ ] Multiple WebSocket endpoint support
- [ ] Event replay functionality
- [ ] Advanced filtering and search
- [ ] Historical data visualization

## License

See main Hive license.
