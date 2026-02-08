"""
Integration-related credential specifications (News, Market Intelligence).
"""

from .base import CredentialSpec

INTEGRATIONS_CREDENTIALS = {
    "newsdata": CredentialSpec(
        env_var="NEWSDATA_API_KEY",
        tools=[
            "news_search",
            "news_headlines",
            "news_by_company",
        ],
        description="API Key for NewsData.io (Primary news provider).",
        help_url="https://newsdata.io/api-documentation",
    ),
    "finlight": CredentialSpec(
        env_var="FINLIGHT_API_KEY",
        tools=[
            "news_sentiment",
        ],
        description="API Key for Finlight.me (Sentiment analysis & news).",
        help_url="https://finlight.me/docs",
        required=False,
    ),
}
