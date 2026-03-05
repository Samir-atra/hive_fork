# Knowledge Agent

A RAG (Retrieval-Augmented Generation) based question-answering agent that answers questions from a knowledge base with proper source citations.

## Features

- **Semantic Search**: Uses vector embeddings to find relevant information
- **Source Citations**: Every answer includes citations from the knowledge base
- **Multi-step Reasoning**: Analyzes questions, retrieves context, and generates accurate answers
- **Interactive Q&A**: Supports both single-shot and conversational modes
- **Knowledge Base Management**: Easy document ingestion and vector storage

## Quick Start

### 1. Ingest Documents

First, populate the knowledge base with documents:

```bash
cd exports/knowledge_agent
PYTHONPATH=../.. uv run python scripts/ingest.py --docs ./knowledge_base/
```

This will:
- Read all `.md` and `.txt` files from the knowledge base directory
- Split documents into chunks
- Generate embeddings
- Store in a vector database

### 2. Validate the Agent

```bash
PYTHONPATH=../.. uv run python -m knowledge_agent validate
```

### 3. Ask Questions

**Single Question:**
```bash
PYTHONPATH=../.. uv run python -m knowledge_agent run --question "What are the key features of Hive?"
```

**Interactive Shell:**
```bash
PYTHONPATH=../.. uv run python -m knowledge_agent shell
```

**TUI Dashboard:**
```bash
PYTHONPATH=../.. uv run python -m knowledge_agent tui
```

## Architecture

```
query_analyzer -> retriever -> context_selector -> answer_generator -> query_analyzer (loop)
```

| Node | Type | Description |
|------|------|-------------|
| query_analyzer | client-facing | Analyze user question and extract key information |
| retriever | internal | Search knowledge base for relevant documents |
| context_selector | internal | Rank and select most relevant context |
| answer_generator | client-facing | Generate answer with citations |

## How It Works

### 1. Query Analysis
The agent analyzes your question to understand:
- Core intent (definition, how-to, comparison, etc.)
- Key entities and concepts
- Optimal search terms

### 2. Knowledge Retrieval
Searches the vector database using:
- Semantic similarity matching
- Relevance scoring
- Top-k result selection

### 3. Context Selection
Reviews retrieved documents and:
- Ranks by relevance
- Removes duplicates
- Ensures diversity
- Prepares context for answer generation

### 4. Answer Generation
Creates a comprehensive answer that:
- Uses only information from retrieved context
- Includes inline citations [Source: filename]
- Provides confidence score
- Indicates when information is insufficient

## Example Interaction

```
Question> What are the key features of Hive?

Searching knowledge base...

--- Answer ---

Based on the knowledge base:

**Key Features of Hive:**

1. **Goal-driven architecture** - Agents are organized around achieving specific goals with defined success criteria [Source: hive_overview.md]

2. **Graph-based execution** - Nodes represent tasks and edges define flow control, allowing complex workflows with branching logic [Source: architecture.md]

3. **Tool integration** - Built-in support for MCP tools with over 100+ pre-built tools available [Source: hive_overview.md]

4. **Memory system** - Provides SharedMemory for data passing between nodes and checkpointing for save/resume [Source: hive_overview.md]

5. **Event loop nodes** - LLM-powered nodes that can reason, call tools, and maintain conversation context [Source: architecture.md]

Sources: hive_overview.md, architecture.md
Confidence: 0.92
```

## CLI Commands

### Ingest Documents
```bash
# Ingest documents
PYTHONPATH=../.. uv run python scripts/ingest.py --docs ./knowledge_base/

# Rebuild vector store from scratch
PYTHONPATH=../.. uv run python scripts/ingest.py --docs ./knowledge_base/ --rebuild
```

### Run Agent
```bash
# Ask a single question
PYTHONPATH=../.. uv run python -m knowledge_agent run --question "Your question here"

# Interactive shell
PYTHONPATH=../.. uv run python -m knowledge_agent shell

# TUI dashboard
PYTHONPATH=../.. uv run python -m knowledge_agent tui
```

### Utilities
```bash
# Show agent info
PYTHONPATH=../.. uv run python -m knowledge_agent info

# Validate agent structure
PYTHONPATH=../.. uv run python -m knowledge_agent validate
```

## Configuration

Configuration is managed through environment variables:

```bash
# LLM Configuration
export KNOWLEDGE_AGENT_MODEL="claude-3-5-sonnet-20241022"
export KNOWLEDGE_AGENT_API_KEY="your-api-key"
export KNOWLEDGE_AGENT_API_BASE="https://api.anthropic.com"

# Or use standard variables
export ANTHROPIC_API_KEY="your-api-key"
export OPENAI_API_KEY="your-api-key"
```

## Vector Store

The agent uses a simple JSON-based vector store for development:

**Location:** `~/.hive/knowledge_agent/vector_store.json`

**Structure:**
```json
{
  "chunks": [
    {
      "chunk_id": "abc123",
      "content": "Document text...",
      "source": "document.md",
      "start_index": 0,
      "end_index": 500
    }
  ],
  "embeddings": [[0.1, 0.2, ...]],
  "metadata": {}
}
```

### Production Upgrade

For production use, consider upgrading to:

**Option A: Pinecone**
- Managed vector database
- High performance at scale
- Use `pinecone_query_vectors` tool

**Option B: ChromaDB**
- Open-source vector store
- Runs locally or in production
- Easy integration

**Option C: FAISS**
- Facebook AI Similarity Search
- Efficient similarity search
- Local deployment

See the `mcp_servers.json` for configuration examples.

## Adding Custom Documents

1. Add `.md` or `.txt` files to `knowledge_base/` directory
2. Run the ingestion script:
   ```bash
   PYTHONPATH=../.. uv run python scripts/ingest.py --docs ./knowledge_base/
   ```
3. New documents will be available for querying

## Best Practices

### Document Preparation
- Use clear, well-structured documents
- Include headings and sections
- Keep documents focused on specific topics
- Avoid duplicate information

### Query Formulation
- Be specific in your questions
- Use relevant keywords
- Ask one question at a time
- Follow up for clarification if needed

### Knowledge Base Management
- Regularly update documents
- Rebuild vector store when adding significant content
- Monitor retrieval quality
- Remove outdated information

## Troubleshooting

### "Knowledge base is empty"
Run the ingestion script to populate the vector store:
```bash
PYTHONPATH=../.. uv run python scripts/ingest.py --docs ./knowledge_base/
```

### Poor Retrieval Quality
- Ensure documents are well-structured
- Check that queries match document terminology
- Consider adjusting chunk size in config
- Rebuild vector store with `--rebuild` flag

### API Key Issues
Set your API key:
```bash
export ANTHROPIC_API_KEY="your-key"
# or
export OPENAI_API_KEY="your-key"
```

## Technical Details

### Embedding Generation
Currently uses a simple hash-based embedding for demonstration. For production:
- Integrate OpenAI embeddings
- Use Anthropic embeddings
- Deploy local embedding models

### Similarity Search
Uses cosine similarity for vector matching:
```python
similarity = dot(embedding_a, embedding_b) / (norm(a) * norm(b))
```

### Chunking Strategy
- Default chunk size: 500 words
- Overlap: 50 words
- Prevents information loss at boundaries

## Future Enhancements

- [ ] Multiple knowledge bases
- [ ] Query expansion and reformulation
- [ ] Conversational follow-ups
- [ ] Source highlighting
- [ ] Confidence scoring improvements
- [ ] Integration with external vector DBs
- [ ] Real-time document updates
- [ ] Multi-language support

## Requirements

- Python 3.10+
- LLM API key (Anthropic or OpenAI)
- numpy (for vector operations)

## License

Part of the Hive framework. See main repository for license details.
