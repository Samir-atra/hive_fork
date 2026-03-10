# Content Research Swarm

A multi-agent content pipeline that demonstrates Hive's sequential agent orchestration capabilities.

## Overview

The Content Research Swarm is a reference agent that shows how to build multi-agent workflows in Hive. It orchestrates three specialized agents:

1. **Research Agent** - Searches the web for relevant information on a topic
2. **Writer Agent** - Drafts content (Twitter thread or blog post) based on research
3. **Editor Agent** - Reviews, polishes, and delivers final content

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Research   │────▶│   Writer    │────▶│   Editor    │
│   Agent     │     │   Agent     │     │   Agent     │
└─────────────┘     └─────────────┘     └─────────────┘
                           ▲                   │
                           └───────────────────┘
                             (revision loop)
```

## Features

- **Sequential Orchestration**: Agents work in a defined order with automatic handoffs
- **Shared Context**: Research findings flow seamlessly to writer, then to editor
- **Feedback Loop**: Editor can request revisions from the writer
- **Client Interaction**: Editor node is client-facing for user approval
- **Web Research**: Uses web search and scrape tools to gather information

## Installation

This agent is part of the Hive framework. Ensure you have Hive installed:

```bash
cd core
pip install -e .
```

## Usage

### CLI

```bash
# Run with a topic
python -m examples.templates.content_research_swarm run --topic "AI trends 2024"

# Interactive shell
python -m examples.templates.content_research_swarm shell

# Launch TUI dashboard
python -m examples.templates.content_research_swarm tui

# Show agent info
python -m examples.templates.content_research_swarm info

# Validate structure
python -m examples.templates.content_research_swarm validate
```

### Programmatic

```python
from examples.templates.content_research_swarm import ContentResearchSwarmAgent

async def main():
    agent = ContentResearchSwarmAgent()
    await agent.start()
    
    result = await agent.trigger_and_wait(
        "start",
        {"content_brief": "Latest developments in renewable energy"}
    )
    
    print(result.output)
    await agent.stop()

import asyncio
asyncio.run(main())
```

## Architecture

### Nodes

| Node | Type | Tools | Description |
|------|------|-------|-------------|
| `research` | event_loop | web_search, web_scrape, save_data, load_data | Gathers information from web sources |
| `writer` | event_loop | save_data, append_data, load_data | Creates draft content |
| `editor` | event_loop, client_facing | save_data, serve_file_to_user | Reviews and delivers final content |

### Context Flow

```
research_brief → [Research] → research_findings, source_list
                              ↓
                 [Writer] ← revision_feedback
                              ↓
                        draft_content, content_type
                              ↓
                 [Editor] → final_content, delivery_status
                    ↓
            needs_revision (loops back to Writer if True)
```

### Edges

| From | To | Condition | Description |
|------|----|-----------|-------------|
| research | writer | ON_SUCCESS | Normal flow after research |
| writer | editor | ON_SUCCESS | Normal flow after writing |
| editor | writer | needs_revision == True | Revision requested |

## Goals and Success Criteria

The agent tracks progress against these success criteria:

1. **Research Complete** - 3+ sources gathered
2. **Draft Created** - Complete draft based on findings
3. **Content Edited** - Content reviewed and polished
4. **Content Delivered** - Final content approved by user

## Use Cases

This agent pattern is useful for:

- Content marketers creating social media posts
- Social media managers planning content calendars
- Indie hackers building in public
- Anyone who needs researched, polished content

## Extending

To add more capabilities:

1. **Add RSS feed support** - Include RSS parsing tools in the research node
2. **Add scheduling** - Create a scheduling node for content publishing
3. **Add analytics** - Track content performance after publishing
4. **Multi-platform output** - Generate content for multiple platforms (Twitter, LinkedIn, etc.)

## License

Part of the Hive framework. See main repository for license details.
