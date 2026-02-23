"""Runtime configuration for Support Debugger Agent."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Support Debugger Agent"
    version: str = "1.0.0"
    description: str = (
        "An iterative support debugging agent that demonstrates cyclic investigation "
        "workflows. Uses hypothesis-driven reasoning to diagnose issues through evidence "
        "gathering, confidence refinement, and convergence-based termination."
    )
    intro_message: str = (
        "Hi! I'm your support debugging assistant. Describe the issue you're facing "
        "and I'll systematically investigate it by forming hypotheses, gathering "
        "evidence, and narrowing down root causes. What problem would you like me "
        "to help debug?"
    )


metadata = AgentMetadata()
