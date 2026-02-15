# Agent Performance & Drift Detection

Automated regression testing for Hive agents to ensure quality stability over time.

## Overview

This framework allows you to:
1.  **Capture Baselines**: Save current "golden" performance metrics (pass rate, latency, semantic output).
2.  **Detect Regressions**: Automatically compare new runs against the baseline to catch performance drops.
3.  **Monitor Drift**: Use LLM-based semantic similarity to detect if agent behavior is drifting away from the original goal description.

## CLI Usage

### 1. Establish a Baseline
After you have a test run that you consider "correct" and "high-performing", promote it to a baseline:
```bash
hive test-baseline exports/my_agent --goal my_goal_id
```

### 2. Check for Regressions
Run regression analysis to compare the current state against the latest baseline:
```bash
# First run the tests
hive test-run exports/my_agent --goal my_goal_id

# Then run regression analysis
hive test-regress exports/my_agent --goal my_goal_id
```

## How it Works
- **Performance**: Metrics like `pass_rate` and `avg_duration_ms` are compared. A drop > 5% (customizable) triggers a regression.
- **Drift**: Pluggable `LLMJudge` compares current outputs with baseline "golden" outputs. If semantic similarity falls below 0.85, drift is flagged.

## Directory Structure
Regression data is stored in the agent's testing directory:
- `.testing/regression/baselines/`: Golden performance snapshots.
- `.testing/regression/reports/`: Historical regression analysis.
