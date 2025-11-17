"""
StrandKit compatibility module for AWS Strands Agents.

This module provides backward compatibility stubs. The ToolProvider pattern
is not needed with the current Strands API. Use get_all_tools() or
get_tools_by_category() from the registry module instead.

Example:
    from strands import Agent
    from strandkit.strands import get_all_tools

    # Create agent with all 60 StrandKit tools
    agent = Agent(tools=get_all_tools())

    # Or with specific categories
    from strandkit.strands import get_tools_by_category

    agent = Agent(tools=(
        get_tools_by_category('iam') +
        get_tools_by_category('cost')
    ))
"""

from typing import List, Any

# Deprecated: ToolProvider classes removed in favor of direct function lists
# Use get_all_tools() or get_tools_by_category() instead

def StrandKitToolProvider():
    """
    Deprecated: Use get_all_tools() instead.

    This function is provided for backward compatibility only.

    Example:
        from strandkit.strands import get_all_tools
        tools = get_all_tools()
    """
    from strandkit.strands.registry import get_all_tools
    return get_all_tools()


def StrandKitCategoryProvider(categories: List[str]):
    """
    Deprecated: Use get_tools_by_category() instead.

    This function is provided for backward compatibility only.

    Args:
        categories: List of category names

    Example:
        from strandkit.strands import get_tools_by_category
        tools = (
            get_tools_by_category('iam') +
            get_tools_by_category('cost')
        )
    """
    from strandkit.strands.registry import get_tools_by_category

    tools = []
    for category in categories:
        tools.extend(get_tools_by_category(category))
    return tools
