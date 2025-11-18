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

StrandKit is a companion SDK for **[AWS Strands Agents](https://strandsagents.com/)** that provides **72 production-ready AWS tools** for:

- 💰 **Cost optimization** - Find waste, analyze spending, get rightsizing recommendations
- 🔒 **Security auditing** - Scan IAM policies, detect misconfigurations, enforce compliance
- 📊 **Infrastructure monitoring** - Analyze CloudWatch metrics, track performance, debug issues
- ⚡ **Performance tuning** - Identify bottlenecks, optimize auto-scaling, analyze load balancers

**Perfect for AWS Strands Agents:**
- **Orchestrator tools** - 4 high-level tools designed for common agent tasks (security audit, cost optimization, diagnostics)
- **Drop-in ready** - All 72 tools work seamlessly with Strands agents via `get_all_tools()`
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

Learn more: [strandsagents.com](https://strandsagents.com/latest/)

## Why StrandKit?

**StrandKit supercharges AWS Strands Agents with 72 production-ready AWS tools** (4 orchestrators + 68 granular).

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
    model="anthropic.claude-3-5-sonnet"
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
- ✅ **Category filtering** - Load only the tools you need (orchestrators, IAM, Cost, EC2, S3, RDS, VPC, etc.)
- ✅ **Production-ready** - All 72 tools tested with real AWS accounts
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
    model="anthropic.claude-3-5-haiku"
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

**Using all 68 granular tools (advanced):**

Use StrandKit's 68 granular tools when you need fine-grained control:

```python
from strands import Agent
from strandkit.strands import get_all_tools

# Create agent with all granular tools
agent = Agent(
    name="aws-analyst",
    tools=get_all_tools(),  # 68 AWS granular tools ready to use
    model="anthropic.claude-3-5-haiku"
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
    model="anthropic.claude-3-5-haiku"
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
    model="anthropic.claude-3-5-sonnet"
)

cost_agent = Agent(
    name="cost-optimizer",
    tools=(get_tools_by_category('cost') +
           get_tools_by_category('cost_waste')),
    model="anthropic.claude-3-5-haiku"
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

### From Source (Current)

```bash
git clone https://github.com/lhassa8/StrandKit.git
cd StrandKit
pip install -e .
```

### From PyPI (Coming Soon)

```bash
pip install strandkit
```

## Quick Start

### Prerequisites

1. **AWS Credentials**: Configure AWS CLI or set environment variables
   ```bash
   aws configure
   ```

2. **Python 3.8+**: Ensure you have a recent Python version
   ```bash
   python --version
   ```

### Basic Usage

```python
from strandkit import (
    get_lambda_logs,
    get_metric,
    analyze_role,
    get_cost_by_service,
    get_ec2_inventory,
    find_overpermissive_security_groups
)

# Get Lambda logs from the last hour
logs = get_lambda_logs("my-function", start_minutes=60)
print(f"Found {logs['error_count']} errors in {logs['total_events']} events")

# Query CloudWatch metrics
errors = get_metric(
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": "my-api"},
    statistic="Sum"
)
print(f"Error rate: {errors['summary']}")

# Get EC2 inventory
inventory = get_ec2_inventory()
print(f"Total instances: {inventory['summary']['total_instances']}")
print(f"Monthly cost: ${inventory['total_monthly_cost']:.2f}")

# Scan security groups for risks
sg_scan = find_overpermissive_security_groups()
print(f"Critical security groups: {sg_scan['summary']['critical']}")

# Analyze IAM role security
role = analyze_role("MyAppRole")
print(f"Risk level: {role['risk_assessment']['risk_level']}")

# Get cost breakdown by service
costs = get_cost_by_service(days_back=30, top_n=5)
for svc in costs['services']:
    print(f"{svc['service']}: ${svc['cost']:.2f}")
```

### Real-World Examples

#### Debug Lambda Errors
```python
from strandkit import get_lambda_logs, get_metric

function_name = "my-api-function"

# 1. Check error metrics
errors = get_metric(
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": function_name},
    statistic="Sum",
    start_minutes=120
)

if errors['summary']['max'] > 0:
    # 2. Get error logs
    error_logs = get_lambda_logs(
        function_name,
        start_minutes=120,
        filter_pattern="ERROR"
    )

    # 3. Print error messages
    for event in error_logs['events']:
        print(f"[{event['timestamp']}] {event['message']}")
```

#### Security Audit
```python
from strandkit import find_overpermissive_roles, analyze_role

# Scan all roles
audit = find_overpermissive_roles()
print(f"Found {len(audit['overpermissive_roles'])} risky roles")

# Analyze critical roles
for role in audit['overpermissive_roles']:
    if role['risk_level'] in ['critical', 'high']:
        details = analyze_role(role['role_name'])
        print(f"\n⚠️ {role['role_name']}:")
        for rec in details['recommendations']:
            print(f"  {rec}")
```

#### IAM Security Compliance Audit
```python
from strandkit import (
    analyze_iam_users,
    analyze_mfa_compliance,
    analyze_password_policy,
    detect_privilege_escalation_paths
)

# Check user security
users = analyze_iam_users(inactive_days=90)
print(f"Inactive users: {users['summary']['inactive_users']}")
print(f"MFA compliance: {users['summary']['mfa_compliance_rate']}%")
print(f"Old access keys: {users['summary']['old_access_keys']}")

# Check MFA compliance
mfa = analyze_mfa_compliance()
if not mfa['root_mfa_status']['enabled']:
    print("🚨 CRITICAL: Root account MFA not enabled!")
print(f"Console MFA compliance: {mfa['summary']['console_mfa_compliance_rate']}%")

# Check password policy
policy = analyze_password_policy()
print(f"Password policy security score: {policy['security_score']}/100")
if policy['violations']:
    print(f"Policy violations: {len(policy['violations'])}")

# Detect privilege escalation
escalation = detect_privilege_escalation_paths()
if escalation['summary']['critical_severity'] > 0:
    print(f"🚨 CRITICAL: {escalation['summary']['critical_severity']} escalation paths!")
```

#### IAM Credential Report (Comprehensive Audit)
```python
from strandkit import get_iam_credential_report

# Generate complete credential audit
report = get_iam_credential_report()

print(f"Total users: {report['summary']['total_users']}")
print(f"MFA compliance: {report['summary']['mfa_compliance_rate']}%")
print(f"Passwords >90 days: {report['summary']['passwords_over_90_days']}")
print(f"Access keys >90 days: {report['summary']['access_keys_over_90_days']}")
print(f"Inactive users: {report['summary']['inactive_users']}")

# Show users with issues
for user in report['users']:
    if user['issues']:
        print(f"\n⚠️ {user['username']}:")
        for issue in user['issues']:
            print(f"  - {issue}")
```

#### Cost Analysis
```python
from strandkit import get_cost_by_service, detect_cost_anomalies

# Get spending breakdown
costs = get_cost_by_service(days_back=30)
print(f"Total: ${costs['total_cost']:.2f}")
for svc in costs['services'][:5]:
    print(f"  {svc['service']}: ${svc['cost']:.2f} ({svc['percentage']:.1f}%)")

# Check for unusual spending
anomalies = detect_cost_anomalies(days_back=30)
if anomalies['total_anomalies'] > 0:
    print(f"\n⚠️ {anomalies['total_anomalies']} cost anomalies detected!")
    for a in anomalies['anomalies']:
        print(f"  {a['date']}: ${a['cost']:.2f} (+{a['deviation_percentage']:.1f}%)")
```

#### EC2 Security Audit
```python
from strandkit import find_overpermissive_security_groups, analyze_security_group

# Scan all security groups
scan = find_overpermissive_security_groups()
print(f"Security Groups Scanned: {scan['summary']['total_groups']}")
print(f"Critical Risks: {scan['summary']['critical']}")
print(f"High Risks: {scan['summary']['high']}")

# Analyze risky groups
for sg in scan['risky_groups']:
    if sg['risk_level'] in ['critical', 'high']:
        details = analyze_security_group(sg['group_id'])
        print(f"\n🔴 {sg['group_name']}:")
        for factor in sg['risk_factors']:
            print(f"  - {factor}")
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
- Comprehensive documentation and examples
- **72 production-ready tools** tested with real AWS accounts

🚧 **In Progress:**
- Agent framework (pending AWS Strands integration)
- InfraDebuggerAgent implementation
- CLI interface

📋 **Planned:**
- Lambda advanced tools
- DynamoDB tools
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
