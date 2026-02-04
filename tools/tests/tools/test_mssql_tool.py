import json
import pytest
from unittest.mock import MagicMock, patch
import pymssql
from aden_tools.tools.mssql_tool import MSSQLClient, register_tools

@pytest.fixture
def mock_credentials():
    mock = MagicMock()
    def get_cred(key):
        if key == "mssql_host": return "localhost"
        if key == "mssql_user": return "sa"
        if key == "mssql_password": return "pass"
        if key == "mssql_database": return "master"
        return None
    mock.get.side_effect = get_cred
    return mock

@pytest.fixture
def client():
    return MSSQLClient("localhost", "sa", "pass", "master")

def test_client_init_defaults():
    client = MSSQLClient("localhost", "sa", "pass")
    assert client.port == 1433
    assert client.host == "localhost"

def test_client_init_custom_port():
    client = MSSQLClient("db.example.com:1434", "sa", "pass")
    assert client.port == 1434
    assert client.host == "db.example.com"

@patch("pymssql.connect")
def test_execute_query_success(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "Test"}]

    result = client.execute_query("SELECT * FROM Users")
    assert len(result) == 1
    assert result[0]["name"] == "Test"
    
    # Verify connections closed
    mock_conn.close.assert_called_once()

@patch("pymssql.connect")
def test_execute_query_forbidden_keyword(mock_connect, client):
    with pytest.raises(ValueError, match="Forbidden keyword"):
        client.execute_query("INSERT INTO Users (name) VALUES ('Bad')")
    
    mock_connect.assert_not_called()

@patch("pymssql.connect")
def test_execute_query_forbidden_keyword_semicolon(mock_connect, client):
    with pytest.raises(ValueError, match="Forbidden keyword"):
        client.execute_query("SELECT * FROM Users; DROP TABLE Users")

@patch("pymssql.connect")
def test_connection_error(mock_connect, client):
    mock_connect.side_effect = pymssql.Error("Login failed")
    
    with pytest.raises(RuntimeError, match="Failed to connect to MSSQL"):
        client.execute_query("SELECT 1")

@patch("pymssql.connect")
def test_query_error(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.execute.side_effect = pymssql.Error("Syntax invalid")

    with pytest.raises(RuntimeError, match="Query execution failed"):
        client.execute_query("SELECT * FROM BadTable")

@patch("pymssql.connect")
def test_list_tables(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [{"TABLE_SCHEMA": "dbo", "TABLE_NAME": "Users"}]
    
    tables = client.list_tables()
    assert tables[0]["TABLE_NAME"] == "Users"
    assert "INFORMATION_SCHEMA.TABLES" in mock_cursor.execute.call_args[0][0]

@patch("pymssql.connect")
def test_get_schema(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [{"COLUMN_NAME": "id", "DATA_TYPE": "int"}]
    
    schema = client.get_schema("dbo.Users")
    assert schema[0]["COLUMN_NAME"] == "id"
    
    args = mock_cursor.execute.call_args[0]
    assert "INFORMATION_SCHEMA.COLUMNS" in args[0]
    assert args[1] == ("Users", "dbo")
    
@patch("aden_tools.tools.mssql_tool.mssql_tool.MSSQLClient")
def test_mcp_tool_query(mock_client_class, mock_credentials):
    mock_client = mock_client_class.return_value
    mock_client.execute_query.return_value = [{"col": "val"}]

    mock_mcp = MagicMock()
    mock_tool_distributor = MagicMock()
    mock_mcp.tool.return_value = mock_tool_distributor
    
    register_tools(mock_mcp, credentials=mock_credentials)
    
    # Find tool
    query_tool = None
    for call in mock_tool_distributor.call_args_list:
        func = call.args[0]
        if func.__name__ == "mssql_query":
            query_tool = func
            break
    
    assert query_tool is not None
    res = query_tool("SELECT 1")
    assert "val" in res
