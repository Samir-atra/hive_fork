"""Runtime configuration for MCP Toolsmith Agent."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "MCP Toolsmith"
    version: str = "1.0.0"
    description: str = (
        "Intelligent MCP server discovery, installation, and configuration agent. "
        "Analyzes your project, discovers relevant MCP servers, generates correct "
        "configuration, collects credentials with human guidance, installs servers "
        "with explicit approval, validates connections end-to-end, and self-heals "
        "when something breaks."
    )
    intro_message: str = (
        "Hi! I'm the MCP Toolsmith. I'll analyze your project, discover relevant "
        "MCP servers, and help you set them up with proper configuration and credentials. "
        "What project path should I analyze?"
    )


metadata = AgentMetadata()
