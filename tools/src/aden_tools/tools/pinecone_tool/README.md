# Pinecone Vector Database Tool

Vector database operations for RAG agent workflows.

## Overview

Pinecone is a managed vector database purpose-built for semantic search and retrieval-augmented generation (RAG). This integration enables Hive agents to store, query, and manage vector embeddings — unlocking workflows like knowledge base search, document retrieval, semantic deduplication, and multi-index cascading search.

## Tools Provided

| Tool | Description |
|------|-------------|
| `pinecone_list_indexes` | List all indexes in your Pinecone project |
| `pinecone_create_index` | Create a new serverless index |
| `pinecone_describe_index` | Get details about a specific index |
| `pinecone_delete_index` | Delete an index (permanent) |
| `pinecone_upsert_vectors` | Upsert vectors into an index |
| `pinecone_query_vectors` | Query for similar vectors |
| `pinecone_fetch_vectors` | Fetch vectors by ID |
| `pinecone_delete_vectors` | Delete vectors from an index |
| `pinecone_upsert_records` | Upsert records using integrated inference |
| `pinecone_search_records` | Search records using integrated inference |
| `pinecone_list_namespaces` | List all namespaces in an index |
| `pinecone_delete_namespace` | Delete a namespace (permanent) |

## Setup

### 1. Get API Key

1. Go to [https://app.pinecone.io/](https://app.pinecone.io/) and sign up or log in
2. Navigate to **API Keys** in the left sidebar
3. Click **Create API Key** or copy the default key
4. Copy the API key value

### 2. Configure Credentials

Set the environment variable:

```bash
export PINECONE_API_KEY=your_api_key_here
```

Or add to your `.env` file:

```
PINECONE_API_KEY=your_api_key_here
```

## Usage Examples

### Create an Index

```python
# Create a serverless index for OpenAI embeddings
pinecone_create_index(
    name="documents",
    dimension=1536,  # OpenAI ada-002 dimension
    metric="cosine",
    cloud="aws",
    region="us-east-1"
)
```

### Upsert Vectors

```python
# First get the index host from describe_index
index = pinecone_describe_index(name="documents")
host = index["index"]["host"]

# Upsert vectors
pinecone_upsert_vectors(
    index_host=host,
    vectors=[
        {
            "id": "doc1",
            "values": [0.1, 0.2, 0.3, ...],  # 1536 floats
            "metadata": {"title": "Document 1", "category": "tech"}
        },
        {
            "id": "doc2",
            "values": [0.4, 0.5, 0.6, ...],
            "metadata": {"title": "Document 2", "category": "news"}
        }
    ],
    namespace="production"
)
```

### Query Vectors

```python
# Query for similar vectors
results = pinecone_query_vectors(
    index_host=host,
    vector=query_embedding,  # Your query vector
    top_k=10,
    filter={"category": "tech"},  # Optional metadata filter
    include_metadata=True
)

# Access matches
for match in results["matches"]:
    print(f"ID: {match['id']}, Score: {match['score']}")
```

### Namespaces

```python
# List namespaces
namespaces = pinecone_list_namespaces(index_host=host)

# Delete a namespace (removes all vectors in it)
pinecone_delete_namespace(
    index_host=host,
    namespace="old-data"
)
```

## Integrated Inference

For indexes created with an embedding model, use record-based operations:

```python
# Upsert records (auto-embeds text)
pinecone_upsert_records(
    index_host=host,
    records=[
        {"_id": "doc1", "title": "AI News", "content": "Full text..."}
    ]
)

# Search records (auto-embeds query)
results = pinecone_search_records(
    index_host=host,
    query={"text": "artificial intelligence"},
    top_k=5
)
```

## API Reference

- [Pinecone API Docs](https://docs.pinecone.io/reference/api/introduction)
- [Python SDK](https://github.com/pinecone-io/pinecone-python-client)

## Free Tier

Starter plan includes:
- 2GB storage
- 1 index
- Unlimited reads

Sufficient for development and testing.
