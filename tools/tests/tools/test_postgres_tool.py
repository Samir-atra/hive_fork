
import unittest
from unittest.mock import MagicMock, patch

from aden_tools.credentials import CredentialManager
from aden_tools.tools.postgres_tool.db import (
    MAX_ROWS,
    QUERY_TIMEOUT_MS,
    execute_read_query,
    validate_query,
)


class TestPostgresTool(unittest.TestCase):
    def test_validate_query_valid(self):
        """Test that valid queries pass validation."""
        valid_queries = [
            "SELECT * FROM users",
            "select id, name from products where price > 100",
            (
                "WITH regional_sales AS (SELECT region, SUM(amount) AS total_sales "
                "FROM orders GROUP BY region) SELECT region, total_sales FROM regional_sales "
                "WHERE total_sales > (SELECT SUM(total_sales)/10 FROM regional_sales)"
            ),
            "SELECT count(*) FROM logs",
        ]
        for q in valid_queries:
            try:
                validate_query(q)
            except ValueError as e:
                self.fail(f"Valid query raised ValueError: {e}")

    def test_validate_query_invalid(self):
        """Test that invalid queries (writes, DDL) fail validation."""
        invalid_queries = [
            "INSERT INTO users (name) VALUES ('hacker')",
            "UPDATE products SET price = 0",
            "DELETE FROM orders",
            "DROP TABLE users",
            "ALTER TABLE products ADD COLUMN secret text",
            "GRANT ALL PRIVILEGES ON DATABASE mydb TO hacker",
            "SELECT * FROM users; DROP TABLE logs",  # SQL Injection attempt
            "CREATE TABLE nothing (id int)",
            "TRUNCATE TABLE logs",
        ]
        for q in invalid_queries:
            with self.assertRaises(ValueError):
                validate_query(q)

    @patch("aden_tools.tools.postgres_tool.db.psycopg2")
    def test_execute_read_query_success(self, mock_psycopg2):
        """Test successful query execution."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock results
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchmany.return_value = [(1, "Alice"), (2, "Bob")]
        mock_cursor.fetchone.return_value = None  # No more rows

        results = execute_read_query("postgres://fake", "SELECT * FROM users")

        # Verify connection and cursor usage
        mock_psycopg2.connect.assert_called_with("postgres://fake")
        mock_conn.set_session.assert_called_with(readonly=True)
        mock_cursor.execute.assert_any_call(f"SET statement_timeout = {QUERY_TIMEOUT_MS};")
        mock_cursor.execute.assert_any_call("SELECT * FROM users")
        mock_cursor.fetchmany.assert_called_with(MAX_ROWS)

        # Verify results
        expected = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        self.assertEqual(results, expected)

    @patch("aden_tools.tools.postgres_tool.db.psycopg2")
    def test_execute_read_query_truncation(self, mock_psycopg2):
        """Test usage warning when results are truncated."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.description = [("id",)]
        # Simulate returning MAX_ROWS
        mock_cursor.fetchmany.return_value = [(i,) for i in range(MAX_ROWS)]
        # Simulate one more row exists
        mock_cursor.fetchone.return_value = (101,)

        with self.assertLogs("aden_tools.tools.postgres_tool.db", level="WARNING") as cm:
            results = execute_read_query("postgres://fake", "SELECT * FROM large_table")

        self.assertTrue(any("truncated" in o for o in cm.output))
        self.assertEqual(len(results), MAX_ROWS)

    @patch("aden_tools.tools.postgres_tool.db.execute_read_query")
    def test_tool_execution_flow(self, mock_execute):
        """
        Verify the connection between credentials and the execution function.
        """
        creds = CredentialManager.for_testing(
            {"postgres_connection_string": "cool_connection_string"}
        )

        # Simulate what the tool does
        try:
            creds.validate_for_tools(["postgres_read_query"])
            conn_str = creds.get("postgres_connection_string")
            mock_execute(conn_str, "SELECT 1")
        except Exception:
            self.fail("Tool logic raised exception")

        mock_execute.assert_called_with("cool_connection_string", "SELECT 1")

if __name__ == "__main__":
    unittest.main()
