"""
Strands Integration for StrandKit v2.0.

This module provides integration with AWS Strands Agents framework,
allowing StrandKit's 60 AWS tools to be used with Strands AI agents.

Usage with AWS Strands Agents (Recommended):
    from strands import Agent
    from strandkit.strands import get_all_tools

    # Create agent with all 60 tools
    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_all_tools()
    )

    # Or use ToolProvider (lazy-loading)
    from strandkit.strands import StrandKitToolProvider
    agent = Agent(tools=[StrandKitToolProvider()])

    # Or by category
    from strandkit.strands import get_tools_by_category
    agent = Agent(tools=(
        get_tools_by_category('iam') +
        get_tools_by_category('cost')
    ))

    # Or category provider
    from strandkit.strands import StrandKitCategoryProvider
    agent = Agent(tools=[
        StrandKitCategoryProvider(['iam', 'cost', 'ec2'])
    ])
"""

from strandkit.strands.registry import (
    get_all_tools,
    get_tools_by_category,
    list_tool_categories
)

from strandkit.strands.provider import (
    StrandKitToolProvider,  # Deprecated: returns list of tools
    StrandKitCategoryProvider  # Deprecated: returns list of tools
)

__all__ = [
    # Registry functions (recommended)
    'get_all_tools',
    'get_tools_by_category',
    'list_tool_categories',
    # Deprecated compatibility functions
    'StrandKitToolProvider',
    'StrandKitCategoryProvider',
]
