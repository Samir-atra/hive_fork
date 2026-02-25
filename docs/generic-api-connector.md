# Generic API Connector Integration

This guide demonstrates how to use the Generic API Connector to call any REST API without building a custom integration.

## Overview

The Generic API Connector provides three tools that allow agents to interact with any REST API:
- `generic_api_get` — GET requests
- `generic_api_post` — POST requests
- `generic_api_request` — Full HTTP method support (GET, POST, PUT, PATCH, DELETE)

## Quick Start

### 1. Configure Credentials

Set the `GENERIC_API_TOKEN` environment variable with your API token:

```bash
export GENERIC_API_TOKEN="your-api-token-here"
```

Or add it to Hive's credential store:

```python
from framework.credentials import CredentialStore

store = CredentialStore.with_encrypted_storage()
store.store("generic_api", {"api_token": "your-api-token-here"})
```

### 2. Use in Agent YAML

```yaml
goal: "Retrieve customer data from our internal CRM API"

tools:
  - generic_api_get
  - generic_api_post
  - generic_api_request
```

### 3. Call the API

The agent can now call your API:

```python
# GET request
result = generic_api_get(
    url="https://api.yourcompany.com/v1/customers/12345",
    auth_method="bearer"
)

# POST request
result = generic_api_post(
    url="https://api.yourcompany.com/v1/customers",
    body={"name": "John Doe", "email": "john@example.com"},
    auth_method="bearer"
)

# Full request with custom method
result = generic_api_request(
    url="https://api.yourcompany.com/v1/customers/12345",
    method="PATCH",
    body={"status": "active"},
    auth_method="custom_header",
    custom_header_name="X-Service-Token"
)
```

## Auth Methods

### Bearer Token (Default)

```python
generic_api_get(
    url="https://api.example.com/data",
    auth_method="bearer"
)
# Sends: Authorization: Bearer {GENERIC_API_TOKEN}
```

### API Key in Authorization Header

```python
generic_api_get(
    url="https://api.example.com/data",
    auth_method="api_key"
)
# Sends: Authorization: ApiKey {GENERIC_API_TOKEN}
```

### Basic Authentication

Set `GENERIC_API_TOKEN` as `username:password`:

```bash
export GENERIC_API_TOKEN="myuser:mypassword"
```

```python
generic_api_get(
    url="https://legacy.example.com/api",
    auth_method="basic"
)
# Sends: Authorization: Basic {base64(myuser:mypassword)}
```

### Custom Header

```python
generic_api_get(
    url="https://api.example.com/data",
    auth_method="custom_header",
    custom_header_name="X-API-Key"
)
# Sends: X-API-Key: {GENERIC_API_TOKEN}
```

### Query Parameter (Not Recommended)

```python
generic_api_get(
    url="https://api.example.com/data",
    auth_method="query_param",
    query_param_name="api_key"
)
# Sends: GET https://api.example.com/data?api_key={GENERIC_API_TOKEN}
```

### No Authentication

```python
generic_api_get(
    url="https://api.open-data.gov/datasets",
    auth_method="none"
)
# No authentication header
```

## Real-World Examples

### Internal ERP System

```yaml
goal: "Get current inventory levels for SKU ABC-123"

tools:
  - generic_api_get

context:
  erp_base_url: "https://erp.internal.company.com/api/v2"
```

The agent uses:

```python
result = generic_api_get(
    url="https://erp.internal.company.com/api/v2/inventory/SKU-ABC-123",
    auth_method="bearer"
)
```

### Legacy Billing System

```yaml
goal: "Create an invoice for customer C-12345"

tools:
  - generic_api_post

context:
  customer_id: "C-12345"
  amount: 199.99
  items: ["Widget A", "Widget B"]
```

The agent uses:

```python
result = generic_api_post(
    url="https://legacy.billing.company.com/invoices",
    body={
        "customer_id": "C-12345",
        "amount": 199.99,
        "line_items": [
            {"name": "Widget A", "price": 99.99},
            {"name": "Widget B", "price": 100.00}
        ]
    },
    auth_method="basic"  # GENERIC_API_TOKEN = "admin:secret"
)
```

### Multi-Step Workflow

```yaml
goal: |
  1. Check inventory for SKU ABC-123
  2. If stock < 10, create purchase order
  3. Send notification to procurement team

tools:
  - generic_api_get
  - generic_api_post
  - send_email
```

The agent orchestrates:

```python
# Step 1: Check inventory
inventory = generic_api_get(
    url="https://inventory.company.com/api/items/ABC-123",
    auth_method="bearer"
)

if inventory["body"]["stock"] < 10:
    # Step 2: Create purchase order
    po = generic_api_post(
        url="https://procurement.company.com/api/orders",
        body={
            "sku": "ABC-123",
            "quantity": 100,
            "urgency": "high"
        },
        auth_method="api_key"
    )
    
    # Step 3: Send notification (using existing email tool)
    send_email(
        to="procurement@company.com",
        subject=f"Low stock alert: ABC-123",
        body=f"Created PO #{po['body']['po_number']}"
    )
```

## Advanced Configuration

### Custom Headers

Add extra headers for versioning, tracking, etc.:

```python
generic_api_get(
    url="https://api.example.com/v2/data",
    auth_method="bearer",
    extra_headers={
        "X-API-Version": "2.0",
        "X-Request-ID": "req-12345",
        "Accept-Language": "en-US"
    }
)
```

### Query Parameters

```python
generic_api_get(
    url="https://api.example.com/customers",
    auth_method="bearer",
    params={
        "page": "1",
        "limit": "50",
        "status": "active"
    }
)
# GET https://api.example.com/customers?page=1&limit=50&status=active
```

### Timeout Configuration

```python
generic_api_get(
    url="https://slow-api.example.com/reports",
    auth_method="bearer",
    timeout=60.0  # Wait up to 60 seconds
)
```

## Error Handling

The connector returns structured error responses:

```python
result = generic_api_get(url="https://api.example.com/data")

if "error" in result:
    # Handle error
    print(f"Request failed: {result['error']}")
    if "help" in result:
        print(f"Suggestion: {result['help']}")
else:
    # Success - check status code
    if result["status_code"] == 200:
        data = result["body"]
        print(f"Got data: {data}")
    elif result["status_code"] == 404:
        print("Resource not found")
```

### Common Error Responses

```python
# Missing credential
{"error": "GENERIC_API_TOKEN not configured", "help": "Set the GENERIC_API_TOKEN..."}

# Invalid URL
{"error": "URL must be 1–2048 characters"}

# Timeout
{"error": "Request timed out"}

# Network error
{"error": "Network error: Connection refused"}

# Unsupported method
{"error": "Unsupported HTTP method: TRACE", "allowed": ["GET", "POST", "PUT", "PATCH", "DELETE"]}
```

## Retry Behavior

The connector automatically retries on transient errors:

- **HTTP 429** (Rate Limited) — up to 3 retries with exponential backoff
- **HTTP 500, 502, 503, 504** (Server Errors) — up to 3 retries
- **Network timeouts** — up to 3 retries

Backoff schedule: 1s, 2s, 4s (capped at 30s).

## Security Best Practices

1. **Use environment variables** — Never hardcode tokens in YAML or code
2. **Prefer Bearer auth** — More secure than query params or custom headers
3. **Use HTTPS only** — The connector accepts any URL, but always use HTTPS
4. **Rotate credentials** — Regularly rotate API tokens
5. **Limit permissions** — Use API tokens with minimal required permissions
6. **Monitor usage** — Track API calls in agent logs

## Multiple API Instances

To connect to multiple APIs, use environment variable prefixes:

```bash
export GENERIC_API_TOKEN="token-for-api-1"
export CRM_API_TOKEN="token-for-crm"
export ERP_API_TOKEN="token-for-erp"
```

Then in your tool calls, you can switch between tokens (requires custom wrapper).

## Health Check

When configuring credentials in the credential store, you can specify a health check endpoint:

```python
from aden_tools.credentials import check_credential_health

result = check_credential_health(
    credential_id="generic_api",
    credentials=credentials
)

if result.is_valid:
    print("Credential is valid")
else:
    print(f"Credential invalid: {result.error_message}")
```

The health check endpoint is user-configurable:
- Endpoint: `/health`, `/api/status`, or any safe GET endpoint
- Method: GET
- Response codes:
  - **200** → Valid
  - **401** → Invalid/expired
  - **403** → Valid but insufficient permissions
  - **429** → Rate limited (token still valid)

## Limitations (v1)

- **JSON only** — Request bodies and responses must be JSON
- **No file uploads** — Cannot send multipart/form-data
- **No streaming** — Entire response is buffered
- **No OAuth flows** — Only static tokens supported
- **No GraphQL** — REST APIs only

## Troubleshooting

### "GENERIC_API_TOKEN not configured"

**Solution**: Set the environment variable or add to credential store.

```bash
export GENERIC_API_TOKEN="your-token"
```

### "Request timed out"

**Solution**: Increase the timeout or check API responsiveness.

```python
generic_api_get(url="...", timeout=60.0)
```

### "Network error: Connection refused"

**Solution**: Verify the URL, check firewall rules, ensure the API is running.

### "Unsupported HTTP method"

**Solution**: Use GET, POST, PUT, PATCH, or DELETE only.

### 401 Unauthorized

**Solution**: Check that your token is valid and hasn't expired.

### 403 Forbidden

**Solution**: Your token is valid but lacks required permissions. Update scopes/permissions.

### 429 Rate Limited

**Solution**: The connector will automatically retry. If persistent, reduce request frequency.

## Related Issues

- [#2805](https://github.com/adenhq/hive/issues/2805) — Multi-step workflow orchestration
- [#4381](https://github.com/adenhq/hive/issues/4381) — Generic API Connector (this implementation)

## See Also

- [Credential Store Design](../credential-store-design.md)
- [Credential Store Usage](../credential-store-usage.md)
- [Tool Development Guide](../developer-guide.md)
