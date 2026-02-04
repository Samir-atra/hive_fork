"""
Microsoft SQL Server tool for Aden Tools.

Provides capabilities to query and inspect MSSQL databases securely.
"""

import logging
from typing import Any, Optional, List, Dict

import pymssql
from fastmcp import FastMCP

from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)


class MSSQLClient:
    """Client for interacting with Microsoft SQL Server."""

    def __init__(self, host: str, user: str, password: str, database: Optional[str] = None):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = 1433  # Default port, could be configurable if needed

        # Parse port from host if present (e.g., host:1433)
        if ":" in self.host:
            try:
                self.host, port_str = self.host.split(":")
                self.port = int(port_str)
            except ValueError:
                pass  # Keep default if parsing fails

    def _get_connection(self):
        """Establish a connection to the database."""
        try:
            conn = pymssql.connect(
                server=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                as_dict=True
            )
            return conn
        except pymssql.Error as e:
            logger.error(f"MSSQL Connection Error: {e}")
            raise RuntimeError(f"Failed to connect to MSSQL: {e}")

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a read-only SQL query."""
        # Basic safety check for read-only
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"]
        normalized_query = query.strip().upper()
        
        # Check if the query starts with a forbidden keyword or contains potentially dangerous statements
        # This is a basic heuristic and not a full SQL parser security guarantee.
        for keyword in forbidden_keywords:
            # Check strictly for starting keywords or keywords after a semicolon to prevent multiple statements
            if normalized_query.startswith(keyword) or f"; {keyword}" in normalized_query or f";{keyword}" in normalized_query:
                raise ValueError(f"Write operations are not allowed. Forbidden keyword: {keyword}")

        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                # pymssql as_dict=True returns list of dicts
                return cursor.fetchall()
        except pymssql.Error as e:
            logger.error(f"MSSQL Query Error: {e}")
            raise RuntimeError(f"Query execution failed: {e}")
        finally:
            conn.close()

    def list_tables(self) -> List[Dict[str, Any]]:
        """List all user tables in the database."""
        # Query to list tables
        query = """
        SELECT TABLE_SCHEMA, TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        return self.execute_query(query)

    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a specific table."""
        # Sanitize table_name to prevent injection
        # Standard way is to use parameters, but INFORMATION_SCHEMA usually works better with literals in some contexts
        # or we use parameters with pymssql.
        
        # We need to handle schema.table vs just table
        schema = "dbo"
        table = table_name
        if "." in table_name:
            parts = table_name.split(".", 1)
            schema = parts[0]
            table = parts[1]

        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                query = """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s
                ORDER BY ORDINAL_POSITION
                """
                cursor.execute(query, (table, schema))
                return cursor.fetchall()
        except pymssql.Error as e:
            logger.error(f"MSSQL Schema Error: {e}")
            raise RuntimeError(f"Failed to get schema for {table_name}: {e}")
        finally:
            conn.close()


def register_tools(mcp: FastMCP, credentials: Optional[CredentialManager] = None) -> None:
    """Register MSSQL tools."""

    def get_client() -> MSSQLClient:
        if credentials:
            host = credentials.get("mssql_host")
            user = credentials.get("mssql_user")
            password = credentials.get("mssql_password")
            database = credentials.get("mssql_database")
        else:
            import os
            host = os.getenv("MSSQL_HOST")
            user = os.getenv("MSSQL_USER")
            password = os.getenv("MSSQL_PASSWORD")
            database = os.getenv("MSSQL_DATABASE")

        if not host or not user or not password:
            raise ValueError("MSSQL_HOST, MSSQL_USER, and MSSQL_PASSWORD must be set")
        
        return MSSQLClient(host, user, password, database)

    @mcp.tool()
    def mssql_query(query: str) -> str:
        """
        Execute a read-only SQL query against the MSSQL database.
        
        Args:
            query: The SQL query to execute (SELECT only).

        Returns:
            JSON string containing the query results.
        """
        try:
            client = get_client()
            result = client.execute_query(query)
            import json
            # Handle non-serializable types if necessary (dates, decimals)
            # pymssql usually returns python types
            return json.dumps(result, indent=2, default=str) 
        except Exception as e:
            return f"Error executing query: {str(e)}"

    @mcp.tool()
    def mssql_list_tables() -> str:
        """
        List all tables in the current database.

        Returns:
            JSON string list of tables with schemas.
        """
        try:
            client = get_client()
            result = client.list_tables()
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing tables: {str(e)}"

    @mcp.tool()
    def mssql_get_schema(table_name: str) -> str:
        """
        Get column details for a specific table.

        Args:
            table_name: The name of the table (e.g., 'Users' or 'dbo.Users').

        Returns:
            JSON string containing column definitions.
        """
        try:
            client = get_client()
            result = client.get_schema(table_name)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error retrieving schema: {str(e)}"
