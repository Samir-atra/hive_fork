import os
import glob

# The easiest way to silence the Node.js 20 deprecation warning across all workflows
# is to set the environment variable FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true globally in the workflows
# or update the actions if v5 or v6 exists.
# For `actions/checkout@v4`, there is no v5 yet. It is still v4, but latest minor version supports node20.
# The warning literally says: "To opt into Node.js 24 now, set the FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true environment variable on the runner or in your workflow file."

for file in glob.glob(".github/workflows/*.yml"):
    with open(file, 'r') as f:
        content = f.read()

    # We can add env to all workflows:
    if "env:\n  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" not in content:
        # Find where to insert it. A good place is right after `jobs:` or inside each job.
        # Alternatively, we can just replace `actions/checkout@v4` with `actions/checkout@v4` and so on, but actually if the runner warns about Node 20, we should set the env var.

        # Let's insert global env after `name:` or `on:` blocks.
        if "env:" not in content[:300]:
            # Simple global insert
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('jobs:'):
                    lines.insert(i, 'env:')
                    lines.insert(i+1, '  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true')
                    lines.insert(i+2, '')
                    break
            content = '\n'.join(lines)
            with open(file, 'w') as f:
                f.write(content)
