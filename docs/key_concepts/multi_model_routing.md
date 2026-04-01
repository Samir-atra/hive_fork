# Multi-Model Routing

The Hive framework provides a `MultiModelRouterNode` capable of evaluating incoming prompts and automatically selecting the best LLM out of a registry of models without adding additional LLM-overhead logic to the execution path.

## Components

The Task-Aware Multi-Model Router consists of the following components:

- **Task Classifier**: Uses simple Regex-based matching logic (a "fast-path") to identify the implicit requirements of an incoming task based on keywords (e.g. math functions, code writing, general querying).
- **Model Registry**: A predefined set of `ModelProfiles` which organize available models into tiers (`simple`, `balanced`, `premium`), explicitly declaring their token costs, capabilities (e.g., `vision`, `coding`), and limits.
- **Constraint Evaluator**: Evaluates models to ensure they do not breach hard requirements passed into the router execution (such as `max_budget` per token or required features like `vision`).
- **Fallback Chain**: Given the requested tier and the available valid models, the system constructs an ordered list of viable alternatives. If the primary model goes down or streams a transient API error, the Router automatically proceeds down the fallback list to ensure robustness.
- **Routing Metrics**: Using the `EventBus`, the router pushes the decision structure (selected model, exact reasons for the top-2 rejections) backward into the Hive metrics and observability stack so performance can be tweaked.

## Usage

```python
from framework.llm.router import MultiModelRouterNode
from framework.llm.router.constraint_evaluator import Constraints

router = MultiModelRouterNode()
stream = router.execute(
    ctx=ctx,
    spec=spec,
    messages=[{"role": "user", "content": "Help me refactor this python script."}],
    constraints=Constraints(max_budget=0.005),
    preferred_tier="balanced"
)
```

The system will route "refactor this python script" as a `coding` task, look within the "balanced" models for a suitable model that has the `coding` capability and costs `<=0.005` per 1k input tokens, and fallback gracefully if the model returns a rate limit error.

### Force Model

If you explicitly want to bypass routing logic for a deterministic execution, you can provide `force_model="gpt-4o"` which disables all fallback and routing logic and executes immediately.
