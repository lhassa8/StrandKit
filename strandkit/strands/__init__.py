"""
Strands Integration for StrandKit.

This module provides AWS Strands agent integration, allowing StrandKit tools
to be used with AI agents that can reason about AWS infrastructure.

Usage:
    # Get all tools for your agent
    from strandkit.strands import get_all_tools
    tools = get_all_tools()

    # Get tools by category
    from strandkit.strands import get_tools_by_category
    iam_tools = get_tools_by_category('iam')

    # Use pre-built agents
    from strandkit.strands.agents import InfraDebuggerAgent
    agent = InfraDebuggerAgent()
    response = agent.run("Why is my Lambda function failing?")
"""

from strandkit.strands.registry import (
    get_all_tools,
    get_tools_by_category,
    get_tool,
    list_tool_categories
)

__all__ = [
    'get_all_tools',
    'get_tools_by_category',
    'get_tool',
    'list_tool_categories'
]
