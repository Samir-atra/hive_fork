[Integration]: Microsoft SQL Server (MSSQL) tool for enterprise database operations

# Description
Implements a dedicated Microsoft SQL Server (MSSQL) tool for the Hive agent framework using the FastMCP pattern. This integration enables agents to securely connect to, query, and inspect MSSQL databases, filling a critical gap for enterprise data analysis.

## Features
- **Secure Authentication**: Uses `CredentialManager` to handle host, user, and password credentials securely.
- **Read-Only Queries**: Executives SQL `SELECT` queries to fetch data for analysis.
- **Safety Checks**: Implements heuristic checks to prevent forbidden operations (INSERT, UPDATE, DELETE, DROP, etc.).
- **Schema Discovery**: Allows agents to list tables (`mssql_list_tables`) and inspect table schemas (`mssql_get_schema`) to construct accurate queries.
- **Port Flexibility**: Supports standard port 1433 or custom ports via `hostname:port` syntax.

## Tools Added
- `mssql_query`: Execute a read-only SQL query.
- `mssql_list_tables`: List all user tables in the database.
- `mssql_get_schema`: Get column details (name, type, etc.) for a specific table.

## Environment Setup
| Variable | Description |
| --- | --- |
| `MSSQL_HOST` | Hostname or IP of the MSSQL server (optional :port). |
| `MSSQL_USER` | Database username. |
| `MSSQL_PASSWORD` | Database user password. |
| `MSSQL_DATABASE` | (Optional) Default database to connect to. |

## Dependencies
- `pymssql`: Added to `tools/pyproject.toml` for Python-MSSQL connectivity.

## Use Cases
- **Data Analysis**: Agents can pull sales data or inventory levels directly from enterprise ERPs.
- **Reporting**: Automate the generation of reports based on live database records.
- **Debugging**: Inspect database state to troubleshoot application issues.

## Testing
- Added robust unit tests in `tools/tests/tools/test_mssql_tool.py`.
- Verified connection handling, query execution, schema retrieval, and error handling (connection failures, bad queries).
- specifically tested the forbidden keyword safety mechanism.
- Verified MCP tool registration.

## Related Issue
- Resolve #3377
