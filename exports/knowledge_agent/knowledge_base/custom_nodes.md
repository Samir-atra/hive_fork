# Building Custom Nodes in Hive

## Node Specification

Every node in Hive is defined using a NodeSpec object:

```python
from framework.graph import NodeSpec

my_node = NodeSpec(
    id="unique_node_id",
    name="Human Readable Name",
    description="What this node does",
    node_type="event_loop",
    system_prompt="Instructions for the LLM",
    tools=["tool1", "tool2"],
    input_keys=["input1", "input2"],
    output_keys=["output1", "output2"],
    client_facing=False,
    max_node_visits=0
)
```

## Node Properties

### id
Unique identifier for the node (required). Used in edges to reference the node.

### name
Human-readable name for display purposes.

### description
Brief description of what the node does. Used in documentation and debugging.

### node_type
Type of node execution:
- `"event_loop"`: LLM-powered reasoning node (most common)
- `"worker"`: Simple processing node
- `"decision"`: Routing decision node

### system_prompt
Instructions for the LLM (only for event_loop nodes). Should include:
1. Role and responsibilities
2. Step-by-step process
3. How to use tools
4. How to call set_output
5. Examples if helpful

### tools
List of tool names available to this node. Tools must be registered in the ToolRegistry.

### input_keys
Data keys to read from SharedMemory before execution.

### output_keys
Data keys to write to SharedMemory after execution. The node must call `set_output` for each key.

### nullable_output_keys
Optional keys that may or may not be set.

### client_facing
Whether this node interacts with end users. Enables conversation mode.

### max_node_visits
Maximum times this node can be visited in one execution. Use 0 for unlimited.

## Writing Effective System Prompts

### Structure
```
1. Role definition
2. Task description
3. Step-by-step process
4. Tool usage instructions
5. Output format requirements
6. Examples (if helpful)
```

### Best Practices

1. **Be Specific**: Clearly state what the node should do
2. **Provide Steps**: Break down complex tasks into steps
3. **Explain Tools**: Describe how and when to use each tool
4. **Show Examples**: Demonstrate expected inputs/outputs
5. **Set Constraints**: Define what the node should NOT do

### Example Prompt
```python
system_prompt="""\
You are a data validator. Your job is to check user input for correctness.

**STEP 1 — Validate input:**
1. Check if input exists
2. Check data types
3. Check for required fields
4. Validate format (emails, URLs, etc.)

**STEP 2 — Report results:**
Use set_output to report validation results:
- set_output("is_valid", "true" or "false")
- set_output("errors", "list of validation errors")
- set_output("warnings", "list of warnings")

**Examples:**
Input: {"email": "user@example.com"}
- is_valid: "true"
- errors: ""
- warnings: ""

Input: {"email": "invalid-email"}
- is_valid: "false"
- errors: "Invalid email format"
- warnings: ""
"""
```

## Input and Output Handling

### Reading Input
Input data is automatically loaded from SharedMemory based on input_keys:
```python
input_keys=["user_name", "user_email"]
# Node can access this data in its context
```

### Writing Output
Use the `set_output` tool (automatically provided):
```python
# In the system prompt, instruct the LLM to:
"Call set_output('key', 'value') to store results"
```

### Memory Scope
Each node has a scoped view of SharedMemory:
- Can only read keys in input_keys
- Can only write keys in output_keys
- Prevents accidental data corruption

## Tool Integration

### Available Tools
Specify which tools the node can use:
```python
tools=["web_scrape", "save_data", "query_database"]
```

### Tool Usage in Prompts
Explain in the system prompt when and how to use each tool:
```python
"""
Use web_scrape to fetch content from URLs:
- Call web_scrape(url="https://example.com")
- The tool returns the page content

Use save_data to persist results:
- Call save_data(filename="output.txt", data="content")
"""
```

## Client-Facing Nodes

### What are Client-Facing Nodes?
Nodes that interact directly with end users:
- Can send messages to users
- Can receive user responses
- Enable conversational interactions

### When to Use
- Intake nodes (collecting user input)
- Output nodes (presenting results)
- Interactive clarification
- Multi-turn conversations

### Example
```python
intake_node = NodeSpec(
    id="intake",
    name="User Intake",
    client_facing=True,
    system_prompt="Ask the user what they need help with..."
)
```

## Error Handling

### Handling Failures
Design edges to handle node failures:
```python
EdgeSpec(
    source="processing",
    target="error_handler",
    condition=EdgeCondition.ON_FAILURE
)
```

### Validation in Nodes
Include validation logic in system prompts:
```python
"""
Before processing:
1. Validate input exists
2. Check data types
3. Verify required fields

If validation fails:
- Call set_output with error information
- Do not proceed with processing
"""
```

## Testing Nodes

### Unit Testing
Test node behavior in isolation:
```python
def test_my_node():
    # Create test input
    input_data = {"test_key": "test_value"}
    
    # Execute node
    result = execute_node(my_node, input_data)
    
    # Verify output
    assert result.success
    assert "output_key" in result.output
```

### Integration Testing
Test node in the full agent workflow:
```python
def test_agent_workflow():
    agent = MyAgent()
    result = await agent.run({"input": "test"})
    
    assert result.success
    # Verify node was executed correctly
```

## Common Patterns

### Intake Pattern
```python
intake_node = NodeSpec(
    id="intake",
    client_facing=True,
    input_keys=[],
    output_keys=["user_request"],
    system_prompt="Ask user for input, then call set_output('user_request', value)"
)
```

### Processing Pattern
```python
process_node = NodeSpec(
    id="process",
    input_keys=["user_request"],
    output_keys=["processed_data"],
    tools=["external_api"],
    system_prompt="Process the request using available tools"
)
```

### Output Pattern
```python
output_node = NodeSpec(
    id="output",
    client_facing=True,
    input_keys=["processed_data"],
    output_keys=["delivered"],
    tools=["save_data"],
    system_prompt="Present results to user and save to file"
)
```
