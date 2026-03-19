import os
import sys
from pathlib import Path

# Add core to sys.path if not there
core_path = str(Path(__file__).parent.parent.parent / "core")
if core_path not in sys.path:
    sys.path.insert(0, core_path)

from framework.cli import main

if __name__ == "__main__":
    agent_dir = str(Path(__file__).parent)
    new_args = [sys.argv[0]]
    if len(sys.argv) > 1:
        new_args.append(sys.argv[1])
        new_args.append(agent_dir)
        new_args.extend(sys.argv[2:])
    else:
        new_args.extend(['info', agent_dir])
    sys.argv = new_args
    sys.exit(main())
