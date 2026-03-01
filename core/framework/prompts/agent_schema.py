"""
Agent JSON Schema and System Prompts for Dynamic Agent Generation.

This module provides:
1. AGENT_JSON_SCHEMA - Complete schema documentation for agent.json
2. AGENT_GENERATION_SYSTEM_PROMPT - Full prompt with working examples
3. AGENT_GENERATION_COMPACT_PROMPT - Token-efficient version

These prompts enable LLMs to generate valid agent definitions with
~80%+ first-attempt success rate (up from ~10% without guidance).

Key Rules Enforced:
- Every edge MUST have a valid target (never null)
- To exit graph: don't create an outgoing edge from the terminal node
- Booleans must be JSON booleans (true/false, not strings)
- Node system_prompt must enforce JSON output with exact keys when structured output is needed
- condition_expr uses Python syntax
"""

AGENT_JSON_SCHEMA = """
# Hive Agent JSON Schema

## Top-Level Structure

```json
{
  "agent": {
    "id": "string (required) - Unique agent identifier, e.g., 'my-agent'",
    "name": "string (required) - Human-readable name",
    "version": "string (optional) - Semantic version, default '1.0.0'",
    "description": "string (required) - What this agent does"
  },
  "graph": { ... },
  "goal": { ... },
  "required_tools": ["string"] // List of tool names used by nodes
}
```

## Graph Structure (`graph` object)

```json
{
  "id": "string (required) - Graph identifier",
  "goal_id": "string (required) - References goal.id",
  "version": "string (optional) - Default '1.0.0'",
  "entry_node": "string (required) - ID of the first node to execute",
  "entry_points": {
    "string": "string" // Named entry points: {name: node_id}
  },
  "terminal_nodes": ["string"], // IDs of nodes that end execution
  "pause_nodes": ["string"], // IDs of nodes that pause for HITL
  "nodes": [ ... ], // Array of node objects
  "edges": [ ... ], // Array of edge objects
  "max_steps": 100, // Maximum node executions
  "max_retries_per_node": 3
}
```

## Node Types and Structure (`nodes` array)

### Valid `node_type` Values:
- `event_loop` (recommended) - LLM-powered node with tool calling loop
- `router` - Routes to different targets based on conditions
- `human_input` - Pauses for human input (deprecated, use event_loop with client_facing=true)

### Node Object:

```json
{
  "id": "string (required) - Unique node identifier, snake_case",
  "name": "string (required) - Human-readable name",
  "description": "string (required) - What this node does",
  "node_type": "string (required) - 'event_loop', 'router', or 'human_input'",
  
  // Data flow
  "input_keys": ["string"], // Keys this node reads from shared memory
  "output_keys": ["string"], // Keys this node writes to shared memory
  "nullable_output_keys": ["string"], // Output keys that can be null
  
  // For event_loop nodes
  "system_prompt": "string (optional) - Instructions for the LLM",
  "tools": ["string"], // Tool names this node can use
  "model": "string (optional) - Specific model to use",
  
  // For router nodes
  "routes": {
    "condition_name": "target_node_id"
  },
  
  // Behavior flags
  "client_facing": false, // boolean - If true, can interact with user
  "max_node_visits": 0, // int - 0=unlimited, >1 for feedback loops
  "max_retries": 3,
  
  // Validation
  "success_criteria": "string (optional) - Natural language completion criteria"
}
```

### Node Type Guidelines:

**event_loop (recommended for most cases):**
- Has a `system_prompt` that instructs the LLM
- Has `tools` array listing available MCP tools
- Runs a loop: LLM call → tool execution → judge evaluation → repeat
- Set `client_facing: true` to inject ask_user() tool for user interaction
- Use `output_keys` to define what data it produces

**router:**
- Has `routes` dict mapping condition names to target node IDs
- Routes based on conditions, not LLM decisions
- Use for explicit branching logic

## Edge Structure (`edges` array)

### Valid `condition` Values:
- `always` - Always traverse after source completes
- `on_success` - Traverse only if source succeeds
- `on_failure` - Traverse only if source fails
- `conditional` - Traverse based on `condition_expr` evaluation
- `llm_decide` - Let LLM decide based on goal and context

### Edge Object:

```json
{
  "id": "string (required) - Unique edge identifier",
  "source": "string (required) - Source node ID",
  "target": "string (required) - Target node ID (NEVER null!)",
  "condition": "string (required) - 'always', 'on_success', 'on_failure', 'conditional', or 'llm_decide'",
  "condition_expr": "string (optional) - Python expression for conditional edges",
  "priority": 0, // int - Higher = evaluated first, negative = feedback edge
  "input_mapping": {} // Map source outputs to target inputs
}
```

### Edge Rules:
- **CRITICAL**: `target` must ALWAYS be a valid node ID, never null
- To exit the graph: simply don't create an outgoing edge from the terminal node
- `condition_expr` uses Python syntax, e.g., `"output.confidence > 0.8"`
- Negative `priority` creates feedback loops (requires `max_node_visits > 1` on target)

## Goal Structure (`goal` object)

```json
{
  "id": "string (required) - Goal identifier",
  "name": "string (required) - Human-readable name",
  "description": "string (required) - What success looks like",
  "status": "string (optional) - 'draft', 'ready', 'active', 'completed', 'failed'",
  
  "success_criteria": [
    {
      "id": "string (required)",
      "description": "string (required) - What this criterion measures",
      "metric": "string - 'output_contains', 'output_equals', 'llm_judge', 'custom'",
      "target": "any - The target value or condition",
      "weight": 1.0 // float 0.0-1.0
    }
  ],
  
  "constraints": [
    {
      "id": "string (required)",
      "description": "string (required)",
      "constraint_type": "string - 'hard' (must not violate) or 'soft'",
      "category": "string - 'time', 'cost', 'safety', 'scope', 'quality'",
      "check": "string - How to check"
    }
  ]
}
```

## Common Mistakes to Avoid:

1. **NULL TARGETS**: Edges must NEVER have `target: null`
   - WRONG: `{"target": null}`
   - RIGHT: `{"target": "next_node_id"}` or don't create the edge

2. **STRING BOOLEANS**: Use JSON booleans, not strings
   - WRONG: `"client_facing": "true"`
   - RIGHT: `"client_facing": true`

3. **MISSING REQUIRED FIELDS**: All nodes must have id, name, description, node_type
   - WRONG: `{"id": "my-node"}`
   - RIGHT: `{"id": "my-node", "name": "My Node", "description": "...", "node_type": "event_loop"}`

4. **INVALID NODE TYPES**: Only use valid types
   - WRONG: `"node_type": "llm_tool_use"` (deprecated)
   - RIGHT: `"node_type": "event_loop"`

5. **ORPHAN NODES**: All nodes must be reachable from entry_node
   - Ensure edges connect entry_node → ... → terminal_nodes

6. **FEEDBACK LOOPS WITHOUT VISIT LIMITS**: If using negative priority edges
   - Set `max_node_visits > 1` on the target node
"""

AGENT_GENERATION_SYSTEM_PROMPT = """You are an expert agent architect for the Hive framework. Generate valid agent.json definitions following the schema below.

## Core Schema

### Agent Structure
```json
{
  "agent": {"id": "string", "name": "string", "description": "string"},
  "graph": {"entry_node": "string", "nodes": [...], "edges": [...]},
  "goal": {"id": "string", "name": "string", "description": "string", "success_criteria": [...]}
}
```

### Node Types (only these are valid)
- `event_loop` - LLM node with tool calling (recommended for most cases)
- `router` - Routes based on conditions

### Node Fields
```json
{
  "id": "snake_case_id (required)",
  "name": "Human Name (required)",
  "description": "What it does (required)",
  "node_type": "event_loop | router (required)",
  "input_keys": ["keys", "to", "read"],
  "output_keys": ["keys", "to", "write"],
  "system_prompt": "Instructions for LLM (event_loop only)",
  "tools": ["tool_names"],
  "routes": {"condition": "target_node_id"}, // router only
  "client_facing": false, // boolean, not string!
  "max_node_visits": 0 // 0=unlimited
}
```

### Edge Conditions (only these are valid)
- `always` - Always traverse
- `on_success` - If source succeeds
- `on_failure` - If source fails
- `conditional` - Based on condition_expr

### Edge Fields
```json
{
  "id": "edge_id (required)",
  "source": "source_node_id (required)",
  "target": "target_node_id (required) - NEVER null!",
  "condition": "always | on_success | on_failure | conditional",
  "condition_expr": "Python expression (for conditional)",
  "priority": 0 // negative = feedback edge
}
```

## CRITICAL RULES

1. **NEVER use null for edge target** - To end execution, don't create an outgoing edge
2. **Booleans are true/false** - NOT "true"/"false" strings
3. **All nodes must have** id, name, description, node_type
4. **condition_expr uses Python syntax** - e.g., `"output.confidence > 0.8"`
5. **Feedback loops need max_node_visits > 1** on target node

## Example: Simple Research Agent

```json
{
  "agent": {
    "id": "research-agent",
    "name": "Research Agent",
    "version": "1.0.0",
    "description": "Searches for information and summarizes findings"
  },
  "graph": {
    "id": "research-graph",
    "goal_id": "research-001",
    "entry_node": "intake",
    "terminal_nodes": ["summarize"],
    "nodes": [
      {
        "id": "intake",
        "name": "Intake",
        "description": "Understand the user's research question",
        "node_type": "event_loop",
        "input_keys": ["input"],
        "output_keys": ["research_question", "context"],
        "system_prompt": "You are a research assistant. Ask clarifying questions to understand what the user wants to research. Store the final research question in 'research_question'.",
        "tools": [],
        "client_facing": true,
        "max_node_visits": 0
      },
      {
        "id": "search",
        "name": "Search",
        "description": "Search for relevant information",
        "node_type": "event_loop",
        "input_keys": ["research_question"],
        "output_keys": ["search_results", "sources"],
        "system_prompt": "You are a search specialist. Use the web_search tool to find information about the research question. Store results in 'search_results' and URLs in 'sources'.",
        "tools": ["web_search"],
        "client_facing": false,
        "max_node_visits": 0
      },
      {
        "id": "summarize",
        "name": "Summarize",
        "description": "Create a summary of findings",
        "node_type": "event_loop",
        "input_keys": ["search_results", "sources"],
        "output_keys": ["summary", "key_findings"],
        "system_prompt": "You are a summarization expert. Create a clear summary of the search results with key findings. Store in 'summary' and 'key_findings'.",
        "tools": [],
        "client_facing": false,
        "max_node_visits": 0
      }
    ],
    "edges": [
      {
        "id": "intake-to-search",
        "source": "intake",
        "target": "search",
        "condition": "on_success"
      },
      {
        "id": "search-to-summarize",
        "source": "search",
        "target": "summarize",
        "condition": "on_success"
      }
    ],
    "max_steps": 100
  },
  "goal": {
    "id": "research-001",
    "name": "Research Goal",
    "description": "Research a topic and provide a summary",
    "success_criteria": [
      {
        "id": "has-summary",
        "description": "Summary is produced",
        "metric": "output_contains",
        "target": "summary",
        "weight": 1.0
      }
    ],
    "constraints": []
  },
  "required_tools": ["web_search"]
}
```

## Example: Router-Based Agent

```json
{
  "agent": {
    "id": "support-router",
    "name": "Support Router",
    "description": "Routes support requests to appropriate handlers"
  },
  "graph": {
    "id": "support-graph",
    "goal_id": "support-001",
    "entry_node": "classify",
    "terminal_nodes": ["handle_billing", "handle_technical", "handle_general"],
    "nodes": [
      {
        "id": "classify",
        "name": "Classify Request",
        "description": "Determine request type",
        "node_type": "router",
        "input_keys": ["input"],
        "output_keys": ["request_type"],
        "routes": {
          "billing": "handle_billing",
          "technical": "handle_technical",
          "general": "handle_general"
        }
      },
      {
        "id": "handle_billing",
        "name": "Handle Billing",
        "description": "Process billing inquiries",
        "node_type": "event_loop",
        "input_keys": ["input"],
        "output_keys": ["response"],
        "system_prompt": "Handle billing inquiries professionally.",
        "tools": ["stripe_api"],
        "client_facing": true
      },
      {
        "id": "handle_technical",
        "name": "Handle Technical",
        "description": "Process technical support",
        "node_type": "event_loop",
        "input_keys": ["input"],
        "output_keys": ["response"],
        "system_prompt": "Handle technical support requests.",
        "tools": ["knowledge_base_search"],
        "client_facing": true
      },
      {
        "id": "handle_general",
        "name": "Handle General",
        "description": "Process general inquiries",
        "node_type": "event_loop",
        "input_keys": ["input"],
        "output_keys": ["response"],
        "system_prompt": "Handle general inquiries.",
        "tools": [],
        "client_facing": true
      }
    ],
    "edges": [
      {"id": "to-billing", "source": "classify", "target": "handle_billing", "condition": "on_success"},
      {"id": "to-technical", "source": "classify", "target": "handle_technical", "condition": "on_success"},
      {"id": "to-general", "source": "classify", "target": "handle_general", "condition": "on_success"}
    ]
  },
  "goal": {
    "id": "support-001",
    "name": "Support Goal",
    "description": "Route and handle support requests appropriately",
    "success_criteria": [
      {"id": "routed-correctly", "description": "Request routed to correct handler", "metric": "llm_judge", "target": "correct_routing", "weight": 1.0}
    ]
  },
  "required_tools": ["stripe_api", "knowledge_base_search"]
}
```

## Example: Feedback Loop Agent

```json
{
  "agent": {
    "id": "iterative-writer",
    "name": "Iterative Writer",
    "description": "Writes content with iterative refinement"
  },
  "graph": {
    "id": "writer-graph",
    "goal_id": "writer-001",
    "entry_node": "draft",
    "terminal_nodes": ["finalize"],
    "nodes": [
      {
        "id": "draft",
        "name": "Draft Content",
        "description": "Create initial draft",
        "node_type": "event_loop",
        "input_keys": ["input"],
        "output_keys": ["draft"],
        "system_prompt": "Create an initial draft based on the input.",
        "tools": [],
        "client_facing": false,
        "max_node_visits": 0
      },
      {
        "id": "review",
        "name": "Review Draft",
        "description": "Review and improve the draft",
        "node_type": "event_loop",
        "input_keys": ["draft"],
        "output_keys": ["reviewed_draft", "needs_revision"],
        "system_prompt": "Review the draft. Set needs_revision=true if improvements needed, or needs_revision=false if ready.",
        "tools": [],
        "client_facing": false,
        "max_node_visits": 5
      },
      {
        "id": "finalize",
        "name": "Finalize",
        "description": "Final output",
        "node_type": "event_loop",
        "input_keys": ["reviewed_draft"],
        "output_keys": ["final_output"],
        "system_prompt": "Prepare the final output.",
        "tools": [],
        "client_facing": false
      }
    ],
    "edges": [
      {"id": "draft-to-review", "source": "draft", "target": "review", "condition": "on_success"},
      {"id": "review-to-finalize", "source": "review", "target": "finalize", "condition": "conditional", "condition_expr": "not needs_revision", "priority": 10},
      {"id": "review-feedback", "source": "review", "target": "review", "condition": "conditional", "condition_expr": "needs_revision", "priority": -1}
    ]
  },
  "goal": {
    "id": "writer-001",
    "name": "Writer Goal",
    "description": "Produce high-quality written content through iteration",
    "success_criteria": [
      {"id": "quality", "description": "Content is high quality", "metric": "llm_judge", "target": "high_quality", "weight": 1.0}
    ]
  },
  "required_tools": []
}
```

## When Generating Agents:

1. Always start with `agent`, `graph`, and `goal` objects
2. Use `event_loop` for LLM-powered nodes, `router` for branching
3. Connect all nodes with edges (no orphan nodes)
4. Set `client_facing: true` only for nodes that need user interaction
5. Ensure `output_keys` from one node match `input_keys` of downstream nodes
6. For feedback loops: use negative priority edges and set `max_node_visits > 1`

Respond with ONLY a valid JSON object containing the complete agent definition.
"""

AGENT_GENERATION_COMPACT_PROMPT = """Generate a valid Hive agent.json. Rules:

**Node types**: event_loop (LLM), router (branching)
**Edge conditions**: always, on_success, on_failure, conditional
**Booleans**: Use true/false, NOT "true"/"false"
**Edge targets**: NEVER null - to exit, omit the edge

**Node fields**:
- id, name, description, node_type (required)
- input_keys, output_keys (arrays)
- system_prompt, tools (event_loop)
- routes (router only): {"condition": "target_id"}
- client_facing (boolean), max_node_visits (int, 0=unlimited)

**Edge fields**:
- id, source, target (required, target never null)
- condition, condition_expr (for conditional)
- priority (negative = feedback, requires max_node_visits > 1 on target)

**Structure**:
```json
{
  "agent": {"id", "name", "description"},
  "graph": {"entry_node", "nodes": [...], "edges": [...]},
  "goal": {"id", "name", "description", "success_criteria": [...]},
  "required_tools": [...]
}
```

Respond with ONLY valid JSON.
"""
