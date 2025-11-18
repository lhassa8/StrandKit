#!/usr/bin/env python3
"""
Example: Strands Agent Using Granular Tools (Advanced)

This example shows using all 58+ granular tools with a Strands agent.
This gives the agent maximum flexibility but can lead to tool confusion.

Use cases for granular tools:
- Specialized agents that need specific tool combinations
- Scripting and automation (direct tool calls)
- Advanced users who want fine-grained control

For general-purpose agents, orchestrator tools are recommended instead.
"""

from strands import Agent
from strandkit.strands import get_all_tools

print("=" * 80)
print("Strands Agent with All Granular Tools (Advanced)")
print("=" * 80)
print()

# Create agent with all 62 tools (4 orchestrators + 58 granular)
all_tools = get_all_tools()

agent = Agent(
    name="aws-power-user",
    tools=all_tools,
    model="anthropic.claude-3-5-sonnet",  # Need more powerful model
    instructions="""You are an advanced AWS infrastructure assistant.

    You have access to 60+ detailed AWS tools covering:
    - CloudWatch (logs, metrics, insights)
    - IAM (roles, policies, security)
    - Cost (spending, waste, optimization)
    - EC2 (instances, performance, scaling)
    - S3 (buckets, storage, access)
    - EBS (volumes, snapshots)

    Use the most appropriate tools to help users with their AWS tasks.
    """
)

print(f"✅ Agent created with {len(agent.tools)} total tools")
print()
print("Tool categories available:")
print("  - 4 orchestrator tools (high-level)")
print("  - 4 CloudWatch tools")
print("  - 11 IAM tools")
print("  - 15 Cost tools")
print("  - 9 EC2 tools")
print("  - 12 S3 tools")
print("  - 6 EBS tools")
print()

# Example 1: Security Audit (agent chooses from many tools)
print("-" * 80)
print("Example 1: Security Audit")
print("-" * 80)
print()
print("User: 'Audit my AWS security and tell me about any risks'")
print()
print("With 60+ tools, the agent might:")
print("  - Use audit_security() orchestrator (best choice)")
print("  - OR call find_overpermissive_roles() + analyze_mfa_compliance() + ...")
print("  - OR call wrong combination of tools")
print()

response = agent.run("Audit my AWS security and tell me about any risks")
print(f"Agent response:\n{response}")
print()

# Example 2: Detailed IAM Analysis
print("-" * 80)
print("Example 2: Detailed IAM Analysis")
print("-" * 80)
print()
print("User: 'Analyze IAM role arn:aws:iam::123456789012:role/MyRole in detail'")
print()
print("Granular tools excel here - agent can use:")
print("  - analyze_role() for detailed role analysis")
print("  - explain_policy() to parse specific policies")
print("  - detect_privilege_escalation_paths() for security")
print()

response = agent.run(
    "Analyze IAM role arn:aws:iam::123456789012:role/MyRole in detail"
)
print(f"Agent response:\n{response}")
print()

print("=" * 80)
print("Summary")
print("=" * 80)
print()
print("Granular Tools:")
print("  ✅ Maximum flexibility and control")
print("  ✅ Best for specialized analysis")
print("  ⚠️  60+ tools can confuse general agents")
print("  ⚠️  Agent might pick wrong tools")
print("  ⚠️  Requires more powerful (expensive) model")
print()
print("Recommended for:")
print("  - Specialized agents (security-only, cost-only)")
print("  - Advanced users who need specific tools")
print("  - Scripting and automation (direct calls)")
print()
print("For general agents, use orchestrator tools instead!")
print()
