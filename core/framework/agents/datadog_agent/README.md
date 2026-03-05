# Datadog Agent

Data Integrity Monitoring Agent for the Hive Framework.

## Overview

The Datadog Agent audits data quality across various data sources, detecting NULL values, schema mismatches, duplicates, and data anomalies. It quarantines invalid records and generates compliance-ready reports.

## Supported Data Sources

- **PostgreSQL**: Full database querying and analysis
- **BigQuery**: Cloud data warehouse integration
- **CSV Files**: Local and uploaded CSV file analysis
- **Excel Files**: XLSX/XLS spreadsheet analysis

## Features

### Data Quality Checks

1. **NULL Detection**: Identify columns with NULL values and count occurrences
2. **Schema Validation**: Verify data types match expected schema
3. **Duplicate Detection**: Find duplicate records across datasets
4. **Data Anomaly Detection**: Identify outliers and invalid formats
5. **Referential Integrity**: Check foreign key relationships (databases)

### Quarantine System

- Isolate invalid records in separate storage
- Maintain audit trails with timestamps
- Preserve original data integrity

### Compliance Reporting

- GDPR and CCPA compliance checks
- Comprehensive audit documentation
- Executive summaries and detailed findings

## Usage

### TUI Mode (Recommended)

```bash
cd /path/to/hive
PYTHONPATH=exports uv run python -m datadog_agent tui
```

### Shell Mode

```bash
PYTHONPATH=exports uv run python -m datadog_agent shell
```

### Validation

```bash
PYTHONPATH=exports uv run python -m datadog_agent validate
```

### Agent Info

```bash
PYTHONPATH=exports uv run python -m datadog_agent info
```

## Workflow

```
┌─────────────────┐
│     INTAKE      │  Gather data source requirements
│ (client-facing) │
└────────┬────────┘
         │ on_success
         ▼
┌─────────────────┐
│    ANALYZE      │  Run data quality checks
│                 │
└────────┬────────┘
         │ on_success
         ▼
┌─────────────────┐
│     REVIEW      │  Present findings for approval
│ (client-facing) │
└────┬───────┬────┘
     │       │ feedback (loops back to ANALYZE)
     │       └──────────────────┐
     │ approved                 │
     ▼                          │
┌─────────────────┐             │
│   QUARANTINE    │             │
│                 │             │
└────────┬────────┘             │
         │ on_success           │
         ▼                      │
┌─────────────────┐             │
│     REPORT      │  Generate final report
│ (client-facing) │
└─────────────────┘
```

## Configuration

The agent uses the following environment variables for data source connections:

### PostgreSQL
- `POSTGRES_CONNECTION_STRING` or individual `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DATABASE`

### BigQuery
- `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)

### Credentials Setup

Use the hive-credentials skill to set up credentials:

```bash
/hive-credentials --agent datadog_agent
```

## Example Usage

1. Start the agent: `hive tui` and select "Datadog Agent"
2. Specify your data source (e.g., PostgreSQL database, CSV file)
3. Select the quality checks to perform
4. Review the findings
5. Approve quarantine of invalid records
6. Generate the final compliance report

## Output

The agent produces:
- **Quality Report**: Summary of data quality issues
- **Quarantine File/Table**: Isolated invalid records
- **Final Report**: Comprehensive documentation with audit trail
