# Aden Tools: Comprehensive Library Index

This file provides a structured overview of the tools available in the Aden framework. These tools are designed to work with the Model Context Protocol (MCP) and enable agents to interact with a wide variety of external systems.

## 📂 Directory Structure

- `tools/`
    - `src/aden_tools/`
        - `credentials/`: Secure credential management and specifications.
        - `tools/`: Individual tool implementations (organized by module).
        - `utils/`: Shared helper functions and utilities.
    - `tests/`: Unit and integration tests for all tools.
    - `mcp_server.py`: The main entry point for running the tools as an MCP server.
    - `BUILDING_TOOLS.md`: Detailed guide for developers creating new tools.

---

## 🛠️ Tool Catalog by Category

| Category | Tools | Description |
| :--- | :--- | :--- |
| **📁 Core & File System** | `view_file`, `write_to_file`, `list_dir`, `grep_search`, `replace_file_content`, `apply_diff`, `apply_patch`, `execute_command_tool` | Essential tools for local file operations, searching, and command execution. |
| **🔍 Search & OSINT** | `web_search` (Google/Brave), `exa_search`, `serpapi_tool`, `scholar_search`, `news_tool`, `exa_find_similar`, `exa_answer` | Intelligence tools for web crawling, academic research, and real-time news retrieval. |
| **💬 Collaboration & Communication** | `slack_tool`, `telegram_tool`, `discord_tool`, `email_tool`, `gmail_tool`, `linear_tool`, `pagerduty_tool` | Comprehensive integrations for messaging platforms, email management, and issue tracking. |
| **📊 Data & Analytics** | `csv_tool`, `excel_tool`, `bigquery_tool`, `postgres_tool`, `snowflake_tool`, `supabase_tool`, `mssql_tool` | Manipulation of structured data files (CSV, Excel) and querying of enterprise databases. |
| **💼 CRM & Business Ops** | `hubspot_tool`, `salesforce_tool`, `dynamics365_tool`, `pipedrive_tool`, `apollo_tool`, `quickbooks_tool`, `greenhouse_tool`, `razorpay_tool` | Management of sales pipelines, contacts, enrichment, and financial operations. |
| **🛡️ Security & Recon** | `ssl_tls_scanner`, `port_scanner`, `dns_security_scanner`, `subdomain_enumerator`, `tech_stack_detector`, `http_headers_scanner`, `risk_scorer` | Automated tools for infrastructure security auditing and surface area mapping. |
| **🤖 AI, Vision & Web** | `vision_tool`, `pdf_read_tool`, `web_scrape_tool`, `browser_use_tool` | High-level tools for OCR, image analysis, document parsing, and autonomous browser use. |
| **📦 Cloud & Infrastructure** | `docker_tool`, `dockerhub_tool`, `cloudwatch_tool`, `datadog_tool`, `sns_tool`, `sqs_tool`, `terraform_tool` | Interaction with cloud logs, message queues, containerized environments, and infrastructure as code. |
| **📅 Scheduling & Productivity** | `calendar_tool`, `google_meet_tool`, `calcom_tool`, `calendly_tool`, `time_tool` | Management of events, video conferencing, and timezone-aware time utilities. |

---

## 📜 Full Tool List (A-Z)

The following tool implementations are located in `src/aden_tools/tools/`:

- **airtable_tool**: Interact with Airtable bases and records.
- **apollo_tool**: Lead enrichment and person/company search.
- **arxiv_tool**: Search and retrieve research papers from arXiv.
- **baserow_tool**: Open-source no-code database interaction.
- **bigquery_tool**: Query and manage Google BigQuery datasets.
- **browser_use_tool**: Autonomous browser navigation and interaction.
- **calcom_tool / calendly_tool**: Scheduling and booking management.
- **calendar_tool**: Full Google Calendar integration.
- **cloudwatch_tool / datadog_tool**: Observability and log querying.
- **csv_tool / excel_tool**: Advanced tabular data manipulation.
- **discord_tool / slack_tool / telegram_tool**: Bot-based chat platform interactions.
- **dns_security_scanner**: Check DNS records for security misconfigurations.
- **docker_tool / dockerhub_tool**: Manage containers and images.
- **dynamics365_tool**: Microsoft Dynamics CRM integration.
- **email_tool / gmail_tool**: Send and manage emails across providers.
- **exa_search_tool**: AI-native semantic search.
- **file_system_toolkits**: High-performance local file utilities.
- **github_tool / gitlab_tool**: DevOps and repository automation.
- **google_ads_tool**: Monitor and manage ad campaigns.
- **google_maps_tool**: Geocoding, directions, and place search.
- **google_search_console_tool**: SEO and site performance metrics.
- **hubspot_tool**: CRM contact and deal management.
- **linear_tool**: Interaction with Linear issue tracking.
- **news_tool**: Real-time news and sentiment analysis.
- **pagerduty_tool**: Manage PagerDuty incidents and services.
- **pdf_read_tool**: Text and metadata extraction from PDF files.
- **port_scanner / subdomain_enumerator**: Network reconnaissance.
- **postgres_tool / snowflake_tool / mssql_tool**: Direct SQL database access.
- **razorpay_tool**: Payment link and invoice management.
- **salesforce_tool**: Salesforce CRM integration for leads, contacts, and opportunities.
- **serpapi_tool**: Scrape search engine results pages.
- **tech_stack_detector**: Identify technologies used by websites.
- **terraform_tool**: Infrastructure as Code automation via Terraform CLI.
- **vision_tool**: Google Cloud Vision image analysis.
- **web_scrape_tool**: Extract clean content from any URL.
- **zendesk_tool**: Support ticket and customer service management.

---

## 🛠️ Internal Implementation Details

### Credential Handling
Tools requiring API keys leverage the `aden_tools.credentials` module. Credentials can be provided via:
1.  **Encrypted Store**: `~/.hive/credentials` (managed via `quickstart.sh`).
2.  **Environment Variables**: e.g., `ANTHROPIC_API_KEY`, `BRAVE_SEARCH_API_KEY`.

### Integration with FastMCP
All tools are registered via the `register_all_tools(mcp, credentials)` function in `src/aden_tools/tools/__init__.py`. This ensures a unified interface for the MCP server.

---
*Created on 2026-02-17*
