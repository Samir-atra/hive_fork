import json
import random
import uuid


def fetch_internal_transactions(date_range: str) -> str:
    """Fetch transactions from the internal system for a given date range.

    Args:
        date_range (str): The date range (e.g., '2023-10-01 to 2023-10-31').

    Returns:
        str: JSON-encoded string of internal transactions.
    """
    return json.dumps(
        [
            {"id": "int_1", "amount": 100.0, "status": "completed", "reference": "ref_A"},
            {"id": "int_2", "amount": 50.0, "status": "failed", "reference": "ref_B"},
            {"id": "int_3", "amount": 200.0, "status": "completed", "reference": "ref_C"},
        ]
    )


def fetch_gateway_transactions(date_range: str) -> str:
    """Fetch transactions from the payment gateway for a given date range.

    Args:
        date_range (str): The date range.

    Returns:
        str: JSON-encoded string of gateway transactions.
    """
    return json.dumps(
        [
            {"id": "gw_1", "amount": 100.0, "status": "settled", "reference": "ref_A"},
            {"id": "gw_3", "amount": 190.0, "status": "settled", "reference": "ref_C"},
            {"id": "gw_4", "amount": 75.0, "status": "settled", "reference": "ref_D"},
        ]
    )


def process_refund(transaction_id: str, amount: float, reason: str) -> str:
    """Process a refund for a specific transaction in the gateway.

    Args:
        transaction_id (str): The gateway transaction ID.
        amount (float): The refund amount.
        reason (str): Reason for the refund.

    Returns:
        str: Result of the refund operation.
    """
    return json.dumps(
        {
            "status": "success",
            "refund_id": f"ref_{uuid.uuid4().hex[:8]}",
            "message": f"Refund of {amount} processed for {transaction_id}.",
        }
    )


def retry_failed_transaction(internal_id: str) -> str:
    """Retry a failed transaction from the internal system.

    Args:
        internal_id (str): The internal transaction ID.

    Returns:
        str: Result of the retry operation.
    """
    success = random.choice([True, False])
    if success:
        return json.dumps(
            {
                "status": "success",
                "message": f"Transaction {internal_id} retried.",
                "new_gw_id": f"gw_retry_{uuid.uuid4().hex[:8]}",
            }
        )
    else:
        return json.dumps({"status": "failed", "message": f"Retry for {internal_id} failed."})
