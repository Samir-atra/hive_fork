"""Node definitions for Payment Reconciliation Agent."""

from framework.graph import NodeSpec

# Node 1: Extract Data
extract_node = NodeSpec(
    id="extract_data",
    name="Extract Transactions",
    description="Fetch transactions from internal and gateway systems for reconciliation.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["date_range"],
    output_keys=["internal_txns", "gateway_txns"],
    system_prompt="""\
You are a payment reconciliation data extraction specialist.
Your task is to fetch transactions for a given date range.

Steps:
1. Use fetch_internal_transactions with the provided date_range.
2. Use fetch_gateway_transactions with the provided date_range.
3. Call set_output("internal_txns", <results from step 1>)
4. Call set_output("gateway_txns", <results from step 2>)
""",
    tools=["fetch_internal_transactions", "fetch_gateway_transactions"],
)

# Node 2: Reconcile and Flag Discrepancies
reconcile_node = NodeSpec(
    id="reconcile",
    name="Reconcile Transactions",
    description="Match transactions across systems and identify anomalies.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["internal_txns", "gateway_txns"],
    output_keys=["matched", "discrepancies", "unmatched_internal", "unmatched_gateway"],
    system_prompt="""\
You are a reconciliation expert. You have internal_txns and gateway_txns.
Match them based on their 'reference' field.

1. Matched: Both systems have the transaction and the amounts are exactly equal.
2. Discrepancies: Both systems have the transaction, but amounts differ or statuses conflict.
3. Unmatched Internal: In internal system but not in gateway. (e.g., failed payments)
4. Unmatched Gateway: In gateway but not in internal system. (e.g., unrecognized settlements)

Analyze the JSON strings you received, then:
- Call set_output("matched", <JSON string list of matched txns>)
- Call set_output("discrepancies", <JSON string list of discrepancies>)
- Call set_output("unmatched_internal", <JSON string list of internal txns not in gateway>)
- Call set_output("unmatched_gateway", <JSON string list of gateway txns not in internal>)
""",
    tools=[],
)

# Node 3: Resolve Discrepancies
resolve_node = NodeSpec(
    id="resolve",
    name="Resolve Discrepancies",
    description="Take actions on unmatched or failed transactions.",
    node_type="event_loop",
    client_facing=False,
    input_keys=["discrepancies", "unmatched_internal", "unmatched_gateway"],
    output_keys=["resolution_report"],
    system_prompt="""\
You are a payment operations specialist. Review the discrepancies and unmatched transactions.

Rules for resolution:
1. Unmatched Internal (failed payments): For each transaction in unmatched_internal
   with status 'failed', use retry_failed_transaction tool to retry it.
2. Unmatched Gateway: For each transaction in unmatched_gateway, these are extra charges.
   Use process_refund tool to issue a refund for the full amount.
   Reason: "Unrecognized transaction".
3. Discrepancies (amount mismatches): If gateway amount > internal amount,
   refund the difference. Use process_refund. Reason: "Overcharge".

After taking actions, summarize all actions taken into a single string report.
Call set_output("resolution_report", <the summary string>).
""",
    tools=["retry_failed_transaction", "process_refund"],
)

# Node 4: Final Report
report_node = NodeSpec(
    id="report",
    name="Generate Report",
    description="Compile the final reconciliation report.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["matched", "resolution_report", "date_range"],
    output_keys=["final_report"],
    system_prompt="""\
You are a reporting assistant. You need to present the final reconciliation results to the user.

1. Write a clear summary covering:
   - Date Range analyzed.
   - Number of perfectly matched transactions.
   - Summary of resolutions applied (refunds, retries) based on the resolution_report.
2. Send this summary to the user (text only, no tool calls).
3. Ask the user if they approve the report.

If they say yes, call set_output("final_report", <the full report>).
""",
    tools=[],
)
