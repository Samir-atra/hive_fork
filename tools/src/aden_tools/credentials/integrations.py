"""
Integration credentials for Aden Tools.

Contains credentials for third-party integrations like Microsoft SQL Server.
"""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
    "mssql_host": CredentialSpec(
        env_var="MSSQL_HOST",
        tools=["mssql_query", "mssql_list_tables", "mssql_get_schema"],
        required=True,
        startup_required=False,
        description="Hostname or IP address of the MSSQL server",
    ),
    "mssql_user": CredentialSpec(
        env_var="MSSQL_USER",
        tools=["mssql_query", "mssql_list_tables", "mssql_get_schema"],
        required=True,
        startup_required=False,
        description="Username for MSSQL authentication",
    ),
    "mssql_password": CredentialSpec(
        env_var="MSSQL_PASSWORD",
        tools=["mssql_query", "mssql_list_tables", "mssql_get_schema"],
        required=True,
        startup_required=False,
        description="Password for MSSQL authentication",
    ),
    "mssql_database": CredentialSpec(
        env_var="MSSQL_DATABASE",
        tools=["mssql_query", "mssql_list_tables", "mssql_get_schema"],
        required=False,  # Optional, can connect to default DB
        startup_required=False,
        description="Target database name on the MSSQL server",
    ),
}
