"""
Core modules for StrandKit.

This package contains the foundational classes and utilities:
- base_agent: Base class for all StrandKit agents
- base_tool: Base class for AWS tools
- aws_client: Boto3 wrapper with credential management
- schema: JSON schema definitions for tools
"""

from strandkit.core.base_agent import BaseAgent
from strandkit.core.aws_client import AWSClient
from strandkit.core.schema import ToolSchema

__all__ = ["BaseAgent", "AWSClient", "ToolSchema"]
