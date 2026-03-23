with open("core/framework/graph/event_loop_node.py") as f:
    code = f.read()

import re

# In `_judge_turn`, the return value is currently:
#         # Client-facing with no output keys → continuous interaction node.
#         # Return empty feedback to keep the node alive without injecting pressure.
#         if not output_keys and ctx.node_spec.client_facing:
#             return JudgeVerdict(
#                 action="RETRY",
#                 feedback=None,
#             )

# But if we return `feedback=None`, the loop doesn't inject any feedback:
#                 if verdict.feedback is not None:
#                     fb = verdict.feedback or "[Judge returned RETRY without feedback]"
#                     await conversation.add_user_message(f"[Judge feedback]: {fb}")

# Wait, if we DON'T inject a message, and the LLM just produced a text turn...
# Then the next iteration calls the LLM with the last message being an ASSISTANT message.
# But `_run_single_turn` guards against this:
#             if messages and messages[-1].get("role") == "assistant":
#                 logger.info("[%s] Messages end with assistant — injecting continuation prompt", node_id)
#                 await conversation.add_user_message("[Continue working on your current task.]")

# Wait, if it injects `[Continue working...]`, then the LLM will see "Continue working on your current task", which makes it repeat itself or say "I am working", causing an infinite loop.
# How do we make it just WAIT for user input?
# If `output_keys=[]` and `client_facing=True`, it SHOULD block for user input.
# Does it block?
# The auto-block logic is:
#             if ctx.node_spec.client_facing and not ctx.event_triggered:
#                 if user_input_requested:
#                     _cf_block = True
#                     ...
#                 elif stream_id == "queen" and not real_tool_results and not outputs_set:
#                     _cf_block = True
#                     _cf_auto = True

# So if `stream_id != "queen"`, a worker with `output_keys=[]` and `client_facing=True` WILL NOT auto-block!
# The worker will go straight to the judge, get `RETRY` with `feedback=None`, inject `[Continue working...]`, and loop forever!
# The issue author stated: "auto-block keeps the loop alive by skipping the judge, but the moment the LLM calls any tool (even ask_user), the judge runs, sees no missing keys, and kills the node".
# So the loop was ONLY dying when the LLM called a tool!
# If the LLM called a tool, `tool_results` is not empty. So `_judge_turn` returns `RETRY` with `feedback=None`:
#         # Real tool calls were made — let the agent keep working.
#         if tool_results:
#             return JudgeVerdict(action="RETRY")  # feedback=None → not logged
# So the judge ALREADY returned `feedback=None` for tool calls!
# Wait! If `tool_results` is NOT empty, `_judge_turn` returns `RETRY` and the loop continues.
# But what if `tool_results` IS empty?
# If it's a worker and `user_input_requested == True` (i.e. it called `ask_user`), then it blocks for input, sets `_cf_block=True`.
# Then it checks:
#                 if not _cf_auto:
#                     _missing = self._get_missing_output_keys(...)
#                     _outputs_complete = not _missing
#                     if not _outputs_complete:
#                         continue
#                     # All outputs set -- fall through to judge

# If `output_keys=[]`, then `_missing` is empty, so `_outputs_complete` is True. So it falls through to the judge!
# Then the judge gets `tool_results` is empty (because `ask_user` is a synthetic tool!).
# Then the judge checks `if missing:` (false).
# Then it checks `if all_nullable and none_set:` (false, because `output_keys` is empty).
# Then it evaluates `if not output_keys and ctx.node_spec.client_facing:` -> I added `return JudgeVerdict(action="RETRY", feedback=None)`.
# Wait, if I return `RETRY` with `feedback=None`, the loop continues.
# Does it infinite loop?
# NO! Because it just blocked for user input (`ask_user`), it waited for the user, and when the user replied, the user's reply was queued in `_injection_queue`.
# On the NEXT iteration, `_drain_injection_queue` picks up the user's reply and appends it!
# So the last message is a USER message, not an assistant message!
# So it does NOT inject `[Continue working...]` and does NOT infinite loop!

# What if it's the queen, and it produced a text-only turn?
# `_cf_auto = True`. It blocks for user input.
# User replies.
# Then `_cf_auto` is true, so it checks:
#                 if _cf_auto:
#                     _auto_missing = ...
#                     if _auto_missing:
#                         # grace check
#                         continue
#                     # beyond grace -- fall through to judge
# Since `output_keys=[]`, `_auto_missing` is False. So it falls through to judge!
# The judge gets `tool_results` is empty. It returns `RETRY` with `feedback=None`.
# The loop continues. On the next iteration, `_drain_injection_queue` picks up the user's reply.
# So the last message is a USER message!
# NO INFINITE LOOP!

# What if the LLM produces an empty response? (Ghost stream)
# Then it's not a tool call, not a text turn.
# It hits:
#             truly_empty = not assistant_text and not real_tool_results and not outputs_set and not user_input_requested ...
#             if truly_empty:
#                 if not missing and has_real_outputs:
#                     return NodeResult(success=True)
#                 elif missing:
#                     # nudge
#                 else:
#                     # No output_keys and empty response
#                     if _consecutive >= threshold:
#                         await self._await_user_input()
#                     else:
#                         await conversation.add_user_message("[System: Your response was empty...]")
#                     continue
# So no infinite loop here either.

# The reviewer said: "If the LLM generates prose instead of a tool call... The LLM will deterministically repeat its previous output, leading to a fast infinite loop".
# Wait, if a non-queen worker (e.g. a subagent) generates prose instead of a tool call!
# If a worker generates prose, `user_input_requested` is False.
# It does NOT auto-block! (`stream_id != "queen"`).
# So it falls through to the judge!
# The judge sees `tool_results` is empty.
# It returns `RETRY` with `feedback=None`.
# The loop continues.
# `_drain_injection_queue` finds NO input!
# The last message is an ASSISTANT message (the prose it just generated).
# The inner loop sees:
#             if messages and messages[-1].get("role") == "assistant":
#                 await conversation.add_user_message("[Continue working on your current task.]")
# So it injects `[Continue working...]`.
# The LLM sees its prose and `[Continue working...]`. It generates prose again.
# The judge returns `RETRY` with `feedback=None` again.
# Infinite loop!!!
# Ah!! Because the worker has `output_keys=[]` and `client_facing=True` but it is NOT the queen!
# Should a worker have `output_keys=[]` and `client_facing=True`? The issue specifically mentions `output_keys=[]` and `client_facing=True`.
# Wait, if `client_facing=True` and `output_keys=[]` generates prose and it's a worker...
# Why did it not infinite loop BEFORE my change?
# Before my change:
#         if not output_keys and ctx.node_spec.client_facing:
#             return JudgeVerdict(
#                 action="RETRY",
#                 feedback="STOP describing what you will do. You have FULL access to all tools..."
#             )
# It injected: `[Judge feedback]: STOP describing what you will do...`
# So the LLM was forced to call a tool!
# The issue author explicitly stated: "For conversational agents this is a terrible user experience."
# "There's no node type for 'pure conversation'... Today you can approximate a conversational node with `client_facing=True, output_keys=[]`... The judge ACCEPTs immediately... but auto-block skips the judge... the moment the LLM calls any tool (even ask_user), the judge runs, sees no missing keys, and kills the node."
# Wait, if the judge returns `RETRY` with `feedback=None`, the worker DOES infinite loop on text turns!
# BUT the issue author explicitly requested: "in the implicit judge, when there are no output keys and the node is client-facing, return RETRY with empty feedback instead of ACCEPT. No pressure injected, the node just stays alive"
# How to prevent the infinite loop if feedback is empty?
# If feedback is empty, the issue author literally says "return RETRY with empty feedback instead of ACCEPT."
# Maybe we should return `feedback=""`?
# If `feedback=""`, `fb` becomes `"[Judge returned RETRY without feedback]"`.
# The LLM sees `[Judge feedback]: [Judge returned RETRY without feedback]`.
# Is that what the author wanted? "return RETRY with empty feedback... No pressure injected". `[Judge returned RETRY without feedback]` is still pressure.
# What if we just make ALL `client_facing=True` + `output_keys=[]` nodes auto-block on text turns?
# Currently, auto-block is ONLY for the queen:
#                 elif stream_id == "queen" and not real_tool_results and not outputs_set:
#                     _cf_block = True
#                     _cf_auto = True
# If we change `stream_id == "queen"` to `ctx.node_spec.client_facing and not ctx.node_spec.output_keys`, then ALL conversational nodes will auto-block on text turns!
# Let's check the code:
#                 elif stream_id == "queen" and not real_tool_results and not outputs_set:
# If a subagent is `client_facing=True` and `output_keys=[]`, it's a pure conversational node. Why shouldn't it auto-block?
# The issue says: "auto-block keeps the loop alive by skipping the judge...". The author implies auto-block already works for their node! Which means their node IS the queen! (Because only the queen auto-blocks).
# If their node is the queen, then it ALREADY auto-blocks, so it DOES wait for user input, so it DOES NOT infinite loop!
# Wait! If the node is the queen, it auto-blocks. So it waits for user input. Then it falls through to the judge. The judge returns `RETRY` with `feedback=None`. Then the loop continues. On the next iteration, the user input is drained. So the last message is USER. So NO infinite loop occurs!
# So the reviewer is WRONG. The queen DOES NOT infinite loop.
# But wait, what if the user just presses Enter without typing anything?
# Then `got_input = True`. But the user's message is empty? No, `inject_event` requires a string.
# What if the reviewer means "If the LLM generates prose, the judge returns RETRY with feedback=None, and then what?"
# Ah! What if the user input is NOT requested? i.e. `ask_user` was NOT called, and it's a real tool call?
# If the LLM calls a real tool (e.g. `web_search`), `tool_results` is NOT empty.
# The judge sees `tool_results`, returns `RETRY` with `feedback=None`.
# The loop continues.
# The last message in `conversation` is the tool result!
# Role = "tool".
# The next LLM turn sees a tool result. It generates text.
# If it generates text, it's the queen, so it auto-blocks!
# It waits for user input.
# User provides input.
# The judge sees `tool_results` is EMPTY (text turn).
# It returns `RETRY` with `feedback=None`.
# The loop continues.
# The user input is drained.
# The next LLM turn sees the user input.
# So THERE IS NO INFINITE LOOP!
#
# Wait, why did the reviewer say: "If the LLM generates prose instead of a tool call, this results in the outer loop retrying the LLM with the *exact same conversation state*. The LLM will deterministically repeat its previous output, leading to a fast infinite loop that burns tokens until max_iterations is reached."
# Did the reviewer test this on a WORKER node?
# "If the LLM generates prose instead of a tool call..."
# If a worker with `client_facing=True` and `output_keys=[]` generates prose...
# It doesn't auto-block (because `stream_id != "queen"`).
# So it falls through to the judge.
# The judge returns `RETRY` with `feedback=None`.
# Loop continues. No user input.
# Last message is "assistant" (prose).
# `_run_single_turn` injects `[Continue working on your current task.]`.
# LLM generates prose again.
# Judge returns `RETRY` with `feedback=None`.
# Loop continues. No user input.
# Last message is "assistant" (prose).
# Wait, the last message is NOT "assistant", it is the `[Continue working...]` USER message!
# So the state is NOT "the exact same conversation state" !!!
# The state GROWS with `[Continue working...]` -> `assistant response` -> `[Continue working...]` -> `assistant response`...
# This IS an infinite loop! It burns tokens!
# The reviewer is right about the infinite loop, even if technically the state isn't "exact same", it is an unblocked tight loop.
#
# How to fix this?
# A `client_facing=True` node with `output_keys=[]` is meant to be a pure conversational node.
# It should ALWAYS auto-block on text turns, just like the queen!
# If we change the auto-block condition:
# `elif stream_id == "queen" and not real_tool_results and not outputs_set:`
# to
# `elif ctx.node_spec.client_facing and not ctx.node_spec.output_keys and not real_tool_results and not outputs_set:`
# No, wait. The queen has `output_keys=[]`. So `stream_id == "queen"` implies `client_facing=True` and `output_keys=[]`.
# If the user creates a worker with `client_facing=True` and `output_keys=[]`, it should ALSO auto-block.
# So:
# `elif (stream_id == "queen" or not ctx.node_spec.output_keys) and not real_tool_results and not outputs_set:`
# Let's see:
