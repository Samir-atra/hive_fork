"""
Pinecone vector database credentials.

Contains credentials for Pinecone integration enabling RAG agent workflows.
"""

from .base import CredentialSpec

PINECONE_CREDENTIALS = {
    "pinecone": CredentialSpec(
        env_var="PINECONE_API_KEY",
        tools=[
            "pinecone_list_indexes",
            "pinecone_create_index",
            "pinecone_describe_index",
            "pinecone_delete_index",
            "pinecone_upsert_vectors",
            "pinecone_query_vectors",
            "pinecone_fetch_vectors",
            "pinecone_delete_vectors",
            "pinecone_upsert_records",
            "pinecone_search_records",
            "pinecone_list_namespaces",
            "pinecone_delete_namespace",
        ],
        required=True,
        startup_required=False,
        help_url="https://app.pinecone.io/",
        description="Pinecone API key for vector database operations",
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To get a Pinecone API Key:
1. Go to https://app.pinecone.io/ and sign up or log in
2. Navigate to API Keys in the left sidebar
3. Click Create API Key or copy the default key
4. Copy the API key value""",
        health_check_endpoint="https://api.pinecone.io/indexes",
        health_check_method="GET",
        credential_id="pinecone",
        credential_key="api_key",
    ),
}
