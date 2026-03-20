# University Setup Guide

This guide is designed for educational institutions looking to adapt the **University Admin Navigation Agent** to their specific portals, systems, and structures.

## Overview

The template provided demonstrates how an AI agent can handle complex, multi-system navigation on behalf of a user (student, staff, or faculty). By default, the agent is configured to perform web searches to identify general structures. For a production deployment, you will want to customize it to point directly at your internal systems.

## Customization Steps

### 1. Update the Portal Navigator Node
In `nodes/__init__.py`, update `portal_navigator_node` to include specific knowledge about your institution's architecture.
- **Example:** Provide the exact URLs for your Registrar, Career Center, and Facilities booking system in the `system_prompt`.
- **Authentication:** If your portals require SSO (Single Sign-On), you can integrate an authentication tool or use cookies with the `web_scrape` tool (if supported) to allow the agent to navigate behind login walls.

### 2. Tailor the Form Detector
The `form_detector_node` currently looks for general terms like "form" or "application."
- Adjust the prompts to match your institution's specific naming conventions (e.g., "e-Transcript Gateway", "Workday Student", "Handshake").
- If your forms are purely digital (e.g., a multi-step web form instead of a PDF), you might add a tool that can interact with form fields directly.

### 3. Add Custom Tools
If your university provides APIs for certain systems (e.g., an API to check room availability or an API to submit an IT ticket), you should:
1. Create a custom tool wrapping your API.
2. Register the tool in `agent.py`.
3. Give the relevant nodes access to the tool.

## Example Use Cases

- **Admissions Onboarding:** Guide new students through the steps to set up their student ID, register for orientation, and complete health forms.
- **Faculty Support:** Help professors find the correct forms for grant applications, travel reimbursements, or syllabus templates.
- **IT Helpdesk Triage:** Navigate the user to the correct self-service knowledge base article before they submit a ticket.
