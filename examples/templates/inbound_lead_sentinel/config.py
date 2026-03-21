"""Configuration for the Inbound Lead Sentinel."""

from pydantic import BaseModel, Field


class SentinelMetadata(BaseModel):
    name: str = "inbound-lead-sentinel"
    version: str = "1.0.0"
    description: str = (
        "Automatically enriches new demo requests via Apollo.io, scores them "
        "against an ICP using the Queen Bee engine, and routes high-scoring leads "
        "into Salesforce as Opportunities."
    )
    author: str = "Aden HQ"


metadata = SentinelMetadata()


class SentinelConfig(BaseModel):
    model: str = "claude-3-5-sonnet-20241022"
    api_key: str | None = None
    api_base: str | None = None
    max_tokens: int = 4096

    # Threshold for creating a Salesforce opportunity
    icp_score_threshold: int = Field(
        default=75, description="Minimum ICP score to route to Salesforce"
    )

    # Circuit breaker settings to prevent runaway API calls
    max_leads_per_batch: int = Field(
        default=50, description="Max leads to process in a single batch"
    )


default_config = SentinelConfig()
