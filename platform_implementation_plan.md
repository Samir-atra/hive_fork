# Implementation Plan: Hive Unified Web Platform

This plan outlines the architecture and phased implementation of the Hive Unified Web Platform, as described in Issue #3144. The platform aims to amplify Hive's goal-driven intelligence by making the invisible visible.

## 1. Technology Stack & Design Philosophy

- **Foundation**: [Vite](https://vitejs.dev/) for a fast, modern build pipeline.
- **Logic**: Vanilla JavaScript with a custom reactive state management system.
- **Styling**: Vanilla CSS with a focus on CSS Variables for the design system.
- **Aesthetics**: Premium, high-contrast dark mode with vibrant accents, glassmorphism details, and dynamic SVG-based animations.
- **Typography**: Inter (Modern sans-serif) with high-legibility scales.

## 2. Platform Architecture

The frontend will reside in the `platform/` directory and will interact with the Hive backend via:
- **REST APIs**: For configuration, documentation, and history.
- **WebSockets/SSE**: For real-time event streaming via Hive's `EventBus`.

### Directory Structure:
```
platform/
├── index.html            # Main entry
├── src/
│   ├── main.js           # Core initialization
│   ├── styles/
│   │   ├── tokens.css     # Design tokens (colors, spacing)
│   │   ├── main.css      # Base styles & layout
│   │   └── modules/      # Module-specific styles
│   ├── components/       # Reusable UI elements (Buttons, Cards, Modals)
│   ├── modules/          # Distinct platform blocks (GoalStudio, EvolutionTheater, etc.)
│   ├── services/         # API and EventBus integration
│   └── utils/            # Graph rendering and formatting helpers
└── public/               # Static assets
```

## 3. Phased Roadmap

### Phase 1: Core Foundation & Design System (Priority: High)
- [ ] Initialize Vite project and setup `platform/` directory.
- [ ] Define the design system in `tokens.css` (Glassmorphism, Vibrant Blues/Purples, sleek dark mode).
- [ ] Implement the shell layout: Responsive Sidebar, Header with agent status, and Content Area.

### Phase 2: Documentation Hub & Goal Studio (Priority: High)
- [ ] **Docs Hub**: Markdown renderer to display files from Hive's `docs/` folder.
- [ ] **Goal Studio**: Intuitive interface for natural language input, success criteria refinement, and constraint definition.

### Phase 3: Live Generation & Execution Cinema (Priority: High)
- [ ] **Event Streaming**: Connect to `EventBus` to receive real-time build and execution events.
- [ ] **Live Generation View**: SVG-based graph visualization where nodes and edges appear with smooth transitions as Hive builds them.
- [ ] **Execution Cinema**: Step-by-step decision trail showing reasoning, tool calls, and LLM internal thoughts.

### Phase 4: Evolution & HITL (Priority: Medium)
- [ ] **Evolution Theater**: Graph diffing view to see changes between agent versions.
- [ ] **HITL Command Center**: Simplified approval cards for non-technical users.

### Phase 5: Intelligence & Optimization (Priority: Medium)
- [ ] **Learning Intelligence**: Visualization of failure patterns and improvement trends.
- [ ] **Cost Optimizer**: Performance metrics dashboard with budget insights.

## 4. Design Guidelines

- **Wow Factor**: Use subtle gradients and backdrop-filters (glassmorphism).
- **No Placeholders**: Use `generate_image` for backgrounds or iconography if needed.
- **Micro-animations**: Every state change should be animated (e.g., node appearing, status pulse).

## 5. Next Steps

1. Create the `platform/` directory and initialize Vite.
2. Build out the `tokens.css` and basic layout.
## 6. Backend Integration Strategy

To transition from mock data to real Hive intelligence, the following integration points will be established:

- **SSE (Server-Sent Events)**: The preferred method for streaming `EventBus` payloads to the UI.
    - `GET /api/v1/stream`: Streams events like `AGENT_BUILD_STEP`, `NODE_CREATED`, `EXECUTION_LIFECYCLE`.
- **WebSocket Protocol**: For bi-directional interactions in **Goal Studio** and **HITL Center**.
- **RESTful Endpoints**:
    - `GET /api/v1/docs`: Fetches directory structure and content of `docs/`.
    - `POST /api/v1/goals`: Initiates agent generation from a natural language goal.
    - `GET /api/v1/versions`: Retrieves agent evolution timeline data.

## 7. Business Value Alignment

| Feature | Stakeholder | Value |
| --- | --- | --- |
| **Execution Cinema** | Developers/DevOps | Faster debugging via reasoning transparency. |
| **HITL Center** | Business Managers | Safe oversight without technical friction. |
| **Evolution Theater** | Quality Assurance | Clear visibility into ROI of self-improvement cycles. |
| **Goal Studio** | Product Owners | Rapid prototyping from ideas to functional agents. |
