from framework.graph import NodeSpec

execute_workflow_node = NodeSpec(
    id="execute-workflow",
    name="Execute Workflow Node",
    description="Executes specific workflow actions based on intent and generates replies.",
    reads=["replied_emails"],
    writes=["workflow_results"],
    system_prompt=(
        "Execute actions via tools for each email based on its intent and draft. "
        "For example, save drafted replies or send them, trash spam, or archive newsletters. "
        "Record the actions taken and output them as 'workflow_results'."
    )
)
