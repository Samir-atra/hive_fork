# Hive Web Application

A modern TypeScript/React web interface for the Hive Agent Framework. This application provides a browser-based UI for building, running, testing, and debugging AI agents.

## Features

### Hive Modes

The web interface supports multiple operational modes accessible via the mode selector in the top bar:

| Mode | Description |
|------|-------------|
| **Build** | Create and configure new agents using the Queen Bee interface |
| **Run** | Execute agents with real-time streaming output |
| **Test** | Run agent tests and view results |
| **Debug** | Inspect checkpoints, memory, and step-through execution |
| **Info** | View agent metadata, configuration, and node overview |

### UI Components

- **Agent Graph** - Visual representation of agent node topology
- **Chat Panel** - Interactive chat interface with the Queen Bee
- **Node Detail Panel** - Inspect individual node state and logs
- **Credentials Modal** - Configure API keys and OAuth integrations
- **Mode Panels** - Context-specific panels for Test, Debug, and Info modes

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test
```

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS 4** - Styling
- **React Router 7** - Navigation
- **Lucide React** - Icons

## Responsive Design

The interface adapts to different screen sizes:

- **Mobile** (<640px) - Full-screen panels with slide-in transitions
- **Tablet** (640-1024px) - Collapsible sidebars
- **Desktop** (>1024px) - Multi-panel layout

## Project Structure

```
src/
├── api/              # API client and types
│   ├── client.ts     # Base fetch wrapper
│   ├── agents.ts     # Agent discovery API
│   ├── sessions.ts   # Session management
│   ├── execution.ts  # Execution control
│   ├── test.ts       # Test framework API
│   ├── debug.ts      # Debug API
│   └── types.ts      # TypeScript type definitions
├── components/       # React components
│   ├── ModeSelector.tsx
│   ├── TestPanel.tsx
│   ├── DebugPanel.tsx
│   ├── InfoPanel.tsx
│   ├── ChatPanel.tsx
│   ├── AgentGraph.tsx
│   └── ...
├── hooks/            # React hooks
│   ├── use-sse.ts    # Server-sent events
│   └── use-media-query.ts
├── lib/              # Utilities
├── pages/            # Page components
│   ├── home.tsx
│   ├── my-agents.tsx
│   └── workspace.tsx
├── App.tsx           # Route definitions
├── main.tsx          # Entry point
└── index.css         # Global styles
```

## Browser Support

- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)

## API Integration

The web interface connects to the Hive backend via:

- **REST API** - Session management, agent discovery, test execution
- **SSE (Server-Sent Events)** - Real-time streaming of LLM output, tool calls, and node transitions

### SSE Event Types

The interface handles the following event types:

- `execution_started` / `execution_completed` / `execution_failed`
- `llm_text_delta` / `client_output_delta`
- `tool_call_started` / `tool_call_completed`
- `node_loop_started` / `node_loop_iteration` / `node_loop_completed`
- `client_input_requested`
- And more...

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Command palette (planned) |
| `Escape` | Close modals/panels |

## License

Apache-2.0
