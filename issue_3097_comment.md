# Response to Issue #3097: AdenAI/Hive Agent Training

## Summary

Thanks for the thoughtful proposal! However, I believe this issue conflates two fundamentally different concepts of "training" and "learning." The SQR technique from the referenced paper doesn't apply to Hive's architecture.

## The Core Problem

### What SQR Does (From the Paper)

Selective Query Recollection (SQR) is a **neural network training technique** designed for query-based object detection models (DETR variants). It:

- Operates during **backpropagation** phases
- Modifies how **gradients flow** through decoder stages
- Updates **model weights** based on loss signals
- Requires differentiable computation graphs

### What Hive "Learning" Actually Is

Hive agents are **NOT neural networks** — they are:

- Orchestrated LLM API calls with tool execution
- Stateless graph traversals (no weights, no backprop)
- Iterative refinement via **feedback loops**, not weight updates

The "learning over time" mentioned in the docs refers to:

| Concept | Mechanism |
|---------|-----------|
| Judge feedback | Nodes retry based on ACCEPT/RETRY/ESCALATE verdicts |
| `max_node_visits` | Allows nodes to execute multiple times with accumulated context |
| Constraint checks | Hard/soft constraints gate completion |
| Iterative testing | Human-in-the-loop prompt refinement |

## Why the `stage` Proposal Doesn't Apply

The proposed `stage` variable in `agent.json` with query recollection assumes:

1. **Decoder stages with trainable queries** → Hive has no such architecture
2. **State retention across CI runs** → Each agent run is isolated; no persistent learning
3. **Learnable graph structure** → Nodes/edges are static configuration, not learned parameters

## Available "Training" Mechanisms in Hive

If you want agents to improve over time, Hive currently supports:

| Mechanism | How It Works |
|-----------|--------------|
| **Feedback Loops** | Set `max_node_visits > 1` to let nodes retry with judge feedback |
| **Judge Evaluation** | Custom judges can validate outputs and force retries |
| **Checkpoint Resume** | Resume execution from clean states after manual fixes |
| **Iterative Testing** | Test → Analyze logs → Fix prompts → Re-run cycle |
| **Prompt Engineering** | Manually refine `system_prompt` based on failure analysis |

## What Would Be Needed for True "Learning Over Time"

If the goal is agents that genuinely improve across sessions, this would require new infrastructure:

1. **Persistent memory across sessions**
   - Vector database storing past failures/successes
   - Retrieval-augmented context injection

2. **Dynamic prompt modification**
   - Automatic prompt updates based on historical performance
   - Example: "Last time this query failed because X, try Y instead"

3. **Meta-learning layer**
   - Track which prompts/tools work for which input types
   - Route similar inputs to successful strategies

This is a significant architectural addition — not a simple config change.

## Recommendation

- SQR is the wrong reference — it's for CNN/transformer weight optimization
- Consider instead: retrieval-augmented generation (RAG), few-shot learning with historical examples, or human feedback collection (RLHF-style)
- A new issue describing the *goal* (persistent learning) rather than a specific *implementation* (SQR) would be more actionable

---

*Happy to discuss further — this is an interesting direction for agent improvement!*
