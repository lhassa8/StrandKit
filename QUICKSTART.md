# StrandKit Quick Start Guide

**Version 2.0.0** - AWS Companion SDK for Strands Agents

StrandKit provides 60 AWS tools designed to work seamlessly with [AWS Strands Agents](https://strandsagents.com/). Build powerful AI agents that can monitor, analyze, and optimize your AWS infrastructure.

## Installation

```bash
pip install strands-agents strandkit boto3
```

Or for development:

```bash
git clone https://github.com/yourusername/StrandKit.git
cd StrandKit
pip install -e .
```

## Prerequisites

1. **AWS Credentials**
   ```bash
   aws configure
   ```

2. **Anthropic API Key** (for Claude models)
   ```bash
   export ANTHROPIC_API_KEY='your-key-here'
   ```

3. **Python 3.8+**

## What's Included

StrandKit provides **60 tools** across **12 categories**:

| Category | Tools | Purpose |
|----------|-------|---------|
| **CloudWatch** | 4 | Logs, metrics, insights queries |
| **CloudFormation** | 1 | Changeset analysis |
| **IAM** | 3 | Role/policy analysis |
| **IAM Security** | 8 | Security auditing, compliance |
| **Cost** | 4 | Usage, forecasting, anomalies |
| **Cost Analytics** | 6 | Budgets, RI analysis, optimization |
| **Cost Waste** | 5 | Zombie resources, idle detection |
| **EC2** | 5 | Instance analysis, inventory |
| **EC2 Advanced** | 4 | Performance, scaling, spot |
| **S3** | 5 | Bucket analysis, security |
| **S3 Advanced** | 7 | Storage optimization, lifecycle |
| **EBS** | 6 | Volume optimization, encryption |

See [TOOLS.md](TOOLS.md) for complete API reference.

---

## Three Ways to Use StrandKit

### 1. With Strands Agents (Recommended)

Use all 60 tools with AWS Strands Agents framework:

```python
from strands import Agent
from strandkit.strands import get_all_tools

# Create agent with all 60 AWS tools
agent = Agent(
    model="anthropic.claude-3-5-haiku",
    tools=get_all_tools(),
    system_prompt="You are an AWS infrastructure expert"
)

# Ask the agent anything about your AWS account
response = agent("Find security issues in my IAM roles")
print(response)
```

### 2. Specialized Agents (Category-Based)

Create focused agents with specific tool categories:

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Security auditing agent
security_agent = Agent(
    model="anthropic.claude-3-5-sonnet",
    tools=(
        get_tools_by_category('iam') +
        get_tools_by_category('iam_security') +
        get_tools_by_category('ec2')
    ),
    system_prompt="""You are a security auditor specializing in AWS.
    Focus on IAM roles, permissions, and security group configurations."""
)

response = security_agent("Audit my AWS account for security risks")
```

### 3. Standalone Tools (No Agent)

Use tools directly in your Python scripts:

```python
from strandkit import find_overpermissive_roles, get_cost_by_service

# IAM security scan
roles = find_overpermissive_roles()
print(f"Found {roles['summary']['high']} high-risk roles")

# Cost analysis
costs = get_cost_by_service(days_back=30)
print(f"Total spend: ${costs['total_cost']:.2f}")
```

---

## Quick Examples

### Example 1: Cost Optimization Agent

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

cost_agent = Agent(
    model="anthropic.claude-3-5-haiku",
    tools=(
        get_tools_by_category('cost') +
        get_tools_by_category('cost_analytics') +
        get_tools_by_category('cost_waste')
    ),
    system_prompt="You are a cloud cost optimization expert."
)

# Agent uses 15 cost-related tools to analyze your spending
response = cost_agent("Find ways to reduce my AWS costs")
print(response)
```

### Example 2: Security Auditor Agent

```python
from strands import Agent
from strandkit.strands import StrandKitCategoryProvider

security_agent = Agent(
    model="anthropic.claude-3-5-sonnet",
    tools=[StrandKitCategoryProvider(['iam', 'iam_security', 'ec2'])],
    system_prompt="You are a security auditor. Find and explain security risks."
)

response = security_agent("Check for overpermissive IAM roles and security groups")
print(response)
```

### Example 3: Infrastructure Debugger

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

debug_agent = Agent(
    model="anthropic.claude-3-5-haiku",
    tools=(
        get_tools_by_category('cloudwatch') +
        get_tools_by_category('ec2')
    ),
    system_prompt="You are an infrastructure debugging expert."
)

response = debug_agent("My Lambda function 'api-handler' is throwing errors. Debug it.")
print(response)
```

### Example 4: Multi-Agent System

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create specialized agents
security = Agent(
    name="security-auditor",
    model="anthropic.claude-3-5-haiku",
    tools=get_tools_by_category('iam') + get_tools_by_category('iam_security')
)

cost = Agent(
    name="cost-optimizer",
    model="anthropic.claude-3-5-haiku",
    tools=get_tools_by_category('cost') + get_tools_by_category('cost_waste')
)

# Each agent works independently
sec_report = security("Audit IAM roles")
cost_report = cost("Find waste")
```

---

## Standalone Usage (No Strands)

You can use StrandKit tools directly without Strands:

```python
from strandkit import (
    find_overpermissive_roles,
    get_cost_by_service,
    analyze_ec2_instance,
    find_zombie_resources
)

# IAM security scan
print("Scanning IAM roles...")
roles = find_overpermissive_roles()
print(f"  High risk: {roles['summary']['high']}")
print(f"  Medium risk: {roles['summary']['medium']}")

# Cost analysis
print("\nAnalyzing costs...")
costs = get_cost_by_service(days_back=30, top_n=5)
for svc in costs['services']:
    print(f"  {svc['service']}: ${svc['cost']:.2f}")

# EC2 instance analysis
print("\nAnalyzing instance...")
analysis = analyze_ec2_instance("i-1234567890abcdef0")
print(f"  Monthly cost: ${analysis['cost_estimate']['monthly_cost']:.2f}")
print(f"  CPU avg: {analysis['metrics']['cpu_utilization']['average']:.1f}%")

# Find waste
print("\nFinding zombie resources...")
zombies = find_zombie_resources()
print(f"  Potential savings: ${zombies['total_monthly_waste']:.2f}/month")
```

---

## Custom AWS Profiles & Regions

```python
from strandkit.core.aws_client import AWSClient
from strandkit import get_cost_by_service

# Create client for specific profile/region
aws = AWSClient(profile="production", region="us-west-2")

# Pass to any tool
costs = get_cost_by_service(days_back=30, aws_client=aws)
```

---

## Integration Patterns

### ToolProvider (Lazy Loading)

Load tools only when needed:

```python
from strands import Agent
from strandkit.strands import StrandKitToolProvider

agent = Agent(
    tools=[StrandKitToolProvider()],  # Loads all 60 tools lazily
    model="anthropic.claude-3-5-haiku"
)
```

### Category Provider

Load specific categories:

```python
from strandkit.strands import StrandKitCategoryProvider

agent = Agent(
    tools=[StrandKitCategoryProvider(['s3', 's3_advanced', 'ebs'])],
    system_prompt="You are an S3 and EBS storage expert"
)
```

### List Available Categories

```python
from strandkit.strands import list_tool_categories, get_tools_by_category

categories = list_tool_categories()
print(f"Available categories: {', '.join(categories)}")

# See how many tools per category
for cat in categories:
    tools = get_tools_by_category(cat)
    print(f"  {cat}: {len(tools)} tools")
```

---

## Real-World Use Cases

### 1. Daily Security Check Script

```python
#!/usr/bin/env python3
from strandkit import find_overpermissive_roles, find_overpermissive_security_groups

# Scan IAM
iam_scan = find_overpermissive_roles()
critical_iam = iam_scan['summary']['critical']

# Scan security groups
sg_scan = find_overpermissive_security_groups()
critical_sg = sg_scan['summary']['critical']

if critical_iam > 0 or critical_sg > 0:
    print(f"⚠️ CRITICAL: {critical_iam} IAM roles, {critical_sg} security groups")
    exit(1)

print("✅ Security check passed")
```

### 2. Cost Alert Monitor

```python
from strandkit import detect_cost_anomalies

anomalies = detect_cost_anomalies(days_back=7, threshold_percentage=25)

if anomalies['total_anomalies'] > 0:
    for a in anomalies['anomalies']:
        if a['severity'] == 'high':
            print(f"🔴 Cost spike on {a['date']}: ${a['cost']:.2f}")
            # Send alert to Slack/email
```

### 3. Resource Cleanup

```python
from strandkit import find_zombie_resources

zombies = find_zombie_resources()

print(f"Potential savings: ${zombies['total_monthly_waste']:.2f}/month")
print(f"  Unattached volumes: ${zombies['breakdown']['unattached_volumes']:.2f}")
print(f"  Old snapshots: ${zombies['breakdown']['old_snapshots']:.2f}")
print(f"  Unused IPs: ${zombies['breakdown']['unused_elastic_ips']:.2f}")
```

---

## Error Handling

All tools return structured JSON, even on errors:

```python
from strandkit import analyze_ec2_instance

result = analyze_ec2_instance("i-nonexistent")

if 'error' in result:
    print(f"Error: {result['error']}")
elif 'warning' in result:
    print(f"Warning: {result['warning']}")
else:
    print(f"Success: {result['instance_details']}")
```

---

## Troubleshooting

**ImportError: No module named 'strandkit'**
```bash
pip install -e .
# or
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**NoCredentialsError**
```bash
aws configure
# or
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

**ResourceNotFound**
- Verify resource exists in correct region
- Check AWS credentials have necessary permissions
- Confirm resource name/ID is correct

---

## Next Steps

1. **Try the examples:**
   ```bash
   python examples/strands_integration.py
   ```

2. **Read the docs:**
   - [TOOLS.md](TOOLS.md) - Complete API reference for all 60 tools
   - [CHANGELOG.md](CHANGELOG.md) - Version history and migration guides
   - [AWS Strands Docs](https://strandsagents.com/) - Official Strands framework docs

3. **Build your own agent:**
   - Choose relevant tool categories
   - Write a focused system prompt
   - Test with real AWS resources

---

## Examples in This Repo

- `examples/strands_integration.py` - 9 integration patterns
- `examples/basic_usage.py` - Standalone tool usage
- `examples/test_imports.py` - Verify installation

---

## What's New in v2.0.0

- ✅ Full AWS Strands Agents integration
- ✅ 60 tools (up from 14 in v0.2.0)
- ✅ 12 categories (CloudWatch, IAM, Cost, EC2, S3, EBS, etc.)
- ✅ `@tool` decorator on all functions
- ✅ ToolProvider pattern for lazy loading
- ✅ Category-based tool selection
- ✅ 100% backward compatible standalone usage

See [CHANGELOG.md](CHANGELOG.md) for migration guide from v1.0.0.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/StrandKit/issues)
- **Strands Docs:** [strandsagents.com](https://strandsagents.com/)
- **AWS Docs:** [AWS Documentation](https://docs.aws.amazon.com/)

---

**StrandKit v2.0.0** - Companion SDK for AWS Strands Agents
