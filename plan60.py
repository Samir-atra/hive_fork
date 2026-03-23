with open("core/framework/graph/event_loop_node.py") as f:
    code = f.read()

# Apply the same logic to the winddown warning injection at 80%.
old_str = """            # Inject graceful winddown warning at 80%
            if ctx.node_spec.client_facing and iteration == int(self._config.max_iterations * 0.8):
                await conversation.add_user_message("""

new_str = """            # Inject graceful winddown warning at 80%
            if (
                ctx.node_spec.client_facing
                and not ctx.node_spec.output_keys
                and iteration == int(self._config.max_iterations * 0.8)
            ):
                await conversation.add_user_message("""

if old_str in code:
    code = code.replace(old_str, new_str)
    with open("core/framework/graph/event_loop_node.py", "w") as f:
        f.write(code)
    print("Fixed winddown warning.")
else:
    print("Not found.")
