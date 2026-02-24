# Email Assistant

**Version**: 1.0.0
**Type**: Multi-node agent

## Overview
An end-to-end Email Assistant agent for the Hive Framework. It handles fetching unread incoming emails, intent classification, automated response generation, and defined workflow logic.

Resolves #4188.

## Architecture

### Execution Flow
`fetch-emails` → `classify-intent` → `generate-reply` → `execute-workflow` → `report`

## Usage

```bash
python -m examples.templates.email_assistant [max_emails]
```
