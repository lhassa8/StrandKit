# StrandKit

<div align="center">

**Companion SDK for AWS Strands Agents**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![AWS](https://img.shields.io/badge/AWS-Ready-orange.svg)](https://aws.amazon.com/)

[Features](#features) •
[Installation](#installation) •
[Quick Start](#quick-start) •
[Documentation](#documentation) •
[Examples](#examples) •
[Contributing](#contributing)

</div>

---

## Overview

StrandKit is a companion SDK for **[AWS Strands Agents](https://strandsagents.com/)** that provides **78 production-ready AWS tools** for:

- 💰 **Cost optimization** - Find waste, analyze spending, get rightsizing recommendations
- 🔒 **Security auditing** - Scan IAM policies, detect misconfigurations, enforce compliance
- 📊 **Infrastructure monitoring** - Analyze CloudWatch metrics, track performance, debug issues
- ⚡ **Performance tuning** - Identify bottlenecks, optimize auto-scaling, analyze load balancers
- 🤖 **AI/ML operations** - Bedrock model analysis, usage monitoring, cost optimization

**Perfect for AWS Strands Agents:**
- **Orchestrator tools** - 4 high-level tools designed for common agent tasks (security audit, cost optimization, diagnostics)
- **Drop-in ready** - All 78 tools work seamlessly with Strands agents via `get_all_tools()`
- **Auto-generated schemas** - Tool definitions automatically converted to Strands-compatible format
- **Category organization** - Filter by orchestrators, IAM, EC2, S3, Cost, CloudWatch for specialized agents
- **Production-tested** - All tools validated with real AWS accounts, handles edge cases gracefully
- **Actionable insights** - Every tool provides recommendations, not just raw data

**Also works standalone** - Use tools directly without Strands for scripting and automation

## What is AWS Strands Agents?

**[AWS Strands Agents](https://strandsagents.com/)** is an open-source Python SDK from AWS for building production-ready, multi-agent AI systems. It provides:

- 🤖 **Agent orchestration** - Build AI agents that reason, plan, and reflect
- 🔧 **Tool integration** - Python functions, MCP tools, AWS service integrations
- 🤝 **Multi-agent patterns** - Agent swarms, handoffs, and graph-based workflows
- 🏢 **Enterprise features** - Memory, observability, guardrails, PII redaction
- ☁️ **AWS-native** - Deploy to Lambda, EKS, Fargate; use Bedrock models

## Why StrandKit?

**StrandKit supercharges AWS Strands Agents with 78 production-ready AWS tools** (4 orchestrators + 74 granular).

### Strands Gives You the Framework, StrandKit Gives You the Tools

**AWS Strands Agents** provides the agent framework - orchestration, multi-agent patterns, observability, and guardrails. But to build AWS agents, you still need to write all the integration code yourself.

**StrandKit fills that gap** - it's a tool library specifically designed for Strands Agents that handle common AWS operations:

| What You Want Your Agent to Do | Without StrandKit | With StrandKit |
|--------------------------------|-------------------|----------------|
| "Audit my AWS security" | Write 500+ lines to scan IAM, S3, EC2, assess risks, prioritize findings | `audit_security()` - 1 orchestrator tool |
| "Find all cost savings" | Write code to check zombies, idle resources, snapshots, buckets | `optimize_costs()` - 1 orchestrator tool |
| "Debug Lambda errors" | Write code to fetch CloudWatch logs, parse metrics, correlate events | `diagnose_issue(resource_type="lambda")` |
| "Get AWS account overview" | Write code to aggregate costs, security, resources across services | `get_aws_overview()` - 1 orchestrator tool |
| "Find overpermissive IAM roles" (detailed) | Write 150+ lines of boto3 code to scan roles, parse policies | `find_overpermissive_roles()` - 1 granular tool |

### Drop-In Ready for Strands Agents

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create a Strands agent with 4 orchestrator tools (recommended)
agent = Agent(
    name="aws-assistant",
    tools=get_tools_by_category('orchestrators'),
    model="anthropic.claude-haiku-4-5-20251001-v1:0"
)

# Agent can now handle complex AWS tasks with simple tools
response = agent("Audit my AWS account for security risks")
# Agent calls audit_security() which internally uses 5+ security tools

response = agent("Find ways to reduce my AWS bill")
# Agent calls optimize_costs() which checks waste, idle resources, storage
```

### Built For Strands

- ✅ **Orchestrator tools** - 4 high-level tools designed for common agent tasks
- ✅ **@tool decorator** - Every function has Strands `@tool` decorator for instant integration
- ✅ **Auto-schemas** - Tool schemas automatically generated for Strands agents
- ✅ **Category filtering** - Load only the tools you need (orchestrators, IAM, Cost, EC2, S3, RDS, VPC, Bedrock, etc.)
- ✅ **Production-ready** - All 78 tools tested with real AWS accounts
- ✅ **Actionable output** - Every tool returns recommendations, not just raw data
- ✅ **Standalone compatible** - Also works without Strands for scripting

## Three Ways to Use StrandKit

### 1. With AWS Strands Agents (Recommended)

**NEW:** For best results, use **Orchestrator Tools** - high-level tools that solve complete tasks:

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create agent with 4 task-focused orchestrator tools (recommended)
agent = Agent(
    name="aws-assistant",
    tools=get_tools_by_category('orchestrators'),
    model="anthropic.claude-haiku-4-5-20251001-v1:0"
)

# Agent has 4 clear, powerful tools:
response = agent("Audit my AWS security")
# Calls audit_security() which orchestrates 5+ security tools

response = agent("Find cost savings")
# Calls optimize_costs() which checks waste, idle resources, storage
```

**Why Orchestrator Tools?**
- ✅ **Clear purpose** - 4 tools vs 60 reduces agent confusion
- ✅ **Better results** - Designed for what agents actually need to do
- ✅ **Comprehensive** - Each orchestrator uses multiple granular tools
- ✅ **Scales to 100+ tools** - As we add more tools, orchestrators hide complexity

**The 4 Orchestrator Tools:**
1. `audit_security()` - Comprehensive security audit (IAM, S3, EC2)
2. `optimize_costs()` - Find all cost savings opportunities
3. `diagnose_issue()` - Smart troubleshooting for Lambda, EC2, S3
4. `get_aws_overview()` - Dashboard view of entire AWS account

---

**Using all 74 granular tools (advanced):**

Use StrandKit's 74 granular tools when you need fine-grained control:

```python
from strands import Agent
from strandkit.strands import get_all_tools

# Create agent with all granular tools
agent = Agent(
    name="aws-analyst",
    tools=get_all_tools(),  # 74 AWS granular tools ready to use
    model="anthropic.claude-haiku-4-5-20251001-v1:0"
)

# Agent can now use any StrandKit tool
response = agent("Find security risks in my IAM roles")
# Agent automatically calls find_overpermissive_roles() and explains findings
```

**Using ToolProvider (Lazy Loading):**
```python
from strands import Agent
from strandkit.strands import StrandKitToolProvider

# Tools are loaded only when agent needs them
agent = Agent(
    tools=[StrandKitToolProvider()],
    model="anthropic.claude-haiku-4-5-20251001-v1:0"
)
```

**Tool Selection by Category:**
```python
from strandkit.strands import get_tools_by_category

# Build specialized agents with specific tool sets
security_agent = Agent(
    name="security-auditor",
    tools=(get_tools_by_category('iam') +
           get_tools_by_category('iam_security') +
           get_tools_by_category('ec2')),
    model="anthropic.claude-haiku-4-5-20251001-v1:0"
)

cost_agent = Agent(
    name="cost-optimizer",
    tools=(get_tools_by_category('cost') +
           get_tools_by_category('cost_waste')),
    model="anthropic.claude-haiku-4-5-20251001-v1:0"
)
```

### 2. Standalone Tools (No AI)

Use StrandKit tools directly without any agent framework:

**Orchestrator tools (recommended):**
```python
from strandkit import (
    audit_security,
    optimize_costs,
    diagnose_issue,
    get_aws_overview
)

# Complete security audit
security_report = audit_security(
    include_iam=True,
    include_s3=True,
    include_ec2=True
)
print(f"Found {security_report['summary']['total_issues']} issues")

# Find all cost savings
savings = optimize_costs(min_impact=10.0)
print(f"Potential savings: ${savings['summary']['total_monthly_savings']:.2f}/month")

# Get account overview
overview = get_aws_overview()
print(f"Monthly spend: ${overview['costs']['total_monthly_spend']:.2f}")
```

**Granular tools (advanced):**
```python
from strandkit import (
    find_overpermissive_roles,
    find_zombie_resources,
    analyze_ec2_performance,
    get_s3_cost_analysis
)

# Direct function calls
risky_roles = find_overpermissive_roles()
wasted_money = find_zombie_resources()
slow_instances = analyze_ec2_performance("i-1234567890")
s3_costs = get_s3_cost_analysis()
```

### 3. Pre-built StrandKit Agents

StrandKit includes example agents built with Claude API for quick prototyping:

```python
from strandkit import InfraDebuggerAgent

# Quick prototype using Claude directly
agent = InfraDebuggerAgent(api_key="sk-ant-...")
result = agent.run("Why is my Lambda function failing?")
```

**Note**: These are simplified examples. For production, use AWS Strands Agents framework (option 1).

## How StrandKit Extends Strands

| Feature | AWS Strands Agents | StrandKit Adds |
|---------|-------------------|----------------|
| **Agent Framework** | ✅ Multi-agent orchestration | N/A (uses Strands) |
| **AWS Tools** | ❌ You write them | ✅ 60 production-ready tools |
| **Tool Schemas** | ✅ Tool definition format | ✅ Auto-generated for all tools |
| **IAM Security** | ❌ Build yourself | ✅ 11 security audit tools |
| **Cost Optimization** | ❌ Build yourself | ✅ 15 cost analysis tools |
| **EC2 Analysis** | ❌ Build yourself | ✅ 10 compute tools |
| **S3 Management** | ❌ Build yourself | ✅ 12 storage tools |
| **CloudWatch** | ❌ Build yourself | ✅ 4 monitoring tools |

**StrandKit = AWS tools for Strands**

## Requirements

**For AWS Strands Agents Integration:**
- Python 3.8+
- AWS credentials configured
- `pip install strands-agents` ([docs](https://strandsagents.com/latest/))
- `pip install strandkit` (from source currently)

**For Standalone Tools:**
- Python 3.8+
- AWS credentials configured
- `pip install boto3`

**For StrandKit Example Agents:**
- Python 3.8+
- AWS credentials
- Anthropic API key
- `pip install anthropic`

## Features

### AWS Tools (Production Ready ✅)

#### CloudWatch Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`get_lambda_logs`** | Retrieve and parse Lambda CloudWatch logs | ✅ Working |
| **`get_metric`** | Query CloudWatch metrics with statistics | ✅ Working |
| **`get_log_insights`** | Run advanced Logs Insights queries | ✅ Working |
| **`get_recent_errors`** | Find recent errors across log groups | ✅ Working |

#### CloudFormation Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`explain_changeset`** | Analyze changesets with risk assessment | ✅ Working |

#### IAM Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_role`** | Analyze IAM role permissions and security risks | ✅ Working |
| **`explain_policy`** | Explain IAM policies in plain English | ✅ Working |
| **`find_overpermissive_roles`** | Scan all roles for security issues | ✅ Working |

#### IAM Security & Compliance Tools (Prevent Breaches)
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_iam_users`** | User security audit (inactive, MFA, old keys) | ✅ Working |
| **`analyze_access_keys`** | Access key security analysis and rotation | ✅ Working |
| **`analyze_mfa_compliance`** | MFA enforcement and compliance tracking | ✅ Working |
| **`analyze_password_policy`** | Password policy vs CIS Benchmark | ✅ Working |
| **`find_cross_account_access`** | Cross-account trust relationship analysis | ✅ Working |
| **`detect_privilege_escalation_paths`** | Detect privilege escalation vectors | ✅ Working |
| **`analyze_unused_permissions`** | Least privilege - find unused permissions | ✅ Working |
| **`get_iam_credential_report`** | Comprehensive credential audit report | ✅ Working |

#### EBS & Volume Optimization Tools (Reduce Storage Costs)
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_ebs_volumes`** | Volume optimization (GP2→GP3, 20% savings) | ✅ Working |
| **`analyze_ebs_snapshots_lifecycle`** | Snapshot lifecycle and cleanup | ✅ Working |
| **`get_ebs_iops_recommendations`** | IOPS optimization and rightsizing | ✅ Working |
| **`analyze_ebs_encryption`** | Encryption compliance checking | ✅ Working |
| **`find_ebs_volume_anomalies`** | Performance issue detection | ✅ Working |
| **`analyze_ami_usage`** | AMI cleanup and cost reduction | ✅ Working |

#### Cost Explorer Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`get_cost_and_usage`** | Get cost data for any time period | ✅ Working |
| **`get_cost_by_service`** | Break down costs by AWS service | ✅ Working |
| **`detect_cost_anomalies`** | Find unusual spending patterns | ✅ Working |
| **`get_cost_forecast`** | Forecast future AWS costs | ✅ Working |

#### Cost Analytics Tools (High-Value Optimization)
| Tool | Description | Status |
|------|-------------|--------|
| **`get_budget_status`** | Monitor budgets with predictive alerts | ✅ Working |
| **`analyze_reserved_instances`** | RI utilization and coverage analysis | ✅ Working |
| **`analyze_savings_plans`** | Savings Plan utilization and coverage | ✅ Working |
| **`get_rightsizing_recommendations`** | EC2/RDS rightsizing with cost savings | ✅ Working |
| **`analyze_commitment_savings`** | RI/SP purchase recommendations with ROI | ✅ Working |
| **`find_cost_optimization_opportunities`** | Aggregate all optimization opportunities | ✅ Working |

#### Cost Waste Detection Tools (Find Hidden Waste)
| Tool | Description | Status |
|------|-------------|--------|
| **`find_zombie_resources`** | Find forgotten resources (EIPs, volumes, snapshots) | ✅ Working |
| **`analyze_idle_resources`** | Detect idle EC2/RDS instances using metrics | ✅ Working |
| **`analyze_snapshot_waste`** | Identify old and orphaned snapshots | ✅ Working |
| **`analyze_data_transfer_costs`** | Analyze data transfer costs (10-30% of bill) | ✅ Working |
| **`get_cost_allocation_tags`** | Analyze cost allocation tag coverage | ✅ Working |

#### EC2 & Compute Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_ec2_instance`** | Comprehensive instance analysis with metrics | ✅ Working |
| **`get_ec2_inventory`** | List all instances with summary statistics | ✅ Working |
| **`find_unused_resources`** | Find stopped instances, unattached volumes, unused EIPs | ✅ Working |
| **`analyze_security_group`** | Analyze security group rules with risk assessment | ✅ Working |
| **`find_overpermissive_security_groups`** | Scan all security groups for security risks | ✅ Working |

#### S3 & Storage Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_s3_bucket`** | Comprehensive bucket analysis (security, cost, config) | ✅ Working |
| **`find_public_buckets`** | Scan all buckets for public access risks | ✅ Working |
| **`get_s3_cost_analysis`** | Storage cost breakdown and optimization opportunities | ✅ Working |
| **`analyze_bucket_access`** | Access logging and CloudTrail integration status | ✅ Working |
| **`find_unused_buckets`** | Identify empty or rarely used buckets | ✅ Working |

#### S3 Advanced Optimization Tools (30-70% Storage Savings)
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_s3_storage_classes`** | Storage class analysis and transition recommendations | ✅ Working |
| **`analyze_s3_lifecycle_policies`** | Lifecycle policy coverage and optimization | ✅ Working |
| **`find_s3_versioning_waste`** | Identify versioning cost waste | ✅ Working |
| **`find_incomplete_multipart_uploads`** | Find hidden costs from incomplete uploads | ✅ Working |
| **`analyze_s3_replication`** | Replication configuration and costs | ✅ Working |
| **`analyze_s3_request_costs`** | Request-based cost analysis | ✅ Working |
| **`analyze_large_s3_objects`** | Find large objects needing optimization | ✅ Working |

#### RDS & Database Tools (NEW in v2.2.0)
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_rds_instance`** | RDS performance, cost, and configuration analysis | ✅ Working |
| **`find_idle_databases`** | Find underutilized RDS instances wasting money | ✅ Working |
| **`analyze_rds_backups`** | Backup configuration and compliance analysis | ✅ Working |
| **`get_rds_recommendations`** | RDS optimization recommendations (rightsizing, RI) | ✅ Working |
| **`find_rds_security_issues`** | Scan all RDS instances for security issues | ✅ Working |

#### VPC & Networking Tools (NEW in v2.2.0)
| Tool | Description | Status |
|------|-------------|--------|
| **`find_unused_nat_gateways`** | Find NAT Gateways with no traffic ($32/month each) | ✅ Working |
| **`analyze_vpc_configuration`** | VPC configuration analysis (subnets, routes, flow logs) | ✅ Working |
| **`analyze_data_transfer_costs`** | Data transfer cost breakdown (10-30% of bill) | ✅ Working |
| **`analyze_vpc_endpoints`** | VPC endpoint analysis and cost savings | ✅ Working |
| **`find_network_bottlenecks`** | Identify network performance bottlenecks | ✅ Working |

#### Bedrock & AI/ML Tools (NEW in v2.3.0)
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_bedrock_usage`** | Bedrock usage, costs, and model invocation metrics | ✅ Working |
| **`list_available_models`** | List all available foundation models (Claude, Llama, Titan, etc.) | ✅ Working |
| **`get_model_details`** | Get model details (pricing, context limits, capabilities) | ✅ Working |
| **`analyze_model_performance`** | Performance metrics (latency, errors, throttling) | ✅ Working |
| **`compare_models`** | Compare models side-by-side for selection | ✅ Working |
| **`get_model_invocation_logs`** | Recent model invocations for debugging | ✅ Working |

### Strands AI Agents (Powered by Claude)

StrandKit includes AI agents that can reason about your AWS infrastructure and use tools automatically.

| Agent | Description | Status |
|-------|-------------|--------|
| **InfraDebuggerAgent** | Debug AWS infrastructure issues using AI + tools | ✅ Working |
| **SecurityAuditorAgent** | AI-powered security auditing | 📋 Planned |
| **CostOptimizerAgent** | Intelligent cost optimization recommendations | 📋 Planned |

**How Strands Agents Work:**
- You ask a question in natural language
- Claude (AI) reasons about the problem
- Agent automatically calls relevant StrandKit tools
- You get an intelligent answer with evidence

**Example:**
```python
from strandkit import InfraDebuggerAgent

# Create agent (uses Claude via Anthropic API)
agent = InfraDebuggerAgent(region="us-east-1")

# Ask a question - agent will use tools automatically
result = agent.run("Why is my Lambda function failing?")
print(result['answer'])

# Agent might call: get_lambda_logs, get_metric, explain_changeset
# Then synthesize findings into a clear diagnosis
```

**Requirements:** Set `ANTHROPIC_API_KEY` environment variable ([get API key](https://console.anthropic.com/))

## Installation

### From PyPI (Recommended)

```bash
pip install strandkit
```

### From Source (Development)

```bash
git clone https://github.com/lhassa8/StrandKit.git
cd StrandKit
pip install -e .
```

## Quick Start

### Prerequisites

1. **Install AWS Strands Agents**:
   ```bash
   pip install strands-agents
   ```

2. **Install StrandKit**:
   ```bash
   pip install strandkit
   ```

3. **AWS Credentials**: Configure AWS CLI or set environment variables
   ```bash
   aws configure
   ```

### Basic Usage with Strands Agents (Recommended)

**StrandKit is designed to be used with AWS Strands Agents** - the AI agent decides when to call which tools:

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create an agent with orchestrator tools (recommended starting point)
agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=get_tools_by_category('orchestrators')
)

# Ask the agent to perform AWS tasks - it will use tools automatically
response = agent("Find all security issues in my AWS account")
# Agent calls audit_security() which uses 5+ security tools internally

response = agent("What's wasting money in my AWS account?")
# Agent calls optimize_costs() which checks zombies, idle resources, etc.

response = agent("Why is my Lambda function failing?")
# Agent calls diagnose_issue() with resource_type="lambda"

print(response)
```

**For more granular control, use specific tool categories:**

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Security-focused agent
security_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=(
        get_tools_by_category('iam') +
        get_tools_by_category('iam_security') +
        get_tools_by_category('ec2')
    )
)

# Agent can now call IAM and EC2 security tools as needed
response = security_agent("Find overpermissive IAM roles and security groups")
# Agent automatically calls find_overpermissive_roles() and
# find_overpermissive_security_groups(), then explains findings

# Cost optimization agent
cost_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",  # Haiku for cost-sensitive workloads
    tools=(
        get_tools_by_category('cost') +
        get_tools_by_category('cost_waste')
    )
)

response = cost_agent("Show me my top AWS costs and find waste")
# Agent calls get_cost_by_service() and find_zombie_resources()
```

### Real-World Examples with Strands Agents

#### Debug Lambda Errors with AI Agent

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create agent with debugging tools
debug_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=get_tools_by_category('cloudwatch')
)

# Natural language debugging - agent figures out what to do
response = debug_agent("""
My Lambda function 'my-api-function' is throwing errors.
Can you check the error rate and show me recent error messages?
""")

print(response)
# Agent automatically:
# 1. Calls get_metric() to check error rate
# 2. Calls get_lambda_logs() with ERROR filter if errors found
# 3. Analyzes and explains the errors in plain English
```

#### Security Audit with AI Agent

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create security agent with IAM and EC2 tools
security_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=(
        get_tools_by_category('iam') +
        get_tools_by_category('iam_security') +
        get_tools_by_category('ec2')
    )
)

# Ask for security audit - agent decides what to check
response = security_agent("""
Perform a security audit of my AWS account.
Check for overpermissive IAM roles and security groups.
""")

print(response)
# Agent automatically:
# 1. Calls find_overpermissive_roles()
# 2. Calls find_overpermissive_security_groups()
# 3. Prioritizes findings by risk level
# 4. Provides remediation recommendations
```

#### Cost Optimization with AI Agent

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create cost optimization agent
cost_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=(
        get_tools_by_category('cost') +
        get_tools_by_category('cost_waste') +
        get_tools_by_category('ec2')
    )
)

# Ask about costs - agent figures out what to analyze
response = cost_agent("""
I want to reduce my AWS bill. Show me where I'm spending money
and find opportunities to save.
""")

print(response)
# Agent automatically:
# 1. Calls get_cost_by_service() to show spending breakdown
# 2. Calls find_zombie_resources() to find waste
# 3. Calls find_unused_resources() for idle EC2 instances
# 4. Calculates total potential savings
# 5. Prioritizes recommendations by impact
```

#### IAM Security Compliance Audit with AI Agent

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create IAM security agent
iam_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=get_tools_by_category('iam_security')
)

# Ask for comprehensive IAM audit
response = iam_agent("""
Perform a comprehensive IAM security audit.
Check for inactive users, MFA compliance, password policy,
and privilege escalation risks.
""")

print(response)
# Agent automatically:
# 1. Calls analyze_iam_users() to check inactive users and keys
# 2. Calls analyze_mfa_compliance() to check MFA status
# 3. Calls analyze_password_policy() to validate policy
# 4. Calls detect_privilege_escalation_paths() to find risks
# 5. Prioritizes findings and provides remediation steps
```

#### Multi-Service Infrastructure Analysis with AI Agent

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create comprehensive infrastructure agent
infra_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=(
        get_tools_by_category('ec2') +
        get_tools_by_category('rds') +
        get_tools_by_category('s3') +
        get_tools_by_category('vpc')
    )
)

# Ask for infrastructure overview
response = infra_agent("""
Give me an overview of my AWS infrastructure.
Show me EC2 instances, RDS databases, S3 buckets, and VPC configuration.
Highlight any issues or recommendations.
""")

print(response)
# Agent automatically:
# 1. Calls get_ec2_inventory() for EC2 overview
# 2. Calls analyze_rds_instance() for each database
# 3. Calls find_public_buckets() to check S3 security
# 4. Calls analyze_vpc_configuration() for networking
# 5. Synthesizes findings and highlights issues
```

#### Bedrock AI/ML Cost Optimization with AI Agent

```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Create Bedrock optimization agent
bedrock_agent = Agent(
    model="anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=get_tools_by_category('bedrock')
)

# Ask about AI/ML costs and optimization
response = bedrock_agent("""
Analyze my Bedrock usage and costs.
Which models am I using? Are there cheaper alternatives?
Compare Claude 3 Sonnet vs Haiku for my workload.
""")

print(response)
# Agent automatically:
# 1. Calls analyze_bedrock_usage() to get usage stats
# 2. Calls list_available_models() to see alternatives
# 3. Calls compare_models() for Claude Sonnet vs Haiku
# 4. Analyzes cost/performance tradeoffs
# 5. Recommends optimal model selection
```

#### Find Unused EC2 Resources
```python
from strandkit import find_unused_resources

# Scan for waste
unused = find_unused_resources()
print(f"Potential Monthly Savings: ${unused['total_potential_savings']:.2f}")
print(f"\nStopped Instances: {unused['stopped_instances_count']}")
print(f"Unattached Volumes: {unused['unattached_volumes_count']}")
print(f"Unused Elastic IPs: {unused['unused_elastic_ips_count']}")
print(f"Old Snapshots (>90 days): {unused['old_snapshots_count']}")
```

#### Find Public S3 Buckets
```python
from strandkit import find_public_buckets, analyze_s3_bucket

# Scan all buckets for public access
scan = find_public_buckets()
print(f"Total buckets: {scan['summary']['total_buckets']}")
print(f"🔴 Public buckets: {scan['summary']['public_buckets']}")
print(f"🔴 Critical risks: {scan['summary']['critical']}")

# Analyze risky buckets
for bucket in scan['public_buckets']:
    if bucket['risk_level'] == 'critical':
        details = analyze_s3_bucket(bucket['bucket_name'])
        print(f"\n🔴 {bucket['bucket_name']}:")
        print(f"  Encryption: {'✅' if details['security']['encryption']['enabled'] else '❌'}")
        for reason in bucket['public_reason']:
            print(f"  - {reason}")
```

#### S3 Cost Optimization
```python
from strandkit import find_unused_buckets, get_s3_cost_analysis

# Find empty or unused buckets
unused = find_unused_buckets(min_age_days=90)
print(f"Empty buckets: {len(unused['empty_buckets'])}")
print(f"Potential savings: ${unused['potential_savings']:.2f}/month")

# Get cost breakdown
costs = get_s3_cost_analysis(days_back=30)
print(f"\nTotal S3 cost: ${costs['total_cost']:.2f}")
print(f"Top buckets:")
for bucket in costs['by_bucket'][:5]:
    print(f"  {bucket['bucket_name']}: ${bucket['estimated_monthly_cost']:.2f}/month")
```

#### Find Zombie Resources (Hidden Waste)
```python
from strandkit import find_zombie_resources

# Find forgotten resources costing money
zombies = find_zombie_resources(min_age_days=30)
print(f"Zombie Resources Found: {zombies['summary']['total_zombies']}")
print(f"Monthly Waste: ${zombies['summary']['total_monthly_waste']:.2f}")
print(f"Annual Waste: ${zombies['summary']['total_annual_waste']:.2f}")

# Show top offenders
for zombie in zombies['zombie_resources'][:5]:
    print(f"\n{zombie['resource_type']}: {zombie['resource_id']}")
    print(f"  Age: {zombie['age_days']} days")
    print(f"  Cost: ${zombie['monthly_cost']:.2f}/month")
    print(f"  Reason: {zombie['reason']}")
    print(f"  Action: {zombie['recommendation']}")
```

#### Detect Idle Resources
```python
from strandkit import analyze_idle_resources

# Find idle EC2 instances
idle = analyze_idle_resources(cpu_threshold=5.0, lookback_days=7)
print(f"Idle Resources: {idle['summary']['total_idle']}")
print(f"Potential Savings: ${idle['summary']['potential_monthly_savings']:.2f}/month")

# Show idle instances
for resource in idle['idle_resources']:
    print(f"\n{resource['resource_id']} ({resource['instance_type']})")
    print(f"  Avg CPU: {resource['avg_cpu']:.2f}%")
    print(f"  Max CPU: {resource['max_cpu']:.2f}%")
    print(f"  Cost: ${resource['monthly_cost']:.2f}/month")
    print(f"  Recommendation: {resource['recommendation']}")
```

#### Analyze Snapshot Waste
```python
from strandkit import analyze_snapshot_waste

# Find old and orphaned snapshots
waste = analyze_snapshot_waste(min_age_days=90)
print(f"Total Snapshots: {waste['ebs_snapshots']['total']}")
print(f"Total Size: {waste['ebs_snapshots']['total_size_gb']:,} GB")
print(f"Monthly Cost: ${waste['ebs_snapshots']['monthly_cost']:.2f}")

print(f"\nOld Snapshots (>90 days): {len(waste['ebs_snapshots']['old_snapshots'])}")
print(f"Orphaned Snapshots: {len(waste['ebs_snapshots']['orphaned_snapshots'])}")
print(f"Potential Savings: ${waste['summary']['potential_monthly_savings']:.2f}/month")
```

#### Analyze Data Transfer Costs
```python
from strandkit import analyze_data_transfer_costs

# Often 10-30% of AWS bill
transfer = analyze_data_transfer_costs(days_back=30)
print(f"Total Data Transfer Cost: ${transfer['total_data_transfer_cost']:.2f}")
print(f"Percentage of Total Bill: {transfer['percentage_of_total_bill']:.1f}%")

print("\nCost by Type:")
for transfer_type, cost in transfer['by_type'].items():
    print(f"  {transfer_type}: ${cost:.2f}")

print("\nOptimization Opportunities:")
for opp in transfer['optimization_opportunities']:
    print(f"  • {opp}")
```

#### RDS Database Analysis (NEW)
```python
from strandkit import analyze_rds_instance, find_idle_databases, find_rds_security_issues

# Analyze specific RDS instance
instance = analyze_rds_instance("prod-database")
print(f"Instance: {instance['instance_id']}")
print(f"Engine: {instance['engine']} {instance['engine_version']}")
print(f"Class: {instance['instance_class']}")
print(f"Monthly Cost: ${instance['cost_estimate']['total_monthly_cost']:.2f}")
print(f"Avg CPU: {instance['performance_metrics']['cpu_utilization']['average']:.1f}%")

# Find underutilized databases
idle = find_idle_databases(cpu_threshold=10.0, lookback_days=7)
print(f"\nIdle Databases: {idle['summary']['total_idle_databases']}")
print(f"Potential Savings: ${idle['summary']['potential_monthly_savings']:.2f}/month")

for db in idle['idle_databases']:
    print(f"\n{db['instance_id']} ({db['instance_class']})")
    print(f"  Avg CPU: {db['metrics']['avg_cpu']:.2f}%")
    print(f"  Monthly cost: ${db['monthly_cost']:.2f}")
    print(f"  Recommendation: {db['recommendation']}")

# Security audit
security = find_rds_security_issues()
print(f"\nSecurity Score: {security['summary']['security_score']}/100")
print(f"Total Findings: {security['summary']['total_findings']}")
print(f"Critical: {security['summary']['critical']}")

for finding in security['findings']:
    if finding['severity'] == 'critical':
        print(f"\n🔴 {finding['title']}")
        print(f"  Instance: {finding['instance_id']}")
        print(f"  Issue: {finding['description']}")
```

#### VPC & Networking Analysis (NEW)
```python
from strandkit import (
    find_unused_nat_gateways,
    analyze_vpc_configuration,
    analyze_vpc_endpoints
)

# Find wasted NAT Gateway spend
nat = find_unused_nat_gateways()
print(f"Unused NAT Gateways: {nat['summary']['total_unused']}")
print(f"Monthly Waste: ${nat['summary']['monthly_waste']:.2f}")

for gateway in nat['unused_nat_gateways']:
    print(f"\n{gateway['nat_gateway_id']}")
    print(f"  VPC: {gateway['vpc_id']}")
    print(f"  Bytes transferred: {gateway['bytes_transferred']}")
    print(f"  Monthly cost: ${gateway['monthly_cost']:.2f}")
    print(f"  Recommendation: DELETE (no traffic in 7 days)")

# Analyze VPC configuration
vpc = analyze_vpc_configuration()
print(f"\nTotal VPCs: {vpc['summary']['total_vpcs']}")
print(f"Public Subnets: {vpc['summary']['public_subnets']}")
print(f"Private Subnets: {vpc['summary']['private_subnets']}")
print(f"NAT Gateways: {vpc['summary']['nat_gateways']}")

# Check VPC endpoints for savings
endpoints = analyze_vpc_endpoints()
print(f"\nVPC Endpoints: {endpoints['summary']['total_endpoints']}")
print(f"Gateway Endpoints: {endpoints['summary']['gateway_endpoints']}")
print(f"Interface Endpoints: {endpoints['summary']['interface_endpoints']}")

if endpoints['missing_gateway_endpoints']:
    print("\nMissing Gateway Endpoints (FREE):")
    for missing in endpoints['missing_gateway_endpoints']:
        print(f"  • {missing['service']} - {missing['benefit']}")
        print(f"    Potential savings: ${missing['estimated_monthly_savings']:.2f}/month")
```

#### Bedrock AI/ML Model Analysis (NEW)
```python
from strandkit import (
    analyze_bedrock_usage,
    list_available_models,
    compare_models,
    get_model_details
)

# Analyze Bedrock usage and costs
usage = analyze_bedrock_usage(days_back=30)
print(f"Total Invocations: {usage['summary']['total_invocations']:,}")
print(f"Total Cost: ${usage['summary']['total_cost']:.2f}")
print(f"Cost Source: {usage['summary']['cost_source']}")

# Show usage by model
for model in usage['by_model']:
    print(f"\n{model['model_pattern']}")
    print(f"  Invocations: {model['invocations']:,}")
    print(f"  Avg daily: {model['avg_daily_invocations']}")
    print(f"  Estimated cost: ${model['estimated_cost']:.2f}")

# List available models
models = list_available_models()
print(f"\nAvailable Models: {models['summary']['total_models']}")
print(f"Providers: {', '.join(models['summary']['providers'])}")

# Show models by provider
for provider, model_ids in models['by_provider'].items():
    print(f"\n{provider}: {len(model_ids)} models")
    for model_id in model_ids[:3]:  # First 3
        print(f"  - {model_id}")

# Compare Claude models
claude_models = [m['model_id'] for m in models['models'] if 'claude' in m['model_id'].lower()]
if len(claude_models) >= 2:
    comparison = compare_models(claude_models[:3])

    print("\nModel Comparison:")
    for model in comparison['comparison_table']:
        print(f"\n{model['model_name']}")
        print(f"  Input: ${model['input_price_per_1k']}/1K tokens")
        print(f"  Output: ${model['output_price_per_1k']}/1K tokens")
        print(f"  Context: {model['context_window']}")
        print(f"  Use cases: {', '.join(model['primary_use_cases'])}")

    # Show cost for typical workload
    print("\nCost for Medium Usage (100K input, 50K output tokens):")
    for model in comparison['cost_comparison']['Medium usage']:
        print(f"  {model['model_name']}: ${model['total_cost']:.2f}")

# Get detailed model info
if claude_models:
    details = get_model_details(claude_models[0])
    print(f"\nModel Details: {details['model_info']['model_name']}")
    print(f"Provider: {details['model_info']['provider']}")
    print(f"Streaming: {details['capabilities']['response_streaming']}")
    print(f"Context window: {details['limits']['context_window']}")
    print(f"Recommended for: {', '.join(details['use_cases'])}")
```

#### Full Cost Optimization Scan
```python
from strandkit import find_cost_optimization_opportunities

# Aggregate all optimization opportunities
opportunities = find_cost_optimization_opportunities(min_impact=50.0)

print(f"Total Opportunities: {opportunities['summary']['total_opportunities']}")
print(f"Total Potential Savings: ${opportunities['summary']['total_potential_savings']:.2f}/month")
print(f"High-Impact Opportunities: {opportunities['summary']['high_impact_count']}")

# Prioritized list
for opp in opportunities['opportunities'][:10]:
    print(f"\n{opp['category']}: {opp['title']}")
    print(f"  Impact: ${opp['monthly_impact']:.2f}/month")
    print(f"  Effort: {opp['effort']}")
    print(f"  Risk: {opp['risk']}")
    print(f"  Action: {opp['action']}")
```

---

## Advanced: Standalone Usage (Without Agents)

**For advanced users:** While StrandKit is designed for Strands Agents, you can also call tools directly as Python functions for scripting and automation.

**Note:** For most use cases, we recommend using Strands Agents (shown above) instead of standalone usage. Agents provide:
- **Natural language interface** - Ask questions instead of writing code
- **Intelligent tool selection** - Agent decides which tools to call
- **Multi-tool workflows** - Agent chains multiple tools automatically
- **Contextual analysis** - Agent synthesizes results from multiple tools

### When to Use Standalone Mode

Use standalone mode for:
- **CI/CD pipelines** - Automated checks in deployment workflows
- **Scripts and cron jobs** - Scheduled AWS audits and reports
- **Integration with existing tools** - Embed in your Python applications
- **Non-interactive analysis** - Programmatic data collection

### Standalone Examples

#### Direct Tool Calls

```python
from strandkit import (
    find_overpermissive_roles,
    get_cost_by_service,
    find_zombie_resources,
    analyze_bedrock_usage
)

# IAM Security - Direct function call
roles = find_overpermissive_roles()
print(f"Found {len(roles['overpermissive_roles'])} risky roles")
for role in roles['overpermissive_roles']:
    if role['risk_level'] == 'critical':
        print(f"⚠️ {role['role_name']}: {', '.join(role['risk_factors'])}")

# Cost Analysis - Direct function call
costs = get_cost_by_service(days_back=30)
print(f"\nTotal AWS Cost: ${costs['total_cost']:.2f}")
for service in costs['services'][:5]:
    print(f"  {service['service']}: ${service['cost']:.2f}")

# Find Waste - Direct function call
zombies = find_zombie_resources()
print(f"\nZombie Resources: {zombies['summary']['total_zombies']}")
print(f"Monthly Waste: ${zombies['summary']['total_monthly_waste']:.2f}")

# Bedrock Usage - Direct function call
bedrock = analyze_bedrock_usage(days_back=30)
print(f"\nBedrock Invocations: {bedrock['summary']['total_invocations']:,}")
print(f"Bedrock Cost: ${bedrock['summary']['total_cost']:.2f}")
```

#### Custom AWS Client for Multi-Account/Region

```python
from strandkit.core.aws_client import AWSClient
from strandkit import get_ec2_inventory, find_public_buckets

# Production account
prod_client = AWSClient(profile="production", region="us-east-1")
prod_ec2 = get_ec2_inventory(aws_client=prod_client)
print(f"Production EC2: {prod_ec2['summary']['total_instances']} instances")

# Dev account
dev_client = AWSClient(profile="dev", region="us-west-2")
dev_buckets = find_public_buckets(aws_client=dev_client)
print(f"Dev public buckets: {dev_buckets['summary']['public_buckets']}")
```

For complete standalone examples of all 78 tools, see the sections below and [QUICKSTART.md](QUICKSTART.md).

---

## Documentation

### Core Components

#### AWS Client

```python
from strandkit.core.aws_client import AWSClient

# Use specific profile and region
client = AWSClient(profile="dev", region="us-west-2")
logs_client = client.get_client("logs")
```

#### CloudWatch Tools

**Get Lambda Logs**

```python
from strandkit.tools.cloudwatch import get_lambda_logs

logs = get_lambda_logs(
    function_name="my-function",
    start_minutes=60,           # Look back 60 minutes
    filter_pattern="ERROR",     # Optional: filter for errors
    limit=100                   # Max events to return
)

# Returns structured JSON:
# {
#   "function_name": "my-function",
#   "total_events": 42,
#   "error_count": 5,
#   "has_errors": true,
#   "events": [...]
# }
```

**Query Metrics**

```python
from strandkit.tools.cloudwatch import get_metric

metrics = get_metric(
    namespace="AWS/Lambda",
    metric_name="Duration",
    dimensions={"FunctionName": "my-function"},
    statistic="Average",        # Average, Sum, Maximum, Minimum
    period=300,                 # 5 minutes
    start_minutes=120           # Last 2 hours
)

# Returns:
# {
#   "datapoints": [...],
#   "summary": {
#     "min": 10.5,
#     "max": 150.2,
#     "avg": 45.7,
#     "count": 24
#   }
# }
```

#### CloudFormation Tools

**Explain Changeset**

```python
from strandkit.tools.cloudformation import explain_changeset

result = explain_changeset(
    changeset_name="my-changeset",
    stack_name="my-stack"
)

# Returns:
# {
#   "summary": {
#     "total_changes": 5,
#     "high_risk_changes": 2,
#     "requires_replacement": 1
#   },
#   "changes": [
#     {
#       "resource_type": "AWS::Lambda::Function",
#       "action": "Modify",
#       "risk_level": "high",
#       "details": "⚠️ REPLACING Lambda Function 'MyFunc'..."
#     }
#   ],
#   "recommendations": [...]
# }
```

## Examples

Check the `examples/` directory for more:

- **`basic_usage.py`** - Simple examples for each tool
- **`test_imports.py`** - Verify installation
- **`demo_real_insights.py`** - Full health dashboard example

Run an example:
```bash
python examples/test_imports.py
```

## Project Structure

```
strandkit/
├── core/
│   ├── aws_client.py       # AWS credential management
│   ├── base_agent.py       # Base class for agents (WIP)
│   └── schema.py           # Tool schema definitions (WIP)
├── tools/
│   ├── cloudwatch.py       # CloudWatch Logs & Metrics
│   └── cloudformation.py   # CloudFormation analysis
├── agents/
│   └── infra_debugger.py   # Infrastructure debugging agent (WIP)
├── prompts/
│   └── infra_debugger_system.md  # Agent system prompts
└── cli/
    └── __main__.py         # CLI interface (WIP)
```

## Development Status

**Current Version:** 0.9.0

✅ **Complete:**
- AWS Client wrapper
- **CloudWatch tools** - Logs, Metrics, Insights queries, error detection (4 tools)
- **CloudFormation tools** - Changeset analysis with risk assessment (1 tool)
- **IAM tools** - Role analysis, policy explanation, security scanning (3 tools)
- **IAM Security tools** - User audits, MFA compliance, privilege escalation detection (8 tools)
- **Cost Explorer tools** - Usage analysis, forecasting, anomaly detection (4 tools)
- **Cost Analytics tools** - RI/SP analysis, rightsizing, budgets, optimization (6 tools)
- **Cost Waste Detection tools** - Zombie resources, idle detection, snapshot waste (5 tools)
- **EC2 & Compute tools** - Instance analysis, security groups, resource optimization (5 tools)
- **S3 & Storage tools** - Bucket security, public access detection, cost optimization (5 tools)
- **EBS & Volume Optimization tools** - GP2→GP3 migration, IOPS, snapshots, encryption (6 tools)
- **S3 Advanced Optimization tools** - Storage classes, lifecycle, versioning, replication (7 tools)
- **RDS & Database tools** - Instance analysis, idle detection, backups, security (5 tools)
- **VPC & Networking tools** - NAT Gateways, VPC config, data transfer, endpoints (5 tools)
- **Bedrock & AI/ML tools** - Model analysis, usage monitoring, cost optimization (6 tools)
- Comprehensive documentation and examples
- **78 production-ready tools** tested with real AWS accounts

🚧 **In Progress:**
- Agent framework (pending AWS Strands integration)
- InfraDebuggerAgent implementation
- CLI interface

📋 **Planned:**
- Lambda advanced tools (monitoring, performance, cost analysis)
- DynamoDB tools (table analysis, capacity optimization)
- Knowledge base tools (Bedrock knowledge bases, RAG optimization)
- Additional agent templates
- PyPI package publication
- MCP server integration

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed status.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/lhassa8/StrandKit.git
cd StrandKit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python examples/test_imports.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

### Phase 1: Core Tools ✅ (Complete)
- ✅ AWS client wrapper
- ✅ CloudWatch tools
- ✅ CloudFormation tools
- ✅ Documentation

### Phase 2: Agent Framework 🚧 (In Progress)
- 🚧 BaseAgent implementation
- 🚧 AWS Strands integration
- 📋 InfraDebuggerAgent

### Phase 3: Expansion 📋 (Planned)
- 📋 IAM analyzer
- 📋 Cost insights
- 📋 Additional agents
- 📋 CLI enhancements

### Phase 4: Distribution 📋 (Future)
- 📋 PyPI publication
- 📋 Documentation website
- 📋 Video tutorials
- 📋 Community building

## Support

- **Documentation:** See [QUICKSTART.md](QUICKSTART.md) for detailed usage
- **Issues:** [GitHub Issues](https://github.com/lhassa8/StrandKit/issues)
- **Discussions:** [GitHub Discussions](https://github.com/lhassa8/StrandKit/discussions)

## Acknowledgments

- Built on top of **AWS Strands Agents**
- Powered by **boto3**
- Inspired by the need for better AWS debugging tools

## Star History

If you find StrandKit useful, please consider giving it a star ⭐

---

<div align="center">

**Built with ❤️ for AWS developers**

[Report Bug](https://github.com/lhassa8/StrandKit/issues) •
[Request Feature](https://github.com/lhassa8/StrandKit/issues) •
[View Documentation](QUICKSTART.md)

</div>
