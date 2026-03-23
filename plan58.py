with open("core/framework/graph/event_loop_node.py") as f:
    code = f.read()

# Let's fix auto-block to apply to ALL pure conversational nodes (output_keys=[] and client_facing=True)
old_str = """                elif stream_id == "queen" and not real_tool_results and not outputs_set:
                    # Auto-block: only for the queen (conversational node).
                    # Workers are autonomous — they block only on explicit
                    # ask_user().  Turns without tool calls or set_output
                    # (including empty ghost streams) are not work — block
                    # and wait for user input."""

new_str = """                elif (stream_id == "queen" or not ctx.node_spec.output_keys) and not real_tool_results and not outputs_set:
                    # Auto-block: for the queen and pure conversational nodes.
                    # Task workers are autonomous — they block only on explicit
                    # ask_user().  Turns without tool calls or set_output
                    # (including empty ghost streams) are not work — block
                    # and wait for user input."""

if old_str in code:
    code = code.replace(old_str, new_str)
    with open("core/framework/graph/event_loop_node.py", "w") as f:
        f.write(code)
    print("Fixed auto-block.")
else:
    print("Not found.")
