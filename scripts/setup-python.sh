#!/bin/bash
#
# setup-python.sh - Enforces deterministic installation of Python dependencies
#
# This script ensures that developers and CI environments install exact version parity
# with the uv.lock file, avoiding unexpected breakages from loose version constraints.

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_ROOT="$( dirname "$SCRIPT_DIR" )"

cd "$WORKSPACE_ROOT"

echo "Setting up Python dependencies deterministically from uv.lock..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it first from https://astral.sh/uv/"
    exit 1
fi

# Run uv sync with --frozen to guarantee installation exactly matches uv.lock
# Without --frozen, uv might silently update the lockfile if it's out of sync
# with pyproject.toml constraints.
uv sync --frozen --all-extras

echo "Dependencies installed successfully based on uv.lock."
