# PagerDuty Tool

Interact with PagerDuty incidents and services. This tool enables agents to manage critical issue escalations, track on-call rotations, and maintain incident lifecycles.

## 🛠️ Tools Available

- `pagerduty_trigger_incident`: Create a new incident for a specific service.
- `pagerduty_acknowledge_incident`: Mark an incident as acknowledged.
- `pagerduty_resolve_incident`: Mark an incident as resolved.
- `pagerduty_get_incident`: Retrieve detailed information about a specific incident.
- `pagerduty_list_incidents`: List and filter incidents by status or service.
- `pagerduty_add_incident_note`: Add a note to an existing incident.
- `pagerduty_list_services`: Find PagerDuty service IDs for incident routing.

## 🔐 Configuration

The PagerDuty tool requires a REST API Key.

### Environment Variables

Set the following environment variable:

```bash
export PAGERDUTY_API_KEY="your-pagerduty-api-key"
# Optional: Used for the 'From' header in some actions (acknowledge/resolve/note)
export PAGERDUTY_USER_EMAIL="your-email@example.com"
```

### Getting an API Key

1. Log in to your PagerDuty account.
2. Go to **Integrations** > **API Access Keys**.
3. Click **Create New API Key**.
4. Copy the key and save it securely.

## 📝 Usage Examples

### Triggering an Incident

```python
# The agent will automatically use this tool when asked to escalate an issue.
pagerduty_trigger_incident(
    title="Critical Database Latency detected in Production",
    service_id="P123ABC",
    urgency="high",
    details="Latency > 500ms for over 5 minutes. Affecting all user regions."
)
```

### Listing Active Incidents

```python
pagerduty_list_incidents(statuses=["triggered", "acknowledged"])
```
