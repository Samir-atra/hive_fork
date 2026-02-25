"""
Generated agent: news-aggregator
Generated at: 2026-02-10T16:03:54.607119
"""

from framework.graph import (
    Goal, SuccessCriterion, Constraint,
    NodeSpec, EdgeSpec, EdgeCondition,
)
from framework.graph.edge import GraphSpec
from framework.graph.goal import GoalStatus


# Goal
GOAL = Goal.model_validate_json('''
{
    "id": "preview-goal",
    "name": "news-aggregator",
    "description": "Generate a summary of today's news",
    "status": "draft",
    "success_criteria": [
        {
            "id": "default",
            "description": "Goal achieved",
            "metric": "llm_judge",
            "target": true,
            "weight": 1.0,
            "met": false
        }
    ],
    "constraints": [],
    "context": {},
    "required_capabilities": [],
    "input_schema": {},
    "output_schema": {},
    "version": "1.0.0",
    "parent_version": null,
    "evolution_reason": null,
    "approved_preview": {
        "goal_summary": "Preview for: news-aggregator",
        "proposed_nodes": [
            {
                "name": "InputProcessor",
                "node_type": "function",
                "purpose": "Parse input",
                "estimated_tools": [],
                "estimated_llm_calls": 1
            },
            {
                "name": "MainLogic",
                "node_type": "llm_generate",
                "purpose": "Execute core task",
                "estimated_tools": [],
                "estimated_llm_calls": 1
            },
            {
                "name": "OutputFormatter",
                "node_type": "function",
                "purpose": "Format result",
                "estimated_tools": [],
                "estimated_llm_calls": 1
            }
        ],
        "proposed_edges": [
            {
                "source": "InputProcessor",
                "target": "MainLogic",
                "condition_type": "always",
                "routing_summary": "Always proceed"
            },
            {
                "source": "MainLogic",
                "target": "OutputFormatter",
                "condition_type": "on_success",
                "routing_summary": "If logic succeeds"
            }
        ],
        "estimated_complexity": "medium",
        "estimated_generation_cost": 0.05,
        "estimated_per_run_cost": 0.01,
        "risk_flags": [
            {
                "severity": "info",
                "message": "Mock preview generated.",
                "suggestion": "Check API keys."
            }
        ],
        "suggested_refinements": []
    },
    "created_at": "2026-02-10T16:03:53.649056",
    "updated_at": "2026-02-10T16:03:53.649059"
}
''')


# Nodes
NODES = [
    NodeSpec.model_validate_json('''
{
    "id": "inputprocessor",
    "name": "InputProcessor",
    "description": "Parse input",
    "node_type": "function",
    "input_keys": [],
    "output_keys": [],
    "nullable_output_keys": [],
    "input_schema": {},
    "output_schema": {},
    "system_prompt": null,
    "tools": [],
    "model": null,
    "function": null,
    "routes": {},
    "max_retries": 3,
    "retry_on": [],
    "max_node_visits": 1,
    "output_model": null,
    "max_validation_retries": 2,
    "client_facing": false
}
    '''),
    NodeSpec.model_validate_json('''
{
    "id": "mainlogic",
    "name": "MainLogic",
    "description": "Execute core task",
    "node_type": "llm_tool_use",
    "input_keys": [],
    "output_keys": [],
    "nullable_output_keys": [],
    "input_schema": {},
    "output_schema": {},
    "system_prompt": null,
    "tools": [],
    "model": null,
    "function": null,
    "routes": {},
    "max_retries": 3,
    "retry_on": [],
    "max_node_visits": 1,
    "output_model": null,
    "max_validation_retries": 2,
    "client_facing": false
}
    '''),
    NodeSpec.model_validate_json('''
{
    "id": "outputformatter",
    "name": "OutputFormatter",
    "description": "Format result",
    "node_type": "function",
    "input_keys": [],
    "output_keys": [],
    "nullable_output_keys": [],
    "input_schema": {},
    "output_schema": {},
    "system_prompt": null,
    "tools": [],
    "model": null,
    "function": null,
    "routes": {},
    "max_retries": 3,
    "retry_on": [],
    "max_node_visits": 1,
    "output_model": null,
    "max_validation_retries": 2,
    "client_facing": false
}
    '''),
]


# Edges
EDGES = [
    EdgeSpec.model_validate_json('''
{
    "id": "inputprocessor_to_mainlogic",
    "source": "inputprocessor",
    "target": "mainlogic",
    "condition": "always",
    "condition_expr": null,
    "input_mapping": {},
    "priority": 0,
    "description": "Always proceed"
}
    '''),
    EdgeSpec.model_validate_json('''
{
    "id": "mainlogic_to_outputformatter",
    "source": "mainlogic",
    "target": "outputformatter",
    "condition": "on_success",
    "condition_expr": null,
    "input_mapping": {},
    "priority": 0,
    "description": "If logic succeeds"
}
    '''),
]


# Graph
GRAPH = GraphSpec.model_validate_json('''
{
    "id": "news-aggregator-graph",
    "goal_id": "preview-goal",
    "version": "1.0.0",
    "entry_node": "inputprocessor",
    "entry_points": {},
    "async_entry_points": [],
    "terminal_nodes": [
        "outputformatter"
    ],
    "pause_nodes": [],
    "nodes": [
        {
            "id": "inputprocessor",
            "name": "InputProcessor",
            "description": "Parse input",
            "node_type": "function",
            "input_keys": [],
            "output_keys": [],
            "nullable_output_keys": [],
            "input_schema": {},
            "output_schema": {},
            "system_prompt": null,
            "tools": [],
            "model": null,
            "function": null,
            "routes": {},
            "max_retries": 3,
            "retry_on": [],
            "max_node_visits": 1,
            "output_model": null,
            "max_validation_retries": 2,
            "client_facing": false
        },
        {
            "id": "mainlogic",
            "name": "MainLogic",
            "description": "Execute core task",
            "node_type": "llm_tool_use",
            "input_keys": [],
            "output_keys": [],
            "nullable_output_keys": [],
            "input_schema": {},
            "output_schema": {},
            "system_prompt": null,
            "tools": [],
            "model": null,
            "function": null,
            "routes": {},
            "max_retries": 3,
            "retry_on": [],
            "max_node_visits": 1,
            "output_model": null,
            "max_validation_retries": 2,
            "client_facing": false
        },
        {
            "id": "outputformatter",
            "name": "OutputFormatter",
            "description": "Format result",
            "node_type": "function",
            "input_keys": [],
            "output_keys": [],
            "nullable_output_keys": [],
            "input_schema": {},
            "output_schema": {},
            "system_prompt": null,
            "tools": [],
            "model": null,
            "function": null,
            "routes": {},
            "max_retries": 3,
            "retry_on": [],
            "max_node_visits": 1,
            "output_model": null,
            "max_validation_retries": 2,
            "client_facing": false
        }
    ],
    "edges": [
        {
            "id": "inputprocessor_to_mainlogic",
            "source": "inputprocessor",
            "target": "mainlogic",
            "condition": "always",
            "condition_expr": null,
            "input_mapping": {},
            "priority": 0,
            "description": "Always proceed"
        },
        {
            "id": "mainlogic_to_outputformatter",
            "source": "mainlogic",
            "target": "outputformatter",
            "condition": "on_success",
            "condition_expr": null,
            "input_mapping": {},
            "priority": 0,
            "description": "If logic succeeds"
        }
    ],
    "memory_keys": [],
    "default_model": "claude-haiku-4-5-20251001",
    "max_tokens": 8192,
    "cleanup_llm_model": null,
    "max_steps": 100,
    "max_retries_per_node": 3,
    "loop_config": {},
    "description": "",
    "created_by": ""
}
''')