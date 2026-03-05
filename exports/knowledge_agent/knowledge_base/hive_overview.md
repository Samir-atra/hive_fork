# Hive Framework Overview

## What is Hive?

Hive is a goal-driven agent framework for building intelligent AI agents. It provides a structured approach to creating agents that can accomplish complex tasks through a graph-based execution model.

## Key Features

### 1. Goal-Driven Architecture
Agents in Hive are organized around achieving specific goals. Each agent has a clearly defined goal with success criteria and constraints. This makes agents more focused and easier to evaluate.

### 2. Graph-Based Execution
Hive uses a graph-based execution model where:
- **Nodes** represent individual tasks or decision points
- **Edges** define the flow between nodes
- **Conditions** determine which path to take based on node outcomes

This allows for complex workflows with branching logic and loops.

### 3. Tool Integration
Hive has built-in support for Model Context Protocol (MCP) tools:
- Over 100+ pre-built tools available
- Easy integration of custom tools
- Automatic tool discovery and registration

### 4. Memory System
Hive provides sophisticated memory management:
- **SharedMemory**: For passing data between nodes within a session
- **StreamMemory**: For concurrent execution with proper isolation
- **Checkpointing**: Save and resume agent execution

### 5. Event Loop Nodes
The most powerful node type is the EventLoopNode, which:
- Uses LLM reasoning to decide actions
- Can call tools and interact with users
- Maintains conversation context
- Handles multi-turn interactions

## Architecture Components

### Nodes
Nodes are the building blocks of agent workflows:
- **Event Loop Nodes**: LLM-powered nodes that can reason and call tools
- **Worker Nodes**: Simple processing nodes
- **Client-Facing Nodes**: Nodes that interact with end users

### Edges
Edges connect nodes and define execution flow:
- **ON_SUCCESS**: Proceed when node succeeds
- **ON_FAILURE**: Proceed when node fails
- **CONDITIONAL**: Proceed based on output conditions

### Goals
Goals define what the agent should accomplish:
- Success criteria with weights and metrics
- Constraints (hard and soft)
- Evaluation criteria

### Tools
Tools extend agent capabilities:
- MCP tools from external servers
- Custom Python functions
- Built-in framework tools

## Use Cases

Hive is ideal for:
1. **Research Agents**: Multi-step research with tool integration
2. **Content Creation**: Writing, summarization, and content generation
3. **Data Processing**: ETL pipelines with intelligent decision-making
4. **Customer Support**: Conversational agents with knowledge retrieval
5. **Workflow Automation**: Complex business process automation

## Getting Started

To create a Hive agent:
1. Define your goal and success criteria
2. Design your node workflow
3. Implement nodes with appropriate prompts
4. Connect nodes with edges
5. Configure tools and resources
6. Test and iterate

## Best Practices

1. **Clear Goal Definition**: Start with a well-defined goal
2. **Modular Design**: Keep nodes focused on single responsibilities
3. **Proper Memory Usage**: Use SharedMemory for data passing
4. **Tool Selection**: Choose appropriate tools for each task
5. **Error Handling**: Design edges to handle failures gracefully
