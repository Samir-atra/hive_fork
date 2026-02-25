"""
Generated agent: preview-agent
Generated at: 2026-02-10T16:11:23.130658
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
    "name": "preview-agent",
    "description": "predict the prices of the tech giants stock",
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
        "goal_summary": "Predict the prices of tech giants' stocks.",
        "proposed_nodes": [
            {
                "name": "Stock Ticker Identification",
                "node_type": "llm_generate",
                "purpose": "Identify the stock tickers for major tech giants based on a general query.",
                "estimated_tools": [],
                "estimated_llm_calls": 1
            },
            {
                "name": "Stock Price Fetcher",
                "node_type": "function",
                "purpose": "Fetch historical and real-time stock price data for a given ticker using a financial data API.",
                "estimated_tools": [],
                "estimated_llm_calls": 0
            },
            {
                "name": "Data Preprocessor",
                "node_type": "function",
                "purpose": "Clean and prepare the fetched stock data for analysis (e.g., handle missing values, normalize).",
                "estimated_tools": [],
                "estimated_llm_calls": 0
            },
            {
                "name": "Prediction Model",
                "node_type": "function",
                "purpose": "Utilize a pre-trained or dynamically trained time-series forecasting model to predict future stock prices.",
                "estimated_tools": [],
                "estimated_llm_calls": 0
            },
            {
                "name": "Output Formatter",
                "node_type": "llm_generate",
                "purpose": "Format the predicted stock prices into a user-friendly and understandable output.",
                "estimated_tools": [],
                "estimated_llm_calls": 1
            }
        ],
        "proposed_edges": [
            {
                "source": "User Input",
                "target": "Stock Ticker Identification",
                "condition_type": "always",
                "routing_summary": "Initial user query to identify tech giants."
            },
            {
                "source": "Stock Ticker Identification",
                "target": "Stock Price Fetcher",
                "condition_type": "on_success",
                "routing_summary": "Pass identified tickers to the data fetching node."
            },
            {
                "source": "Stock Price Fetcher",
                "target": "Data Preprocessor",
                "condition_type": "on_success",
                "routing_summary": "Pass fetched stock data for preprocessing."
            },
            {
                "source": "Data Preprocessor",
                "target": "Prediction Model",
                "condition_type": "on_success",
                "routing_summary": "Pass preprocessed data to the prediction model."
            },
            {
                "source": "Prediction Model",
                "target": "Output Formatter",
                "condition_type": "on_success",
                "routing_summary": "Pass predicted prices to the output formatter."
            },
            {
                "source": "Output Formatter",
                "target": "User Output",
                "condition_type": "always",
                "routing_summary": "Present the final prediction to the user."
            }
        ],
        "estimated_complexity": "high",
        "estimated_generation_cost": 0.05,
        "estimated_per_run_cost": 0.03,
        "risk_flags": [
            {
                "severity": "warning",
                "message": "Critierion 'Goal achieved' may not be covered.",
                "suggestion": "Add a specific verification step."
            }
        ],
        "suggested_refinements": []
    },
    "created_at": "2026-02-10T16:11:19.735629",
    "updated_at": "2026-02-10T16:11:19.735631"
}
''')


# Nodes
NODES = [
    NodeSpec.model_validate_json('''
{
    "id": "stock_ticker_identification",
    "name": "Stock Ticker Identification",
    "description": "Identify the stock tickers for major tech giants based on a general query.",
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
    "id": "stock_price_fetcher",
    "name": "Stock Price Fetcher",
    "description": "Fetch historical and real-time stock price data for a given ticker using a financial data API.",
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
    "id": "data_preprocessor",
    "name": "Data Preprocessor",
    "description": "Clean and prepare the fetched stock data for analysis (e.g., handle missing values, normalize).",
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
    "id": "prediction_model",
    "name": "Prediction Model",
    "description": "Utilize a pre-trained or dynamically trained time-series forecasting model to predict future stock prices.",
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
    "id": "output_formatter",
    "name": "Output Formatter",
    "description": "Format the predicted stock prices into a user-friendly and understandable output.",
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
]


# Edges
EDGES = [
    EdgeSpec.model_validate_json('''
{
    "id": "stock_ticker_identification_to_stock_price_fetcher",
    "source": "stock_ticker_identification",
    "target": "stock_price_fetcher",
    "condition": "on_success",
    "condition_expr": null,
    "input_mapping": {},
    "priority": 0,
    "description": "Pass identified tickers to the data fetching node."
}
    '''),
    EdgeSpec.model_validate_json('''
{
    "id": "stock_price_fetcher_to_data_preprocessor",
    "source": "stock_price_fetcher",
    "target": "data_preprocessor",
    "condition": "on_success",
    "condition_expr": null,
    "input_mapping": {},
    "priority": 0,
    "description": "Pass fetched stock data for preprocessing."
}
    '''),
    EdgeSpec.model_validate_json('''
{
    "id": "data_preprocessor_to_prediction_model",
    "source": "data_preprocessor",
    "target": "prediction_model",
    "condition": "on_success",
    "condition_expr": null,
    "input_mapping": {},
    "priority": 0,
    "description": "Pass preprocessed data to the prediction model."
}
    '''),
    EdgeSpec.model_validate_json('''
{
    "id": "prediction_model_to_output_formatter",
    "source": "prediction_model",
    "target": "output_formatter",
    "condition": "on_success",
    "condition_expr": null,
    "input_mapping": {},
    "priority": 0,
    "description": "Pass predicted prices to the output formatter."
}
    '''),
]


# Graph
GRAPH = GraphSpec.model_validate_json('''
{
    "id": "preview-agent-graph",
    "goal_id": "preview-goal",
    "version": "1.0.0",
    "entry_node": "stock_ticker_identification",
    "entry_points": {},
    "async_entry_points": [],
    "terminal_nodes": [
        "output_formatter"
    ],
    "pause_nodes": [],
    "nodes": [
        {
            "id": "stock_ticker_identification",
            "name": "Stock Ticker Identification",
            "description": "Identify the stock tickers for major tech giants based on a general query.",
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
            "id": "stock_price_fetcher",
            "name": "Stock Price Fetcher",
            "description": "Fetch historical and real-time stock price data for a given ticker using a financial data API.",
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
            "id": "data_preprocessor",
            "name": "Data Preprocessor",
            "description": "Clean and prepare the fetched stock data for analysis (e.g., handle missing values, normalize).",
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
            "id": "prediction_model",
            "name": "Prediction Model",
            "description": "Utilize a pre-trained or dynamically trained time-series forecasting model to predict future stock prices.",
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
            "id": "output_formatter",
            "name": "Output Formatter",
            "description": "Format the predicted stock prices into a user-friendly and understandable output.",
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
    ],
    "edges": [
        {
            "id": "stock_ticker_identification_to_stock_price_fetcher",
            "source": "stock_ticker_identification",
            "target": "stock_price_fetcher",
            "condition": "on_success",
            "condition_expr": null,
            "input_mapping": {},
            "priority": 0,
            "description": "Pass identified tickers to the data fetching node."
        },
        {
            "id": "stock_price_fetcher_to_data_preprocessor",
            "source": "stock_price_fetcher",
            "target": "data_preprocessor",
            "condition": "on_success",
            "condition_expr": null,
            "input_mapping": {},
            "priority": 0,
            "description": "Pass fetched stock data for preprocessing."
        },
        {
            "id": "data_preprocessor_to_prediction_model",
            "source": "data_preprocessor",
            "target": "prediction_model",
            "condition": "on_success",
            "condition_expr": null,
            "input_mapping": {},
            "priority": 0,
            "description": "Pass preprocessed data to the prediction model."
        },
        {
            "id": "prediction_model_to_output_formatter",
            "source": "prediction_model",
            "target": "output_formatter",
            "condition": "on_success",
            "condition_expr": null,
            "input_mapping": {},
            "priority": 0,
            "description": "Pass predicted prices to the output formatter."
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