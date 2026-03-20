import json
from unittest.mock import MagicMock, patch

import pytest

from framework.runner.receipts import is_receipt_configured, mint_receipt_async, mint_receipt_sync


def test_is_receipt_configured_true(monkeypatch):
    monkeypatch.setenv("C2C_API_BASE", "https://claw2claw.com/api")
    monkeypatch.setenv("C2C_API_KEY", "test_key")
    monkeypatch.setenv("C2C_BOT_ID", "test_bot")
    assert is_receipt_configured() is True


def test_is_receipt_configured_false(monkeypatch):
    monkeypatch.delenv("C2C_API_KEY", raising=False)
    assert is_receipt_configured() is False


@patch("urllib.request.urlopen")
def test_mint_receipt_sync_success(mock_urlopen, monkeypatch):
    monkeypatch.setenv("C2C_API_BASE", "https://claw2claw.com/api")
    monkeypatch.setenv("C2C_API_KEY", "test_key")
    monkeypatch.setenv("C2C_BOT_ID", "test_bot")

    # Mock sequence: 1) /offers, 2) /jobs, 3) /receipts
    mock_responses = [
        MagicMock(read=lambda: json.dumps({"offerId": "offer_123"}).encode("utf-8")),
        MagicMock(read=lambda: json.dumps({"jobId": "job_123"}).encode("utf-8")),
        MagicMock(read=lambda: json.dumps({"proofUrl": "https://claw2claw.com/proof/123"}).encode("utf-8")),
    ]

    # Required for context manager simulation
    for r in mock_responses:
        r.__enter__.return_value = r

    mock_urlopen.side_effect = mock_responses

    proof_url = mint_receipt_sync(
        "Test Agent",
        "Test Description",
        {"output": "success"}
    )

    assert proof_url == "https://claw2claw.com/proof/123"
    assert mock_urlopen.call_count == 3


@pytest.mark.asyncio
@patch("urllib.request.urlopen")
async def test_mint_receipt_async_success(mock_urlopen, monkeypatch):
    monkeypatch.setenv("C2C_API_BASE", "https://claw2claw.com/api")
    monkeypatch.setenv("C2C_API_KEY", "test_key")
    monkeypatch.setenv("C2C_BOT_ID", "test_bot")

    mock_responses = [
        MagicMock(read=lambda: json.dumps({"offerId": "offer_123"}).encode("utf-8")),
        MagicMock(read=lambda: json.dumps({"jobId": "job_123"}).encode("utf-8")),
        MagicMock(read=lambda: json.dumps({"proofUrl": "https://claw2claw.com/proof/123"}).encode("utf-8")),
    ]
    for r in mock_responses:
        r.__enter__.return_value = r
    mock_urlopen.side_effect = mock_responses

    proof_url = await mint_receipt_async(
        "Test Agent",
        "Test Description",
        {"output": "success"}
    )

    assert proof_url == "https://claw2claw.com/proof/123"
    assert mock_urlopen.call_count == 3


@patch("urllib.request.urlopen")
def test_mint_receipt_sync_failure_no_offer(mock_urlopen, monkeypatch):
    monkeypatch.setenv("C2C_API_BASE", "https://claw2claw.com/api")
    monkeypatch.setenv("C2C_API_KEY", "test_key")
    monkeypatch.setenv("C2C_BOT_ID", "test_bot")

    # Mock /offers failing (missing offerId)
    mock_response = MagicMock(read=lambda: json.dumps({}).encode("utf-8"))
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    proof_url = mint_receipt_sync(
        "Test Agent",
        "Test Description",
        {"output": "success"}
    )

    assert proof_url is None
    assert mock_urlopen.call_count == 1
