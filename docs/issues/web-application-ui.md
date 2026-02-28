# Web Application - Modern Web UI for Hive Framework

## Overview
Implement a modern web-based user interface that replaces/enhances the existing Terminal UI (TUI), enabling users to interact with Hive's full capabilities through a browser. The interface should provide access to all Hive modes including building, testing, debugging, and other operational modes.

---

## Scope

**From Roadmap (Open Hive > TUI to GUI Upgrade):**
- [ ] Modern web UI framework setup (React/Vue/Svelte)
- [ ] Responsive design implementation
- [ ] Cross-browser compatibility

---

## Requirements

### 1. Technology Stack
- **Frontend Framework**: TypeScript-based React/Vue/Svelte (recommend React with TypeScript for ecosystem support)
- **Build Tool**: Vite or similar modern bundler
- **Styling**: Tailwind CSS or similar utility-first framework for responsive design
- **State Management**: Zustand, Redux Toolkit, or similar

### 2. Core Features

**Hive Mode Integration:**

| Mode | Description |
|------|-------------|
| **Build Mode** | Create and configure new agents using Hive Coder |
| **Test Mode** | Run agent tests, view results, debug failures |
| **Debug Mode** | Inspect checkpoints, memory, step-through execution |
| **Run Mode** | Execute agents with real-time streaming output |
| **Info Mode** | View agent metadata, configuration, dependencies |

**UI Components:**
- Agent selector/switcher
- Mode toggle/navigation
- Chat interface with streaming support
- Real-time log viewer
- Graph visualization (future: React Flow integration)
- Memory/state inspector
- Credential management panel

### 3. Responsive Design
- Mobile-first approach
- Breakpoints: mobile (<640px), tablet (640-1024px), desktop (>1024px)
- Collapsible sidebars for smaller screens
- Touch-friendly controls

### 4. Cross-Browser Compatibility
- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)

---

## Technical Specifications

```
web/
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   ├── AgentSelector/
│   │   ├── ModeSelector/
│   │   ├── LogViewer/
│   │   └── MemoryInspector/
│   ├── hooks/
│   ├── services/
│   │   └── hive-api.ts        # TypeScript API client
│   ├── stores/
│   ├── types/
│   └── App.tsx
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## API Integration Points

The web UI should connect to existing Hive backend:
- **Event Bus** (`runtime/event_bus.py`) - real-time streaming
- **Agent Runtime** (`runtime/agent_runtime.py`) - lifecycle control
- **Session Store** (`storage/session_store.py`) - state persistence
- **Test Framework** (`testing/`) - test execution and results

---

## Acceptance Criteria
- [ ] TypeScript project scaffolded with chosen framework
- [ ] Responsive layout works across all breakpoints
- [ ] All Hive modes accessible from UI
- [ ] Real-time streaming from Event Bus functional
- [ ] Cross-browser testing passes
- [ ] TUI feature parity achieved

---

## Related Roadmap Items
- TUI to GUI Upgrade (Open Hive section)
- Local API Gateway (for browser-to-backend communication)
- Visual Graph Explorer (future integration)
- Memory & State Inspector
- Local Control Panel
