"""Node definitions for Revenue Recovery Agent."""

from framework.graph import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Campaign Intake",
    description=(
        "Gather campaign parameters from the operator: recovery type, time window, "
        "and targeting criteria"
    ),
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=["campaign_request"],
    output_keys=["campaign_config"],
    success_criteria=(
        "Campaign configuration is complete: includes recovery type "
        "(abandoned_cart, failed_payment, lapsed_buyer), time window, discount threshold, "
        "and any custom targeting rules."
    ),
    system_prompt="""\
You are a revenue recovery campaign intake specialist. The operator wants to run a campaign.

**STEP 1 — Gather requirements (text only, NO tool calls):**

Ask about:
1. **Recovery type**: Which segment to target?
   - Abandoned carts (customers who added items but didn't complete checkout)
   - Failed payments (orders that failed at payment stage)
   - Lapsed buyers (customers who haven't purchased in X days)

2. **Time window**: How far back to look? (e.g., last 7 days, last 30 days)

3. **Discount threshold**: Should we offer discounts? If so, at what cart value threshold?
   - Example: "Offer 10% discount for carts over $50"

4. **Custom rules**: Any specific targeting? (e.g., first-time buyers only, specific categories)

Keep the conversation brief. Make reasonable assumptions if the operator doesn't specify details.

**STEP 2 — After the operator confirms, call set_output:**
- set_output("campaign_config", JSON with: recovery_type, time_window_days,
  discount_threshold, discount_percent, custom_rules)
""",
    tools=[],
)

data_intake_node = NodeSpec(
    id="data_intake",
    name="Fetch Store Data",
    description="Pull orders and customer data from Shopify based on campaign configuration",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=0,
    input_keys=["campaign_config"],
    output_keys=["customers_data", "recovery_candidates"],
    success_criteria=(
        "Fetched all relevant orders and customers from Shopify. Recovery candidates list "
        "includes customer email, cart/order value, items, and last activity date."
    ),
    system_prompt="""\
You are a data intake agent. Fetch relevant data from Shopify based on campaign configuration.

**Work in phases:**

1. **Fetch orders** using shopify_list_orders:
   - For abandoned carts: Look for orders with financial_status "pending" or incomplete checkouts
   - For failed payments: Look for orders with financial_status indicating failure
   - For lapsed buyers: You'll need customer data first

2. **Fetch customers** using shopify_list_customers:
   - Get customer list with orders_count and total_spent for segmentation

3. **Build recovery candidates list**:
   For each candidate, extract:
   - Customer email
   - Customer name
   - Cart/order value
   - Items in cart/order (titles, prices)
   - Last activity date
   - Customer lifetime value (total_spent)
   - Orders count

4. **Save data** for later use:
   - Use save_data(filename="candidates.json", data=...) to save the recovery candidates list
   - Use save_data(filename="customers.json", data=...) to save customer data

**Important:**
- Handle API errors gracefully
- If no candidates found, report that in the output
- Work in batches of 50 records max per API call
- Call set_output in a SEPARATE turn from other tool calls

When done, call set_output:
- set_output("customers_data", "Summary of customer data fetched")
- set_output("recovery_candidates", "Count and summary of recovery candidates found")
""",
    tools=[
        "shopify_list_orders",
        "shopify_get_order",
        "shopify_list_customers",
        "shopify_search_customers",
        "save_data",
        "load_data",
    ],
)

segmentation_node = NodeSpec(
    id="segmentation",
    name="Segment Customers",
    description="Segment recovery candidates by value tier, purchase history, and engagement level",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=0,
    input_keys=["recovery_candidates", "campaign_config"],
    output_keys=["segments"],
    success_criteria=(
        "Customers are segmented into meaningful groups: high_value, medium_value, low_value, "
        "first_time_buyer, repeat_buyer, with segment-specific outreach strategies."
    ),
    system_prompt="""\
You are a customer segmentation specialist. Segment the recovery candidates into meaningful groups.

**Load the data:**
First, call load_data(filename="candidates.json") to get the recovery candidates.

**Segmentation criteria:**

1. **Value tiers** (based on cart/order value):
   - High value: $100+
   - Medium value: $50-$99
   - Low value: Under $50

2. **Customer type**:
   - First-time buyer: orders_count == 0 or 1
   - Repeat buyer: orders_count >= 2

3. **Engagement level** (for lapsed buyers):
   - Recently lapsed: 30-60 days since last purchase
   - Moderately lapsed: 60-90 days
   - Long lapsed: 90+ days

4. **Discount eligibility** (based on campaign config):
   - Eligible for discount if cart value >= discount_threshold

**Output structure:**
Create segments with:
- segment_id (e.g., "high_value_first_time")
- customer_count
- avg_cart_value
- recommended_approach (tone, urgency level)
- discount_eligible (boolean)

Save the segmentation results:
- save_data(filename="segments.json", data=...)

When done, call set_output:
- set_output("segments", "JSON string describing each segment with counts and strategies")
""",
    tools=[
        "load_data",
        "save_data",
    ],
)

personalization_node = NodeSpec(
    id="personalization",
    name="Generate Recovery Messages",
    description="Generate personalized recovery emails for each segment with appropriate tone",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=0,
    input_keys=["segments", "campaign_config"],
    output_keys=["message_batches"],
    success_criteria=(
        "Generated personalized email content for each segment. Each message includes "
        "subject line, HTML body with product references, appropriate tone, and discount."
    ),
    system_prompt="""\
You are an email personalization specialist. Generate recovery emails for each customer segment.

**Load the data:**
- load_data(filename="segments.json") to get segment definitions
- load_data(filename="candidates.json") to get individual customer data

**Message generation rules:**

1. **Tone by value tier:**
   - High value ($100+): Professional, personalized, urgency without pressure
   - Medium value ($50-$99): Friendly, helpful, reminder-focused
   - Low value (Under $50): Casual, quick nudge, focus on convenience

2. **Tone by recovery type:**
   - Abandoned cart: "You left something behind" - helpful reminder
   - Failed payment: "We had trouble processing your payment" - supportive, solution-focused
   - Lapsed buyer: "We miss you" - warm, re-engagement focused

3. **Discount offers:**
   - Only include if customer is discount_eligible
   - Format: Clear discount code and expiration
   - Example: "Use code COMEBACK10 for 10% off your order"

4. **Personalization:**
   - Include customer name
   - Reference specific products in their cart
   - Include cart total

**Generate a sample message per segment** (not per customer):
- Create 1-3 example messages that can be used as templates
- These will be presented to the operator for approval

Save the messages:
- save_data(filename="message_templates.json", data=...)

When done, call set_output:
- set_output("message_batches", "JSON string with message templates for each segment")
""",
    tools=[
        "load_data",
        "save_data",
    ],
)

approval_node = NodeSpec(
    id="approval",
    name="Review & Approve Campaign",
    description="Present message samples to the operator for review and approval before sending",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=["message_batches", "segments"],
    output_keys=["approved", "feedback"],
    nullable_output_keys=["feedback"],
    success_criteria=(
        "Operator has reviewed the message samples and explicitly approved or requested changes. "
        "100% human approval before any outreach is sent."
    ),
    system_prompt="""\
You are presenting the recovery campaign for operator approval.

**STEP 1 — Present campaign summary (text only, NO tool calls):**

Show the operator:
1. **Campaign Overview**: Recovery type, time window, total candidates
2. **Segment Breakdown**: Count and avg value per segment
3. **Message Samples**: Show 1-2 example messages per segment
   - Include subject line and body preview
   - Highlight personalization elements
4. **Estimated Impact**: Number of emails to send per segment

Ask the operator:
- Do the segments look correct?
- Are the message tones appropriate?
- Any changes needed before approval?
- Ready to proceed with sending?

**STEP 2 — After the operator responds, call set_output:**
- If approved: set_output("approved", "true") and set_output("feedback", "")
- If changes needed: set_output("approved", "false") and
  set_output("feedback", "description of what to change")
""",
    tools=[],
)

send_node = NodeSpec(
    id="send",
    name="Send Recovery Emails",
    description="Dispatch approved recovery emails to customers via configured email provider",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=0,
    input_keys=["approved"],
    output_keys=["send_results"],
    success_criteria=(
        "All approved emails have been sent. Results include success count, failure count, "
        "and any error messages for failed sends."
    ),
    system_prompt="""\
You are an email dispatch agent. Send the approved recovery emails.

**Load the data:**
- load_data(filename="candidates.json") to get customer data
- load_data(filename="message_templates.json") to get approved messages
- load_data(filename="segments.json") to match customers to messages

**Send emails using send_email:**

For each customer:
1. Select the appropriate message template based on their segment
2. Personalize with their name and products
3. Call send_email with:
   - to: customer email
   - subject: personalized subject line
   - html: personalized HTML body
   - provider: "resend" (or "gmail" if configured)
   - from_email: Must be set from EMAIL_FROM env var or passed explicitly

**Important:**
- Track successes and failures
- If rate limited, wait and retry
- Save progress periodically

**After sending:**
- Save results: save_data(filename="send_results.json", data=...)
- Include: total_sent, successes, failures, timestamps

When done, call set_output:
- set_output("send_results", "JSON summary: total_sent, success_count, failure_count, any errors")
""",
    tools=[
        "send_email",
        "load_data",
        "save_data",
    ],
)

tracking_node = NodeSpec(
    id="tracking",
    name="Log Campaign Results",
    description="Log campaign results and generate recovery tracking report",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=["send_results"],
    output_keys=["campaign_report"],
    success_criteria=(
        "Campaign report generated with: emails sent, estimated reach, "
        "instructions for tracking conversions, and recommendations for future campaigns."
    ),
    system_prompt="""\
You are generating the final campaign report.

**STEP 1 — Compile results:**
- load_data(filename="send_results.json") to get send results
- load_data(filename="segments.json") to get segment summaries

**STEP 2 — Generate report (text only, NO tool calls):**

Present to the operator:
1. **Campaign Summary**
   - Recovery type targeted
   - Time window covered
   - Total candidates identified
   - Emails sent successfully

2. **Segment Breakdown**
   - Emails per segment
   - Estimated value at stake

3. **Tracking Instructions**
   - How to monitor conversions (check Shopify orders in next 72 hours)
   - Key metrics to watch: open rate, click rate, conversion rate

4. **Recommendations**
   - When to run follow-up campaigns
   - Suggested timing for next outreach
   - Segment-specific optimization tips

5. **Saved Files**
   - List all data files saved for this campaign

**STEP 3 — Save the report:**
- save_data(filename="campaign_report.html", data=...) with formatted HTML report

**STEP 4 — After presenting, call set_output:**
- set_output("campaign_report", "JSON summary of the campaign results and next steps")
""",
    tools=[
        "load_data",
        "save_data",
        "serve_file_to_user",
    ],
)

__all__ = [
    "intake_node",
    "data_intake_node",
    "segmentation_node",
    "personalization_node",
    "approval_node",
    "send_node",
    "tracking_node",
]
