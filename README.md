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

| Tool | Description | Status |
|------|-------------|--------|
| **`get_lambda_logs`** | Retrieve and parse Lambda CloudWatch logs | ✅ Working |
| **`get_metric`** | Query CloudWatch metrics with statistics | ✅ Working |
| **`explain_changeset`** | Analyze CloudFormation changesets with risk assessment | ✅ Working |

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
from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
from strandkit.tools.cloudformation import explain_changeset

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

# Analyze CloudFormation changes
changeset = explain_changeset("my-changeset", "my-stack")
for change in changeset['changes']:
    if change['risk_level'] == 'high':
        print(f"⚠️ {change['details']}")
```

### Real-World Example: Debug Lambda Errors

```python
from strandkit.tools.cloudwatch import get_lambda_logs, get_metric

function_name = "my-api-function"

# 1. Check if there are errors
errors = get_metric(
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": function_name},
    statistic="Sum",
    start_minutes=120
)

if errors['summary']['max'] > 0:
    print(f"⚠️ Found errors! Investigating...")

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

**Current Version:** 0.1.0 (MVP)

✅ **Complete:**
- AWS Client wrapper
- CloudWatch Logs tool (`get_lambda_logs`)
- CloudWatch Metrics tool (`get_metric`)
- CloudFormation changeset analyzer (`explain_changeset`)
- Comprehensive documentation and examples

🚧 **In Progress:**
- Agent framework (pending AWS Strands integration)
- InfraDebuggerAgent implementation
- CLI interface

📋 **Planned:**
- IAM policy analyzer
- Cost analysis tools
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
