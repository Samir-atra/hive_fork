# Observability Agent

This template demonstrates Hive's built-in observability features, which track runtime metrics such as:
- Latency per node
- Token usage
- Node visit counts
- Judge verdicts (ACCEPT, ESCALATE, RETRY)

## Setup

First, ensure observability is enabled in your `~/.hive/configuration.json`:

```json
{
  "observability": {
    "enabled": true,
    "log_metrics": true,
    "metrics_file": "/tmp/hive_metrics.jsonl"
  }
}
```

If `metrics_file` is not provided, the metrics will be saved in your session data directory.

## Running the Agent

You can tail the metrics file to see the real-time node evaluations and metrics being recorded:

```bash
tail -n 100 -f /tmp/hive_metrics.jsonl
```
