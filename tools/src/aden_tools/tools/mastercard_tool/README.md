# Mastercard Payment Tool

Integration with Mastercard Payment Gateway Services (MPGS) for secure payment processing, tokenization, and transaction management.

## Overview

This tool enables Hive agents to interact with Mastercard's payment infrastructure for:
- Tokenizing card details for PCI compliance friendly storage
- Authorizing payments (placing holds on funds)
- Executing direct payments (authorize and capture)
- Capturing previously authorized transactions
- Processing full or partial refunds
- Retrieving transaction status and details
- Verifying 3D Secure authentication eligibility

## Available Tools

This integration provides 8 MCP tools for comprehensive payment operations:

- `mastercard_create_token` - Securely store card details and return a non-sensitive token
- `mastercard_authorize` - Verify funds and place a hold without capturing
- `mastercard_pay` - Execute a direct payment (authorize and capture in one step)
- `mastercard_capture` - Capture funds from a previously authorized transaction
- `mastercard_refund` - Process full or partial refunds
- `mastercard_retrieve_transaction` - Fetch transaction status and details
- `mastercard_verify_service` - Validate 3D Secure (3DS) eligibility
- `mastercard_void` - Cancel a previously authorized transaction

## Setup

### 1. Get Mastercard API Credentials

1. Contact your Mastercard Payment Gateway provider
2. Obtain your Merchant ID and API Password
3. For testing, use the Mastercard Test Gateway (Sandbox)

### 2. Configure Environment Variables

```bash
export MASTERCARD_MERCHANT_ID="your_merchant_id"
export MASTERCARD_API_PASSWORD="your_api_password"
export MASTERCARD_BASE_URL="https://test-gateway.mastercard.com"  # Optional, defaults to test gateway
```

**Important:** Use the test gateway for development. Never commit production credentials to version control.

## Usage

### mastercard_create_token

Create a secure token for card details. Tokens allow you to store card information securely without handling sensitive data directly.

**Arguments:**
- `card_number` (str, required) - The card number (PAN)
- `card_expiry_month` (str, required) - Two-digit expiry month (e.g., "05")
- `card_expiry_year` (str, required) - Four-digit expiry year (e.g., "2027")
- `card_security_code` (str, optional) - Card security code (CVV/CVC)

**Example:**
```python
mastercard_create_token(
    card_number="5123456789012346",
    card_expiry_month="05",
    card_expiry_year="2027"
)
```

### mastercard_authorize

Authorize a payment to verify funds and place a hold without capturing.

**Arguments:**
- `order_id` (str, required) - Unique identifier for this order
- `amount` (str, required) - Amount in smallest currency unit (e.g., cents)
- `currency` (str, required) - ISO 4217 currency code (e.g., "USD")
- `token` (str, optional) - Previously created token (recommended)
- `card_number` (str, optional) - Card number (if not using token)
- `card_expiry_month` (str, optional) - Card expiry month (if not using token)
- `card_expiry_year` (str, optional) - Card expiry year (if not using token)
- `card_security_code` (str, optional) - Card security code (if not using token)
- `description` (str, optional) - Order description

**Example:**
```python
mastercard_authorize(
    order_id="order-123",
    amount="1000",
    currency="USD",
    token="1234567890123456"
)
```

### mastercard_pay

Execute a direct payment in one step (authorize and capture immediately).

**Arguments:**
- `order_id` (str, required) - Unique identifier for this order
- `amount` (str, required) - Amount in smallest currency unit (e.g., cents)
- `currency` (str, required) - ISO 4217 currency code (e.g., "USD")
- `token` (str, optional) - Previously created token (recommended)
- `card_number` (str, optional) - Card number (if not using token)
- `card_expiry_month` (str, optional) - Card expiry month (if not using token)
- `card_expiry_year` (str, optional) - Card expiry year (if not using token)
- `card_security_code` (str, optional) - Card security code (if not using token)
- `description` (str, optional) - Order description
- `authorize_first` (bool, default: False) - If True, authorize only (requires manual capture)

**Example:**
```python
mastercard_pay(
    order_id="order-456",
    amount="5000",
    currency="USD",
    token="1234567890123456",
    description="Flight booking payment"
)
```

### mastercard_capture

Capture funds from a previously authorized transaction.

**Arguments:**
- `order_id` (str, required) - Order ID from the original authorization
- `transaction_id` (str, required) - Transaction ID for the capture
- `amount` (str, optional) - Amount to capture (omit for full authorized amount)
- `currency` (str, optional) - Currency code (required if amount is specified)

**Example:**
```python
mastercard_capture(
    order_id="order-123",
    transaction_id="2",
    amount="1000",
    currency="USD"
)
```

### mastercard_refund

Process a full or partial refund.

**Arguments:**
- `order_id` (str, required) - Order ID from the original transaction
- `amount` (str, required) - Refund amount in smallest currency unit
- `currency` (str, required) - ISO 4217 currency code (e.g., "USD")
- `transaction_id` (str, optional) - Transaction ID for the refund
- `target_transaction_id` (str, optional) - Original transaction to refund

**Example:**
```python
# Full refund
mastercard_refund(
    order_id="order-456",
    amount="5000",
    currency="USD"
)

# Partial refund
mastercard_refund(
    order_id="order-456",
    amount="2500",
    currency="USD"
)
```

### mastercard_retrieve_transaction

Retrieve transaction status and details.

**Arguments:**
- `order_id` (str, required) - Order ID to query
- `transaction_id` (str, optional) - Specific transaction ID (omit for order summary)

**Example:**
```python
# Get order summary with all transactions
mastercard_retrieve_transaction(order_id="order-456")

# Get specific transaction details
mastercard_retrieve_transaction(order_id="order-456", transaction_id="1")
```

### mastercard_verify_service

Verify 3D Secure (3DS) authentication eligibility.

**Arguments:**
- `order_id` (str, required) - Unique identifier for this verification
- `transaction_id` (str, required) - Unique transaction ID for the verification
- `token` (str, optional) - Previously created token (recommended)
- `card_number` (str, optional) - Card number (if not using token)
- `card_expiry_month` (str, optional) - Card expiry month (if not using token)
- `card_expiry_year` (str, optional) - Card expiry year (if not using token)

**Example:**
```python
mastercard_verify_service(
    order_id="verify-123",
    transaction_id="1",
    token="1234567890123456"
)
```

### mastercard_void

Void a previously authorized transaction (release the hold without capturing).

**Arguments:**
- `order_id` (str, required) - Order ID from the original authorization
- `transaction_id` (str, required) - Transaction ID for this void operation
- `target_transaction_id` (str, required) - The authorization transaction to void

**Example:**
```python
mastercard_void(
    order_id="order-123",
    transaction_id="2",
    target_transaction_id="1"
)
```

## Authentication

Mastercard Payment Gateway uses HTTP Basic Authentication:
- **Username:** `merchant.{MASTERCARD_MERCHANT_ID}`
- **Password:** MASTERCARD_API_PASSWORD

The tool automatically constructs the auth tuple from your environment variables.

## Error Handling

All tools return error dicts for failures:

```json
{
  "error": "Invalid Mastercard API credentials"
}
```

Common errors:
- `401` - Invalid API credentials
- `403` - Insufficient permissions
- `404` - Resource not found
- `429` - Rate limit exceeded

## Testing

Use Mastercard's Test Gateway (Sandbox) for development:
1. Set `MASTERCARD_BASE_URL` to `https://test-gateway.mastercard.com`
2. Use test card numbers provided by Mastercard
3. No real charges will be processed

### Test Card Numbers

For testing, use these sample card numbers:
- `5123456789012346` - Visa (successful authorization)
- `5111111111111111` - Mastercard (successful authorization)
- Refer to Mastercard's documentation for more test cards

## Workflow Example: Flight Booking Payment

```python
# 1. Create token for customer's card
token_result = mastercard_create_token(
    card_number="5123456789012346",
    card_expiry_month="12",
    card_expiry_year="2027"
)
token = token_result["token"]

# 2. Authorize payment for flight booking
auth_result = mastercard_authorize(
    order_id="flight-booking-001",
    amount="50000",  # $500.00
    currency="USD",
    token=token,
    description="Flight to Paris"
)

# 3. Confirm booking and capture payment
capture_result = mastercard_capture(
    order_id="flight-booking-001",
    transaction_id="2"
)

# 4. If needed, refund the payment
refund_result = mastercard_refund(
    order_id="flight-booking-001",
    amount="50000",
    currency="USD"
)
```

## API Reference

- [Mastercard Integration Guidelines](https://test-gateway.mastercard.com/api/documentation/integrationGuidelines/index.html)
- [API Reference](https://test-gateway.mastercard.com/api/documentation/apiDocumentation/index.html)
- [3D Secure Integration](https://test-gateway.mastercard.com/api/documentation/integrationGuidelines/supportedFeatures/pickAdditionalFunctionality/authentication/3DS/3DS.html)
