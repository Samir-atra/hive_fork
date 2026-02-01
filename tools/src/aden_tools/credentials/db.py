"""
Database credential specifications.
"""

from .base import CredentialSpec

DB_CREDENTIALS = {
    "postgres_connection_string": CredentialSpec(
        env_var="POSTGRES_CONNECTION_STRING",
        tools=["postgres_read_query"],
        required=True,
        description="Connection string for PostgreSQL database (e.g., postgresql://user:password@localhost:5432/dbname)",
    ),
}
