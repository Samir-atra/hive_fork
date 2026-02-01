import logging
from typing import Any

import psycopg2
from fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)

# Constants for safety/limits
MAX_ROWS = 100
QUERY_TIMEOUT_MS = 10000  # 10 seconds


def get_connection(connection_string: str):
    """Create a database connection."""
    try:
        conn = psycopg2.connect(connection_string)
        # Set read only session
        conn.set_session(readonly=True)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def validate_query(query: str) -> None:
    """
    Validate that the query is a read-only SELECT query.
    Simple keyword check - not perfect but catches basic attempts.
    """
    query_upper = query.strip().upper()

    # helper for checking forbidden keywords
    forbidden = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "COMMIT",
        "ROLLBACK",
    ]

    if not query_upper.startswith("SELECT"):
        # Allow WITH for CTEs, typically start with WITH
        if not query_upper.startswith("WITH"):
            raise ValueError("Only SELECT queries are allowed.")

    for keyword in forbidden:
        # Check if keyword exists as a whole word
        # This is a basic check; sophisticated SQL parsing is harder but this covers MVP
        if (
            f" {keyword} " in f" {query_upper} "
            or f"\n{keyword}" in query_upper
            or f"({keyword}" in query_upper
        ):
            raise ValueError(f"Query contains forbidden keyword: {keyword}")


def execute_read_query(connection_string: str, query: str) -> list[dict[str, Any]]:
    """
    Execute a read-only query against the database.

    Args:
        connection_string: Database connection string.
        query: SQL query to execute.

    Returns:
        List of dictionaries representing rows.
    """
    validate_query(query)

    conn = None
    try:
        conn = get_connection(connection_string)
        with conn.cursor() as cur:
            # Set statement timeout
            cur.execute(f"SET statement_timeout = {QUERY_TIMEOUT_MS};")

            cur.execute(query)

            # Fetch column names
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                results = []
                # Fetch with limit
                rows = cur.fetchmany(MAX_ROWS)
                for row in rows:
                    results.append(dict(zip(columns, row, strict=True)))

                # Check if there were more rows
                if cur.fetchone():
                    logger.warning(f"Query result truncated to {MAX_ROWS} rows.")
                    # We can append a metadata field or just log it.
                    # For simplicity, we just return the limited rows.

                return results
            return []
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise e
    finally:
        if conn:
            conn.close()


def register_tools(mcp: FastMCP, credentials=None):
    """Register PostgreSQL tools."""

    @mcp.tool(
        name="postgres_read_query",
        description="Execute a read-only SQL query against the PostgreSQL database.",
    )
    def postgres_read_query(query: str, ctx: Context = None) -> str:
        """
        Execute a read-only SQL query (SELECT only) and return results as JSON.

        Args:
            query: The SQL query to execute. MUST be a SELECT statement.
        """
        if credentials:
            # Check creds
            try:
                credentials.validate_for_tools(["postgres_read_query"])
                conn_str = credentials.get("postgres_connection_string")
            except Exception as e:
                return f"Error: Missing credentials. {str(e)}"
        else:
            return "Error: Credential manager not provided."

        try:
            results = execute_read_query(conn_str, query)
            import json

            # Use default str for non-serializable objects (like dates)
            return json.dumps(results, default=str, indent=2)
        except Exception as e:
            return f"Error executing query: {str(e)}"
