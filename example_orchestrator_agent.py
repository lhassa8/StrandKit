#!/usr/bin/env python3
"""
Example: Strands Agent Using Orchestrator Tools (Recommended)

This example shows the recommended way to build a Strands agent - using
4 high-level orchestrator tools that are clear and task-focused.

Benefits:
- Agent only sees 4 tools (not confused by 60+ options)
- Tools aligned with what agents actually need to do
- Each orchestrator internally uses multiple granular tools
- Scales well as StrandKit grows to 100+ tools
"""

from strands import Agent
from strandkit.strands import get_tools_by_category

print("=" * 80)
print("Strands Agent with Orchestrator Tools (Recommended)")
print("=" * 80)
print()

# Create agent with just 4 orchestrator tools
agent = Agent(
    name="aws-assistant",
    tools=get_tools_by_category('orchestrators'),
    model="anthropic.claude-3-5-haiku",
    instructions="""You are an AWS infrastructure assistant.

    You have access to 4 powerful tools:
    - audit_security: Check IAM, S3, and EC2 security
    - optimize_costs: Find cost savings opportunities
    - diagnose_issue: Troubleshoot Lambda, EC2, S3 issues
    - get_aws_overview: Get account summary

    Use these tools to help users manage their AWS infrastructure.
    """
)

print(f"✅ Agent created with {len(agent.tools)} orchestrator tools")
print()
print("Tools available to agent:")
for i, tool in enumerate(agent.tools, 1):
    print(f"  {i}. {tool.__name__}()")
print()

# Example 1: Security Audit
print("-" * 80)
print("Example 1: Security Audit")
print("-" * 80)
print()
print("User: 'Audit my AWS security and tell me about any risks'")
print()

response = agent.run("Audit my AWS security and tell me about any risks")
print(f"Agent response:\n{response}")
print()

# Example 2: Cost Optimization
print("-" * 80)
print("Example 2: Cost Optimization")
print("-" * 80)
print()
print("User: 'Find ways to reduce my AWS bill'")
print()

response = agent.run("Find ways to reduce my AWS bill")
print(f"Agent response:\n{response}")
print()

# Example 3: Account Overview
print("-" * 80)
print("Example 3: Account Overview")
print("-" * 80)
print()
print("User: 'Give me an overview of my AWS account'")
print()

response = agent.run("Give me an overview of my AWS account")
print(f"Agent response:\n{response}")
print()

print("=" * 80)
print("Summary")
print("=" * 80)
print()
print("Benefits of Orchestrator Tools:")
print("  ✅ Agent only sees 4 clear tools (not confused)")
print("  ✅ Tools match what agents need to do")
print("  ✅ Each tool orchestrates multiple AWS checks")
print("  ✅ Scales to 100+ tools without agent confusion")
print()
print("Recommended for: General-purpose AWS agents")
print()
