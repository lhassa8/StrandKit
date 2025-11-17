#!/usr/bin/env python3
"""
StrandKit v2.0 + AWS Strands Agents Integration Examples

This file demonstrates all the ways to integrate StrandKit's 60 AWS tools
with the official AWS Strands Agents framework.

Requirements:
    pip install strands-agents strandkit boto3

Setup:
    - Configure AWS credentials (AWS CLI or environment variables)
    - Set ANTHROPIC_API_KEY if using Claude models
"""

from strands import Agent


# ============================================================================
# Example 1: All Tools (Complete AWS Agent)
# ============================================================================

def example_all_tools():
    """Create agent with all 60 StrandKit tools."""
    from strandkit.strands import get_all_tools

    print("=" * 70)
    print("Example 1: Agent with All 60 Tools")
    print("=" * 70)

    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_all_tools(),
        system_prompt="You are an AWS infrastructure expert"
    )

    # Test query
    response = agent("List all available tool categories")
    print(f"\nAgent response:\n{response}\n")


# ============================================================================
# Example 2: ToolProvider (Lazy Loading)
# ============================================================================

def example_tool_provider():
    """Use StrandKitToolProvider for lazy-loading tools."""
    from strandkit.strands import StrandKitToolProvider

    print("=" * 70)
    print("Example 2: Using StrandKitToolProvider")
    print("=" * 70)

    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=[StrandKitToolProvider()],
        system_prompt="You are an AWS cost optimization specialist"
    )

    # Test query
    response = agent("What tools do you have for analyzing AWS costs?")
    print(f"\nAgent response:\n{response}\n")


# ============================================================================
# Example 3: Category-Based Tools (Specialized Agents)
# ============================================================================

def example_security_agent():
    """Create specialized security auditing agent."""
    from strandkit.strands import get_tools_by_category

    print("=" * 70)
    print("Example 3: Security Auditing Agent")
    print("=" * 70)

    agent = Agent(
        model="anthropic.claude-3-5-sonnet",
        tools=(
            get_tools_by_category('iam') +
            get_tools_by_category('iam_security') +
            get_tools_by_category('ec2')
        ),
        system_prompt="""You are a security auditor specializing in AWS.
        Focus on IAM roles, permissions, and security group configurations.
        Always explain security risks and provide remediation steps."""
    )

    # Test query
    response = agent("Check for security issues in my AWS account")
    print(f"\nAgent response:\n{response}\n")


def example_cost_agent():
    """Create specialized cost optimization agent."""
    from strandkit.strands import get_tools_by_category

    print("=" * 70)
    print("Example 4: Cost Optimization Agent")
    print("=" * 70)

    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=(
            get_tools_by_category('cost') +
            get_tools_by_category('cost_analytics') +
            get_tools_by_category('cost_waste')
        ),
        system_prompt="""You are a cloud cost optimization expert.
        Analyze AWS spending, identify waste, and recommend savings opportunities.
        Always provide specific dollar amounts and ROI calculations."""
    )

    # Test query
    response = agent("Find ways to reduce my AWS costs")
    print(f"\nAgent response:\n{response}\n")


def example_debugger_agent():
    """Create specialized debugging agent."""
    from strandkit.strands import get_tools_by_category

    print("=" * 70)
    print("Example 5: Infrastructure Debugging Agent")
    print("=" * 70)

    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=(
            get_tools_by_category('cloudwatch') +
            get_tools_by_category('ec2') +
            get_tools_by_category('ec2_advanced')
        ),
        system_prompt="""You are an infrastructure debugging expert.
        Use CloudWatch logs and metrics to diagnose issues.
        Provide step-by-step troubleshooting guidance."""
    )

    # Test query
    response = agent("How would you debug a slow Lambda function?")
    print(f"\nAgent response:\n{response}\n")


# ============================================================================
# Example 6: Category Provider (Alternative Approach)
# ============================================================================

def example_category_provider():
    """Use StrandKitCategoryProvider for category-based tools."""
    from strandkit.strands import StrandKitCategoryProvider

    print("=" * 70)
    print("Example 6: Using StrandKitCategoryProvider")
    print("=" * 70)

    # Create S3 specialist agent
    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=[StrandKitCategoryProvider(['s3', 's3_advanced'])],
        system_prompt="You are an S3 storage optimization expert"
    )

    # Test query
    response = agent("What S3 optimization tools do you have?")
    print(f"\nAgent response:\n{response}\n")


# ============================================================================
# Example 7: Multi-Agent System (Agent Swarm)
# ============================================================================

def example_multi_agent():
    """Create multiple specialized agents working together."""
    from strandkit.strands import get_tools_by_category

    print("=" * 70)
    print("Example 7: Multi-Agent System")
    print("=" * 70)

    # Security agent
    security_agent = Agent(
        name="security-auditor",
        model="anthropic.claude-3-5-haiku",
        tools=get_tools_by_category('iam') + get_tools_by_category('iam_security'),
        system_prompt="You are a security auditor. Focus on IAM and access control."
    )

    # Cost agent
    cost_agent = Agent(
        name="cost-optimizer",
        model="anthropic.claude-3-5-haiku",
        tools=get_tools_by_category('cost') + get_tools_by_category('cost_waste'),
        system_prompt="You are a cost optimizer. Focus on reducing AWS spend."
    )

    # Each agent can work independently
    print("\n[Security Agent]")
    sec_response = security_agent("Summarize your capabilities")
    print(sec_response)

    print("\n[Cost Agent]")
    cost_response = cost_agent("Summarize your capabilities")
    print(cost_response)


# ============================================================================
# Example 8: Standalone Tool Usage (No Agent)
# ============================================================================

def example_standalone():
    """Use StrandKit tools directly without Strands agent."""
    from strandkit import find_overpermissive_roles, find_zombie_resources

    print("=" * 70)
    print("Example 8: Standalone Tool Usage (No Agent)")
    print("=" * 70)

    print("\nCalling find_overpermissive_roles() directly...")
    try:
        result = find_overpermissive_roles()
        print(f"Found {result['summary']['total_roles']} IAM roles")
        print(f"High risk: {result['summary']['high_risk']}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nCalling find_zombie_resources() directly...")
    try:
        result = find_zombie_resources()
        print(f"Total waste: ${result['total_monthly_waste']:.2f}/month")
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example 9: List Available Categories
# ============================================================================

def example_list_categories():
    """List all available tool categories."""
    from strandkit.strands import list_tool_categories, get_tools_by_category

    print("=" * 70)
    print("Example 9: Available Tool Categories")
    print("=" * 70)

    categories = list_tool_categories()

    print(f"\nStrandKit has {len(categories)} tool categories:\n")
    for category in categories:
        tools = get_tools_by_category(category)
        print(f"  - {category}: {len(tools)} tools")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("StrandKit v2.0 + AWS Strands Agents Integration Examples")
    print("=" * 70 + "\n")

    # Run examples (comment out as needed)
    try:
        # Basic examples
        example_all_tools()
        example_tool_provider()

        # Specialized agents
        example_security_agent()
        example_cost_agent()
        example_debugger_agent()

        # Advanced patterns
        example_category_provider()
        example_multi_agent()

        # Standalone usage
        example_standalone()

        # Utility
        example_list_categories()

    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("\nInstall required packages:")
        print("  pip install strands-agents strandkit boto3")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  - AWS credentials are configured")
        print("  - ANTHROPIC_API_KEY is set (for Claude models)")


if __name__ == '__main__':
    main()
