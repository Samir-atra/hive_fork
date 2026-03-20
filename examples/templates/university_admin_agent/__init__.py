"""
University Admin Navigation Agent.

An autonomous administrative navigation agent for universities to help students
and staff locate forms, jobs, processes, and resources across institutional systems.
"""

from .agent import UniversityAdminAgent, default_agent
from .config import metadata

__all__ = ["UniversityAdminAgent", "default_agent", "metadata"]
