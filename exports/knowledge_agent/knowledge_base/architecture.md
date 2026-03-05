# Hive Architecture Deep Dive

## Core Concepts

### Graph Specification
The GraphSpec is the central configuration object that defines an agent:
- **Nodes**: List of node specifications
- **Edges**: Connections between nodes
- **Entry Points**: Starting points for execution
- **Terminal Nodes**: End points that stop execution
- **Loop Configuration**: Settings for iterative execution

### Node Execution Flow

1. **Entry Point**: Execution starts at the entry node
2. **Node Execution**: Each node executes and produces outputs
3. **Memory Update**: Outputs are stored in SharedMemory
4. **Edge Evaluation**: Conditions are checked to determine next node
5. **Loop or Terminate**: Continue to next node or stop at terminal node

### Memory Management

#### SharedMemory
```python
# Read data from memory
value = memory.read("key")

# Write data to memory
memory.write("key", value)

# Create scoped view with permissions
node_memory = memory.with_permissions(
    read_keys=["input1", "input2"],
    write_keys=["output1"]
)
```

#### StreamMemory (for concurrent execution)
```python
# Create stream memory
manager = SharedStateManager()
memory = manager.create_memory(
    execution_id="exec_123",
    isolation=IsolationLevel.SHARED
)

# Async operations
await memory.write("key", value)
value = await memory.read("key")
```

## Node Types Explained

### Event Loop Node
The most powerful node type that uses LLM reasoning:
- Processes input data
- Calls tools as needed
- Generates outputs
- Can interact with users (if client-facing)

**Configuration:**
- `system_prompt`: Instructions for the LLM
- `tools`: List of available tools
- `input_keys`: Data to read from memory
- `output_keys`: Data to write to memory
- `client_facing`: Whether node interacts with end user

### Worker Node
Simple processing nodes for non-LLM tasks:
- Data transformation
- API calls
- File operations

### Decision Node
Nodes that make routing decisions:
- Evaluate conditions
- Choose execution paths
- Support complex logic

## Tool System

### MCP Tools
Model Context Protocol tools provide:
- Standardized tool interface
- External server integration
- Tool discovery and registration

### Custom Tools
Create custom tools as Python functions:
```python
@tool(description="My custom tool")
def my_tool(param: str) -> dict:
    # Tool implementation
    return {"result": "value"}
```

### Tool Registry
The ToolRegistry manages all tools:
- Load MCP tools from config
- Register custom tools
- Provide tool executor for nodes

## Edge Conditions

### ON_SUCCESS
Proceed when node completes successfully:
```python
EdgeSpec(
    source="node_a",
    target="node_b",
    condition=EdgeCondition.ON_SUCCESS
)
```

### ON_FAILURE
Proceed when node fails:
```python
EdgeSpec(
    source="node_a",
    target="error_handler",
    condition=EdgeCondition.ON_FAILURE
)
```

### CONDITIONAL
Proceed based on output evaluation:
```python
EdgeSpec(
    source="classifier",
    target="urgent_handler",
    condition=EdgeCondition.CONDITIONAL,
    condition_expr="priority == 'urgent'"
)
```

## Checkpointing

Hive supports execution checkpointing:
- Save agent state at node completion
- Resume from last checkpoint
- Configurable checkpoint frequency
- Automatic cleanup of old checkpoints

Configuration:
```python
checkpoint_config = CheckpointConfig(
    enabled=True,
    checkpoint_on_node_complete=True,
    checkpoint_max_age_days=7
)
```

## Conversation Modes

### Continuous Mode
Agent maintains conversation across executions:
- History preserved
- Context maintained
- Multi-turn interactions

### Single-Shot Mode
Each execution is independent:
- No history between runs
- Stateless execution
- Suitable for batch processing

## Performance Considerations

1. **Token Limits**: Configure max_history_tokens to control context size
2. **Loop Limits**: Set max_iterations to prevent infinite loops
3. **Tool Call Limits**: Limit max_tool_calls_per_turn to control costs
4. **Checkpointing**: Balance frequency vs. storage costs
