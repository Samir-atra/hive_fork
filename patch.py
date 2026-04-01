import re

with open("core/framework/llm/router/task_classifier.py", "r") as f:
    content = f.read()

content = content.replace('def classify(self, prompt: str) -> str:', 'def classify(self, prompt: str | list) -> str:')
content = content.replace('if not prompt:\n            return "general"', '''if not prompt:
            return "general"

        if isinstance(prompt, list):
            # Extract text from multimodal prompt
            text_parts = []
            for item in prompt:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            prompt = " ".join(text_parts)

        if not isinstance(prompt, str):
            prompt = str(prompt)''')

with open("core/framework/llm/router/task_classifier.py", "w") as f:
    f.write(content)

with open("core/framework/llm/router/fallback_chain.py", "r") as f:
    content = f.read()

content = content.replace('if not constraints.required_capabilities:\n            constraints.required_capabilities = []\n        if task_category not in constraints.required_capabilities:\n             constraints.required_capabilities.append(task_category)', '''# Do not mutate the original constraints object
        req_caps = list(constraints.required_capabilities) if constraints.required_capabilities else []
        if task_category != "general" and task_category not in req_caps:
            req_caps.append(task_category)

        # We need to pass the modified capabilities to the evaluator
        # Create a temporary constraints object for evaluation
        eval_constraints = Constraints(
            max_budget=constraints.max_budget,
            max_latency_ms=constraints.max_latency_ms,
            required_context=constraints.required_context,
            required_capabilities=req_caps
        )''')

content = content.replace('is_valid, _ = self.evaluator.evaluate(candidate, constraints)', 'is_valid, _ = self.evaluator.evaluate(candidate, eval_constraints)')

with open("core/framework/llm/router/fallback_chain.py", "w") as f:
    f.write(content)

with open("core/framework/llm/router/router_node.py", "r") as f:
    content = f.read()

content = content.replace('def _determine_fallback_chain(\n        self,\n        prompt: str,\n', 'def _determine_fallback_chain(\n        self,\n        prompt: str | list,\n')

# Fix stream error logic
content = content.replace('''                    elif isinstance(event, StreamErrorEvent) and event.recoverable:
                         logger.warning(f"[router] Model {model} encountered recoverable stream error: {event.error}")
                         yield event
                         success = False
                         break # Break to fallback if stream itself yields error''', '''                    elif isinstance(event, StreamErrorEvent) and event.recoverable:
                        logger.warning(f"[router] Model {model} encountered recoverable stream error: {event.error}")
                        success = False
                        break # Break to fallback, DO NOT yield the error to the client''')

with open("core/framework/llm/router/router_node.py", "w") as f:
    f.write(content)
