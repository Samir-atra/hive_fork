from framework.graph import NodeSpec

report_node = NodeSpec(
    id="report",
    name="Report Node",
    description="Consolidates actions taken into a summary report.",
    reads=["workflow_results"],
    writes=["summary_report"],
    system_prompt=(
        "Create a comprehensive summary report of all the actions taken. "
        "Format it clearly for the user and return as 'summary_report'."
    )
)
