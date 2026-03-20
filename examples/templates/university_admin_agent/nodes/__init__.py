"""Node definitions for University Admin Navigation Agent."""

from framework.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Understand what administrative task the user needs help with (e.g., transcript request, room booking, student jobs).",
    node_type="event_loop",
    client_facing=True,
    input_keys=["user_input"],
    output_keys=["admin_task_brief"],
    system_prompt="""\
You are the intake assistant for a University Admin Navigation Agent.

**STEP 1 — Greet and ask the user:**
Greet the user and ask what kind of administrative task they need help with. Examples:
- Transcripts and records
- Student ambassador or campus jobs
- Administrative processes like room booking or IT support

Keep it brief and friendly. If the user already provided their request in `user_input`, skip asking and acknowledge their request.

**STEP 2 — Set the task brief:**
Once you understand the user's need, call set_output to create a clear brief for the agent's navigation strategy.
- set_output("admin_task_brief", "<a concise description of the task and target portal/domain based on the user's request>")
""",
    tools=[],
)

portal_navigator_node = NodeSpec(
    id="portal-navigator",
    name="Portal Navigator",
    description="Determine the appropriate university portal (e.g., Registrar, Career Services, Facilities) and navigate to find relevant resources.",
    node_type="event_loop",
    input_keys=["admin_task_brief"],
    output_keys=["navigation_data"],
    system_prompt="""\
You are the Portal Navigator skill for a University Admin Navigation Agent.

Your task: Based on the admin_task_brief, search and identify the correct university portals and pages.

**Instructions:**
1. Determine what part of the university handles this request (e.g., "Registrar's Office" for transcripts, "Student Union" or "Career Center" for jobs, "Facilities" for room bookings).
2. Since this is an example template and we are not bound to a specific university, perform a web search for general examples or mock the navigation process by searching for common university processes regarding the requested task (e.g., "how to request university transcript form online").
3. Use web_search to find 2-3 examples of how universities structure these pages.
4. Use web_scrape to extract some details from one or two good examples.

**Output format:**
Use set_output("navigation_data", <JSON string>) with this structure:
```json
{
  "target_portal": "Registrar / Career Center / Facilities",
  "discovered_urls": ["https://...", "https://..."],
  "context": "Brief context about the portals found."
}
```
""",
    tools=["web_search", "web_scrape"],
)

form_detector_node = NodeSpec(
    id="form-detector",
    name="Form Detector",
    description="Analyze the navigated pages to identify specific forms, requirements, and deadlines.",
    node_type="event_loop",
    input_keys=["navigation_data"],
    output_keys=["resource_details"],
    system_prompt="""\
You are the Form Detector skill for a University Admin Navigation Agent.

Your task: Analyze the URLs provided in navigation_data to extract actionable steps, form links, requirements, or deadlines.

**Instructions:**
1. Read the `navigation_data`.
2. Use web_scrape on the provided URLs to look for specific forms (e.g., PDF links, portal login buttons, application forms), prerequisites, and contact information.
3. Synthesize what you find into structured resource details.

**Output format:**
Use set_output("resource_details", <JSON string>) with this structure:
```json
{
  "forms_found": [{"name": "Transcript Request Form", "url": "https://..."}],
  "requirements": ["Must provide student ID", "Fee of $10"],
  "deadlines": ["Rolling basis"],
  "instructions": ["Step 1...", "Step 2..."]
}
```
""",
    tools=["web_scrape"],
)

resource_mapper_node = NodeSpec(
    id="resource-mapper",
    name="Resource Mapper",
    description="Compile the navigation and form details into a clear, actionable guide for the user.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["resource_details", "navigation_data", "admin_task_brief"],
    output_keys=["solution_report"],
    system_prompt="""\
You are the Resource Mapper for a University Admin Navigation Agent.

Your task: Compile everything found into a clear, helpful response for the user.

**Instructions:**
1. Review the original `admin_task_brief`, `navigation_data`, and `resource_details`.
2. Create a well-structured markdown or plain text report that gives the user EXACTLY what they need to do to complete their administrative task.
3. Include direct links to forms/portals, a list of requirements, and step-by-step instructions.

**Output format:**
Use set_output("solution_report", "<your fully formatted report text here>")
""",
    tools=[],
)

__all__ = [
    "intake_node",
    "portal_navigator_node",
    "form_detector_node",
    "resource_mapper_node",
]
