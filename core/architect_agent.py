import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from framework.llm.provider import LLMProvider

class ArchitectAgent:
    def __init__(self, provider: Optional[LLMProvider] = None, exports_dir: str = "../exports"):
        self.provider = provider
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def generate_agent(self, user_prompt: str) -> Dict[str, Any]:
        """
        Generates a functional Hive agent based on the user prompt using an LLM.
        """
        # Sanitize prompt for folder name
        safe_name = re.sub(r'[^a-z0-9]', '_', user_prompt.lower()[:20]).strip('_')
        timestamp = os.popen('date +%s').read().strip()
        agent_id = f"{safe_name}_{timestamp}"
        agent_dir = self.exports_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        if self.provider:
            # Use the provider's model in the prompt so the generated agent uses the same high-quality model
            current_model = self.provider.model
            system_prompt = f"""
You are the Hive Architect, an expert in generating valid Python code for the 'Hive Agentic Platform' framework.
Your task is to generate a fully functional, valid `agent.py` file for the agent named '{agent_id}'.

Framework Rules:
1. ALWAYS use the following imports:
   import asyncio
   from framework.graph import GraphSpec, NodeSpec, EdgeSpec, EdgeCondition
   from framework.graph.executor import GraphExecutor
   from framework.runtime.core import Runtime
   from framework.llm.litellm import LiteLLMProvider
   from pathlib import Path

2. Define a `async def run_agent(input_data: str)` function.
3. Inside `run_agent`:
   a. Create a `LiteLLMProvider` (model="{current_model}").
   b. Create a `Runtime` with storage path: `Path("./logs/{agent_id}")`.
   c. Create a `GraphExecutor` using the runtime and the provider.
   d. Define at least 3 nodes (Analyzer, Researcher, Reporter) as local functions.
   e. Register these functions to the executor.
   f. Define a `GraphSpec` properly connecting Analyzer -> Researcher -> Reporter.
   g. EXECUTE the graph: `result = await executor.execute(graph, goal="{user_prompt}", initial_data={{"user_prompt": input_data}})`
   h. Return the final report from the result.

Provide ONLY the valid Python code for `agent.py`. DO NOT include any markdown code blocks (like ```python) or explanatory text.
Goal: {user_prompt}
"""
            try:
                response = self.provider.complete(
                    messages=[{"role": "user", "content": f"Generate agent.py for: {user_prompt}"}],
                    system=system_prompt.strip()
                )
                # Clean up response in case model includes markdown markers
                agent_code = response.content.strip()
                if "```python" in agent_code:
                    agent_code = agent_code.split("```python")[1].split("```")[0].strip()
                elif "```" in agent_code:
                    agent_code = agent_code.split("```")[1].split("```")[0].strip()
                
                if not agent_code:
                    raise ValueError("LLM returned empty content")
                    
            except Exception as e:
                print(f"Architect LLM Call Failed: {e}")
                # Fallback to a better functional template if LLM fails
                agent_code = self._get_fallback_template(agent_id, user_prompt)
        else:
            agent_code = self._get_fallback_template(agent_id, user_prompt)

        
        # Generate README.md
        readme_content = f"""# Agent: {agent_id}
## Generator
{self.provider.model if self.provider else "Template/Static"}

## Goal
{user_prompt}

## Usage
Run `python agent.py` to execute.
"""

        (agent_dir / "agent.py").write_text(agent_code)
        (agent_dir / "README.md").write_text(readme_content)

        return {
            "agent_id": agent_id,
            "generator": self.provider.model if self.provider else "Static Template",
            "path": str(agent_dir),
            "files": ["agent.py", "README.md"]
        }

    def _get_fallback_template(self, agent_id: str, user_prompt: str) -> str:
        """Returns a valid, functional fallback agent template."""
        return f"""
import asyncio
from framework.graph import GraphSpec, NodeSpec, EdgeSpec, EdgeCondition
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime
from framework.llm.litellm import LiteLLMProvider
from pathlib import Path

async def run_agent(input_data: str):
    # Fallback simulation of a real agent flow
    provider = LiteLLMProvider(model="gemini/gemini-1.5-flash")
    runtime = Runtime(storage_path=Path(f"./logs/{{agent_id}}"))
    executor = GraphExecutor(runtime=runtime, llm=provider)

    async def analyzer(**kwargs): return {{"query": kwargs.get("user_prompt", input_data)}}
    async def researcher(**kwargs): return {{"raw_data": f"Simulated data for {{kwargs.get('query')}}"}}
    async def reporter(**kwargs): return {{"report": f"Generated Report for '{user_prompt}':\\n{{kwargs.get('raw_data')}}"}}

    executor.register_function("analyzer", analyzer)
    executor.register_function("researcher", researcher)
    executor.register_function("reporter", reporter)

    graph = GraphSpec(
        id="{agent_id}",
        goal_id="goal_1",
        entry_node="analyzer",
        terminal_nodes=["reporter"],
        nodes=[
            NodeSpec(id="analyzer", name="Analyzer", node_type="function", function="analyzer", input_keys=["user_prompt"], output_keys=["query"]),
            NodeSpec(id="researcher", name="Researcher", node_type="function", function="researcher", input_keys=["query"], output_keys=["raw_data"]),
            NodeSpec(id="reporter", name="Reporter", node_type="function", function="reporter", input_keys=["raw_data"], output_keys=["report"])
        ],
        edges=[
            EdgeSpec(id="e1", source="analyzer", target="researcher", condition=EdgeCondition.ON_SUCCESS),
            EdgeSpec(id="e2", source="researcher", target="reporter", condition=EdgeCondition.ON_SUCCESS)
        ]
    )

    result = await executor.execute(graph, goal="{user_prompt}", initial_data={{"user_prompt": input_data}})
    return result.get("report", "No report generated.")

if __name__ == "__main__":
    asyncio.run(run_agent("Test Execution"))
"""

