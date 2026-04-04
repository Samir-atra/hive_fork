# Reddit Business Opportunity Scanner Agent

A Hive agent that monitors targeted subreddits, identifies business opportunities, and drafts outreach messages for Human-in-the-Loop (HITL) approval.

## Overview

This agent helps businesses and indie founders find potential customers, validate ideas, and identify recurring pain points on Reddit. It monitors specified subreddits, uses an LLM to score posts for business signals (like problem severity, audience size, urgency), drafts personalized outreach, and requires human approval before logging to Airtable or taking action.

## Key Features

- **Automated Monitoring:** Scans configured subreddits regularly.
- **Smart Filtering & Scoring:** Filters by keywords and uses an LLM to score posts based on business potential.
- **Enrichment:** Automatically scrapes linked websites for additional context.
- **Personalized Outreach:** Drafts non-spammy, tailored outreach messages.
- **Human-in-the-Loop (HITL):** Presents high-value leads and drafts for human approval before final action.

## Configuration

You can customize the following parameters in `config.py`:
- `subreddits`: List of subreddits to monitor (e.g., "SaaS", "entrepreneur").
- `keywords`: Keywords/phrases to look for (e.g., "frustrated with", "looking for").
- `score_threshold`: Minimum LLM score (0-10) required to surface a lead.
- `outreach_tone`: Tone of the generated outreach message (e.g., "helpful", "curious").
