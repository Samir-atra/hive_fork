with open("core/framework/graph/event_loop_node.py") as f:
    code = f.read()

import re

m = re.search(r'elif stream_id == "queen" and not real_tool_results and not outputs_set:', code)
if m:
    print(m.group(0))
