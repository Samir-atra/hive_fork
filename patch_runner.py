with open("core/framework/runner/runner.py", "r") as f:
    text = f.read()

text = text.replace(
"""    # Build GraphSpec
    graph = GraphSpec(
        id=graph_data.get("id", "agent-graph"),
        goal_id=graph_data.get("goal_id", ""),
        version=graph_data.get("version", "1.0.0"),
        entry_node=graph_data.get("entry_node", ""),""",
"""    # Build GraphSpec
    graph = GraphSpec(
        id=graph_data.get("id", "agent-graph"),
        goal_id=graph_data.get("goal_id", ""),
        version=graph_data.get("version", "1.0.0"),
        token_budget=graph_data.get("token_budget", None),
        entry_node=graph_data.get("entry_node", ""),"""
)

text = text.replace(
"""            # Resolve max_context_tokens with priority:
            #   1. agent loop_config["max_context_tokens"] (explicit, wins silently)
            #   2. agent default_config.max_context_tokens (logged)
            #   3. configuration.json llm.max_context_tokens
            #   4. hardcoded default (32_000)
            agent_loop_config: dict = dict(getattr(agent_module, "loop_config", {}))
            if "max_context_tokens" not in agent_loop_config:
                if agent_config and hasattr(agent_config, "max_context_tokens"):
                    agent_loop_config["max_context_tokens"] = agent_config.max_context_tokens
                    logger.info(
                        "Agent default_config overrides max_context_tokens: %d"
                        " (configuration.json value ignored)",
                        agent_config.max_context_tokens,
                    )
                else:
                    agent_loop_config["max_context_tokens"] = get_max_context_tokens()

            # Read intro_message from agent metadata (shown on TUI load)""",
"""            # Resolve max_context_tokens with priority:
            #   1. agent loop_config["max_context_tokens"] (explicit, wins silently)
            #   2. agent default_config.max_context_tokens (logged)
            #   3. configuration.json llm.max_context_tokens
            #   4. hardcoded default (32_000)
            agent_loop_config: dict = dict(getattr(agent_module, "loop_config", {}))
            if "max_context_tokens" not in agent_loop_config:
                if agent_config and hasattr(agent_config, "max_context_tokens"):
                    agent_loop_config["max_context_tokens"] = agent_config.max_context_tokens
                    logger.info(
                        "Agent default_config overrides max_context_tokens: %d"
                        " (configuration.json value ignored)",
                        agent_config.max_context_tokens,
                    )
                else:
                    agent_loop_config["max_context_tokens"] = get_max_context_tokens()

            if agent_config and hasattr(agent_config, "token_budget"):
                agent_loop_config["token_budget"] = agent_config.token_budget

            # Read intro_message from agent metadata (shown on TUI load)"""
)

text = text.replace(
"""                "terminal_nodes": getattr(agent_module, "terminal_nodes", []),
                "pause_nodes": getattr(agent_module, "pause_nodes", []),
                "nodes": nodes,
                "edges": edges,
                "max_tokens": max_tokens,
                "loop_config": agent_loop_config,
            }
            # Only pass optional fields if explicitly defined by the agent module
            conversation_mode = getattr(agent_module, "conversation_mode", None)""",
"""                "terminal_nodes": getattr(agent_module, "terminal_nodes", []),
                "pause_nodes": getattr(agent_module, "pause_nodes", []),
                "nodes": nodes,
                "edges": edges,
                "max_tokens": max_tokens,
                "loop_config": agent_loop_config,
            }
            if max_tokens_override is not None:
                graph_kwargs["token_budget"] = max_tokens_override
            elif agent_config and hasattr(agent_config, "token_budget"):
                graph_kwargs["token_budget"] = agent_config.token_budget

            # Only pass optional fields if explicitly defined by the agent module
            conversation_mode = getattr(agent_module, "conversation_mode", None)"""
)

text = text.replace(
"""        # Generate flowchart.json if missing (for legacy JSON-based agents)
        generate_fallback_flowchart(graph, goal, agent_path)

        runner = cls(
            agent_path=agent_path,
            graph=graph,
            goal=goal,""",
"""        if max_tokens_override is not None:
            graph.token_budget = max_tokens_override

        # Generate flowchart.json if missing (for legacy JSON-based agents)
        generate_fallback_flowchart(graph, goal, agent_path)

        runner = cls(
            agent_path=agent_path,
            graph=graph,
            goal=goal,"""
)

with open("core/framework/runner/runner.py", "w") as f:
    f.write(text)
