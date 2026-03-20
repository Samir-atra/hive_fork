# University Admin Navigation Agent

The **University Admin Navigation Agent** is an example template demonstrating how an autonomous agent can navigate complex, multi-system environments like those found in educational institutions.

Universities often have administrative systems that are notoriously fragmented. This agent can help students, staff, and faculty locate forms, job postings, and processes that are typically scattered across various portals (e.g., admissions, finance, IT, and student services).

## Features

- **Multi-domain navigation:** Seamlessly handle different institutional websites.
- **Form detection:** Find required forms and processes for tasks like requesting transcripts or booking rooms.
- **Resource mapping:** Structure findings into a step-by-step summary for the user.

## Getting Started

### Prerequisites

Ensure you have the `hive` framework installed and active in your environment.

### Running the Agent

You can start the agent via the CLI. It will prompt you for your goal if you do not provide one.

```bash
uv run python -m examples.templates.university_admin_agent
```

Or you can run it with a specific goal directly:

```bash
uv run python -m examples.templates.university_admin_agent --goal "Navigate to transcript request form, identify requirements, and provide direct link"
```

## Agent Graph

This agent implements a 4-node pipeline:
1. **Intake:** Clarifies the user's specific administrative task.
2. **Portal Navigator:** Formulates a strategy and searches the web for the correct portal or system.
3. **Form Detector:** Analyzes the target URLs to extract specific links, requirements, or deadlines.
4. **Resource Mapper:** Synthesizes the findings into a clear, actionable guide for the user.

## Customization for Institutions

If you represent an educational institution and want to tailor this template for your own portals and single sign-on (SSO) systems, please see the [University Setup Guide](docs/UNIVERSITY_SETUP.md).
