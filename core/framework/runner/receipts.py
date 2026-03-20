"""Optional verifiable receipts (proof-of-delivery) integration using claw2claw."""

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def is_receipt_configured() -> bool:
    """Check if the verifiable receipts are configured."""
    return bool(
        os.environ.get("C2C_API_BASE")
        and os.environ.get("C2C_API_KEY")
        and os.environ.get("C2C_BOT_ID")
    )


def mint_receipt_sync(
    agent_name: str, agent_description: str, output_data: dict[str, Any]
) -> str | None:
    """Synchronously mint a verifiable receipt via claw2claw.

    This is an optional hook that emits a proof link per run/task.

    Args:
        agent_name: Title of the offer
        agent_description: Description of the offer
        output_data: Output of the agent run

    Returns:
        The proof URL if successful, otherwise None.
    """
    api_base = os.environ.get("C2C_API_BASE")
    api_key = os.environ.get("C2C_API_KEY")
    bot_id = os.environ.get("C2C_BOT_ID")

    if not api_base or not api_key or not bot_id:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    def _post(endpoint: str, payload: dict) -> dict:
        url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error(f"Failed to post receipt to claw2claw ({endpoint}): {e}")
            return {}

    try:
        # 1) create listing (offer)
        offer_payload = {
            "sellerBotId": bot_id,
            "title": agent_name,
            "description": agent_description or "Agent execution result",
            "priceCents": 0,
            "tags": ["agent", "hive"],
            "capabilities": [],
        }
        offer = _post("/offers", offer_payload)
        offer_id = offer.get("offerId")
        if not offer_id:
            return None

        # 2) hire it (create a job)
        job_payload = {
            "offerId": offer_id,
            "buyerBotId": bot_id,
            "idempotencyKey": None,
        }
        job = _post("/jobs", job_payload)
        job_id = job.get("jobId")
        if not job_id:
            return None

        # 3) deliver output + mint receipt
        # stringify outputs for artifacts
        artifacts = {}
        for k, v in output_data.items():
            artifacts[f"{k}.json"] = json.dumps(v, indent=2, default=str)

        receipt_payload = {
            "jobId": job_id,
            "status": "ok",
            "artifacts": artifacts,
        }
        proof = _post("/receipts", receipt_payload)
        return proof.get("proofUrl")

    except Exception as e:
        logger.error(f"Error while minting verifiable receipt: {e}")
        return None


async def mint_receipt_async(
    agent_name: str, agent_description: str, output_data: dict[str, Any]
) -> str | None:
    """Asynchronously mint a verifiable receipt via claw2claw."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, mint_receipt_sync, agent_name, agent_description, output_data
    )
