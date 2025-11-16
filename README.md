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

StrandKit is **not** a new agent framework—it extends AWS Strands by providing AWS-focused tools, prebuilt agent templates, and clean Python APIs that hide Strands boilerplate.

Think of it as the **developer experience layer** for AWS Strands Agents:
- 🔧 **Batteries-included AWS tools** (CloudWatch, CloudFormation, IAM)
- 🤖 **Ready-to-use agent templates** (InfraDebuggerAgent, etc.)
- 🎯 **Simple, Pythonic APIs** that hide complexity
- 📋 **LLM-friendly schemas** and documentation
- 📖 **Comprehensive docstrings** and examples

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

#### Cost Explorer Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`get_cost_and_usage`** | Get cost data for any time period | ✅ Working |
| **`get_cost_by_service`** | Break down costs by AWS service | ✅ Working |
| **`detect_cost_anomalies`** | Find unusual spending patterns | ✅ Working |
| **`get_cost_forecast`** | Forecast future AWS costs | ✅ Working |

#### EC2 & Compute Tools
| Tool | Description | Status |
|------|-------------|--------|
| **`analyze_ec2_instance`** | Comprehensive instance analysis with metrics | ✅ Working |
| **`get_ec2_inventory`** | List all instances with summary statistics | ✅ Working |
| **`find_unused_resources`** | Find stopped instances, unattached volumes, unused EIPs | ✅ Working |
| **`analyze_security_group`** | Analyze security group rules with risk assessment | ✅ Working |
| **`find_overpermissive_security_groups`** | Scan all security groups for security risks | ✅ Working |

### Agent Templates (Coming Soon)

| Agent | Description | Status |
|-------|-------------|--------|
| **InfraDebuggerAgent** | Debug AWS infrastructure issues automatically | 🚧 In Progress |
| **IAMReviewerAgent** | Review and explain IAM policies | 📋 Planned |
| **CostAnalystAgent** | Analyze AWS costs and anomalies | 📋 Planned |

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

**Current Version:** 0.3.0

✅ **Complete:**
- AWS Client wrapper
- **CloudWatch tools** - Logs, Metrics, Insights queries, error detection (4 tools)
- **CloudFormation tools** - Changeset analysis with risk assessment (1 tool)
- **IAM tools** - Role analysis, policy explanation, security scanning (3 tools)
- **Cost Explorer tools** - Usage analysis, forecasting, anomaly detection (4 tools)
- **EC2 & Compute tools** - Instance analysis, security groups, resource optimization (5 tools)
- Comprehensive documentation and examples
- **19 production-ready tools** tested with real AWS accounts

🚧 **In Progress:**
- Agent framework (pending AWS Strands integration)
- InfraDebuggerAgent implementation
- CLI interface

📋 **Planned:**
- S3 bucket analysis tools
- RDS database monitoring tools
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
