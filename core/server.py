
import os
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv

from framework.graph import Goal, GraphSpec, NodeSpec, EdgeSpec, EdgeCondition
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime
from framework.llm.litellm import LiteLLMProvider
from architect_agent import ArchitectAgent

# 1. Load Environment
load_dotenv()

app = FastAPI(title="Hive Agentic API")

# Enable CORS for the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global stores
activity_log = []
evolution_log = [
    {"stage": "Initial Prompt", "action": "Analyzing intent", "timestamp": "0s"},
    {"stage": "Architecture", "action": "Graph optimization", "timestamp": "1.2s"},
    {"stage": "Pruning", "action": "Removing redundant nodes", "timestamp": "2.1s"}
]
cinema_data = {
    "artifacts": [],
    "metrics": {"total_nodes": 0, "latency_avg": 0, "token_count": 0}
}
session_stats = {"success": 0, "failure": 0, "total": 0}

class AgentRequest(BaseModel):
    prompt: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/activity")
def get_activity():
    return activity_log

@app.get("/evolution")
def get_evolution():
    return evolution_log

@app.get("/cinema")
def get_cinema():
    return cinema_data

@app.get("/analytics")
def get_analytics():
    return session_stats

@app.get("/docs_content")
def get_docs():
    docs_path = Path("../HIVE_OVERVIEW.md")
    if docs_path.exists():
        return {"content": docs_path.read_text()}
    return {"content": "# Hive Documentation\nDocumentation not found."}

async def run_discovery_agent(user_prompt: str):
    global activity_log, cinema_data, evolution_log
    activity_log = [{"text": "Initializing Hive Engine...", "icon": "Cpu", "success": True}]
    evolution_log = [{"stage": "Start", "action": "Initializing engine", "timestamp": "0s"}]

    try:
        # 1. Initialize Architect with LLM Provider
        gemini = LiteLLMProvider(model="gemini/gemini-2.5-flash")
        architect = ArchitectAgent(provider=gemini, exports_dir="../exports")
        
        # 2. Simulate/Run Discovery Graph (keep existing logic for UI feedback)
        runtime = Runtime(storage_path=Path("./agent_logs/api_run"))
        executor = GraphExecutor(runtime=runtime, llm=gemini)

        activity_log.append({"text": f"Goal Set: {user_prompt[:30]}...", "icon": "Target", "success": True})
        evolution_log.append({"stage": "Goal Parsing", "action": "Mapping prompt to architecture", "timestamp": "0.5s"})

        # Define a basic discovery agent for verifying the framework
        def analyze(**kwargs): return kwargs.get("query") or kwargs.get("user_prompt") or "Unknown Query"
        def research(**kwargs): return f"Found simulated insights for: {kwargs.get('query') or kwargs.get('intent')}"
        def summarize(**kwargs): return f"Executive Summary: {kwargs.get('raw_data') or 'No Data'}"

        executor.register_function("n1", analyze)
        executor.register_function("n2", research)
        executor.register_function("n3", summarize)

        graph = GraphSpec(
            id="discovery-verify",
            goal_id="verify",
            entry_node="n1",
            terminal_nodes=["n3"],
            nodes=[
                NodeSpec(id="n1", name="Analyzer", description="Analyzes user intent", node_type="function", function="analyze", input_keys=["user_prompt"], output_keys=["query"]),
                NodeSpec(id="n2", name="Researcher", description="Researches discovery insights", node_type="function", function="research", input_keys=["query"], output_keys=["raw_data"]),
                NodeSpec(id="n3", name="Reporter", description="Generates technical summary", node_type="function", function="summarize", input_keys=["raw_data"], output_keys=["report"])
            ],
            edges=[
                EdgeSpec(id="e1", source="n1", target="n2", condition=EdgeCondition.ON_SUCCESS),
                EdgeSpec(id="e2", source="n2", target="n3", condition=EdgeCondition.ON_SUCCESS)
            ]
        )

        activity_log.append({"text": "Executing Node: Analyzer", "icon": "Loader2", "success": True})
        evolution_log.append({"stage": "Node Construction", "action": "Instantiating Analyzer", "timestamp": "1.2s"})
        await asyncio.sleep(1)
        
        # 3. Generate REAL Agent Files
        activity_log.append({"text": f"Architecting Agent Codebase ([{gemini.model}])...", "icon": "Zap", "success": True})
        generated_agent = architect.generate_agent(user_prompt)
        
        activity_log.append({"text": "Executing Node: Researcher", "icon": "Loader2", "success": True})
        evolution_log.append({"stage": "Code Generation", "action": f"Created {generated_agent['agent_id']}", "timestamp": "2.1s"})
        await asyncio.sleep(1)

        result = await executor.execute(graph, Goal(id="v", name="V", description="V"), {"user_prompt": user_prompt})

        if result.success:
            report = result.output.get("report", "No report generated")
            final_msg = f"Workflow Complete! Agent generated at: {generated_agent['path']}"
            
            activity_log.append({
                "text": final_msg,
                "icon": "CheckCircle",
                "success": True,
                "report": report
            })
            evolution_log.append({"stage": "Complete", "action": "Graph execution finished", "timestamp": f"{result.total_latency_ms/1000}s"})
            
            # Read generated files for display
            agent_code = Path(generated_agent['path']) / "agent.py"
            code_content = agent_code.read_text() if agent_code.exists() else "Error reading code."

            cinema_data = {
                "artifacts": [
                    {"id": "report_1", "type": "markdown", "title": "Discovery Report", "content": report},
                    {"id": "code_1", "type": "python", "title": "Generated Agent Code", "content": code_content}
                ],
                "metrics": {
                    "total_nodes": result.steps_executed,
                    "latency_avg": result.total_latency_ms / (result.steps_executed or 1),
                    "token_count": result.total_tokens
                }
            }
            session_stats["success"] += 1
        else:
            activity_log.append({
                "text": f"Execution Failed: {result.error}",
                "icon": "XCircle",
                "success": False
            })
            session_stats["failure"] += 1
        
        session_stats["total"] += 1
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        activity_log.append({"text": f"System Error: {str(e)}", "icon": "XCircle", "success": False})

@app.post("/generate")
async def generate(req: AgentRequest, background_tasks: BackgroundTasks):
    global activity_log, evolution_log, cinema_data
    # Clear logs immediately so frontend doesn't see stale data
    activity_log = []
    evolution_log = []
    cinema_data = {
        "artifacts": [],
        "metrics": {"total_nodes": 0, "latency_avg": 0, "token_count": 0}
    }
    background_tasks.add_task(run_discovery_agent, req.prompt)
    return {"message": "Agent generation started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
