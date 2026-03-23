with open("core/framework/graph/event_loop_node.py") as f:
    code = f.read()

# Change the `max_iterations` graceful exit condition to ONLY apply if `is_cf` AND `not output_keys`.
old_str = """        is_cf = ctx.node_spec.client_facing
        success_val = is_cf
        exit_status_val = "success" if is_cf else "failure"
        error_val = (
            None
            if is_cf
            else f"Max iterations ({self._config.max_iterations}) reached without acceptance"
        )"""

new_str = """        is_pure_conv = ctx.node_spec.client_facing and not ctx.node_spec.output_keys
        success_val = is_pure_conv
        exit_status_val = "success" if is_pure_conv else "failure"
        error_val = (
            None
            if is_pure_conv
            else f"Max iterations ({self._config.max_iterations}) reached without acceptance"
        )"""

if old_str in code:
    code = code.replace(old_str, new_str)
    with open("core/framework/graph/event_loop_node.py", "w") as f:
        f.write(code)
    print("Fixed success override.")
else:
    print("Not found.")
