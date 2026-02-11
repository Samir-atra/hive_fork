# Production Readiness Guide

This guide helps you identify which use cases are ready for production with Hive today, and which are better suited for experimentation.

## Production-Ready Use Cases

These are scenarios where Hive excels in production environments today. They typically involve:
- **Clear Inputs & Outputs:** The task has a defined starting point and a verifiable end result.
- **Repeatable Processes:** The workflow, while dynamic, follows a general pattern (e.g., Intake -> Process -> Output).
- **Verifiable Success:** You can programmatically check if the output is correct (e.g., JSON schema validation, presence of specific keywords).

### Examples:
| Use Case | Why it works |
| :--- | :--- |
| **Data Enrichment** | Taking a list of companies and finding their latest funding rounds. Success is easily verified (field is not null). |
| **Content Moderation** | Reviewing user inputs against safety policies. Success criteria are clear (policy violation tags). |
| **Research & Reporting** | Searching the web for specific topics and summarizing them. Constraints (citation required) enforce quality. |
| **Customer Support Triage** | Categorizing incoming tickets and drafting responses. Human-in-the-loop nodes review drafts before sending. |

## Experimental Use Cases

These scenarios are possible with Hive but may require more iteration, stronger guardrails, or are currently less predictable.

### Examples:
| Use Case | Challenges |
| :--- | :--- |
| **Open-Ended Creative Writing** | "Write a funny blog post." Success is subjective and hard to measure programmatically. |
| **Zero-Shot Complex Coding** | "Build a full app from scratch." High probability of compounding errors without extensive feedback loops. |
| **High-Frequency Trading** | Real-time latency requirements may clash with LLM inference times. |

## Moving to Production

To take an experimental agent to production:

1.  **Define Hard Constraints:** Use `agent.json` to set budget limits and safety checks.
2.  **Add Human-in-the-Loop:** Insert approval nodes for critical actions (e.g., sending emails, executing code).
3.  **Implement Robust Evals:** Define strict success criteria (e.g., "Output must be valid JSON", "Must contain < 500 words").
4.  **Monitor Costs:** Set daily budget caps in your provider settings and Hive configuration.
