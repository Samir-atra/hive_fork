# Baserow Tool

Structured data backend for agent workflows. Provides persistent, shared storage for cross-agent coordination and long-running process tracking.

## Features
- **Persistent Storage**: Save agent state and workflow data.
- **Shared Access**: Multiple agents can read from and write to the same tables.
- **Human-Readable**: Uses human-readable field names for easy developer interaction.
- **Self-Hostable**: Supports both baserow.io and self-hosted instances.

## Configuration

Set the following environment variables or configure via the Hive Credential Store:

- `BASEROW_TOKEN`: Your Baserow Database Token.
- `BASEROW_URL` (Optional): Custom base URL (e.g., `https://baserow.example.com`). Defaults to `https://api.baserow.io`.

### Getting a Database Token
1. Log in to your Baserow account.
2. Go to **User Settings** (bottom left profile icon).
3. Select **Database tokens**.
4. Create a new token with appropriate workspace permissions.

## Available Tools

### `baserow_list_rows`
List rows from a Baserow table.
- `table_id` (int): ID of the table.
- `search` (str, optional): Search term.
- `order_by` (str, optional): Sort field (e.g., `name` or `-created_at`).
- `limit` (int, default=100): Max rows to return.

### `baserow_get_row`
Get a specific row by ID.
- `table_id` (int): ID of the table.
- `row_id` (int): ID of the row.

### `baserow_create_row`
Create a new row.
- `table_id` (int): ID of the table.
- `data` (dict): Field values (e.g., `{"Name": "John Doe", "Project": "Hive Integration"}`).

### `baserow_update_row`
Update an existing row.
- `table_id` (int): ID of the table.
- `row_id` (int): ID of the row.
- `data` (dict): Fields to update.

### `baserow_delete_row`
Delete a row.
- `table_id` (int): ID of the table.
- `row_id` (int): ID of the row.

## Example Workflow

### Scraper Agent
Writes found leads to a "Leads" table.
```python
baserow_create_row(table_id=123, data={"Company": "Acme Corp", "Website": "acme.com"})
```

### Scoring Agent
Filters for unscored leads and updates their score.
```python
leads = baserow_list_rows(table_id=123, search="Acme")
baserow_update_row(table_id=123, row_id=leads['results'][0]['id'], data={"Score": 85})
```

### Outreach Agent
Triggers action for leads with score > 80.
```python
high_quality_leads = baserow_list_rows(table_id=123) # Filtering handled by agent logic or future filter query support
```
