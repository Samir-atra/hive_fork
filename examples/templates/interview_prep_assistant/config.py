"""Runtime configuration for Interview Preparation Assistant Agent."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Interview Prep Assistant"
    version: str = "1.0.0"
    description: str = (
        "Detect interview-related emails, extract key details (role, company, date), "
        "generate interview questions and preparation tips, and provide ATS-based "
        "resume optimization suggestions to help you prepare efficiently."
    )
    intro_message: str = (
        "Hi! I'm your Interview Preparation Assistant. Share an interview invitation "
        "email with me, and I'll help you prepare by extracting key details, generating "
        "relevant interview questions, providing preparation tips, and suggesting "
        "resume optimizations. Ready to get started?"
    )


metadata = AgentMetadata()
