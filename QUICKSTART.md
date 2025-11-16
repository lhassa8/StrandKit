# StrandKit Quick Start Guide

## Installation (Development Mode)

Since this is in development, you can use it directly:

```bash
cd StrandKit
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

Or create a virtual environment and install in editable mode:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Prerequisites

1. **AWS Credentials**
   - Configure AWS CLI: `aws configure`
   - Or use AWS profiles in `~/.aws/credentials`

2. **Python 3.8+**
   - Install boto3: `pip install boto3`

## Using the Tools

### 1. Get Lambda Logs

```python
from strandkit.tools.cloudwatch import get_lambda_logs

# Get logs from the last hour
logs = get_lambda_logs("my-lambda-function", start_minutes=60)

print(f"Total events: {logs['total_events']}")
print(f"Errors found: {logs['error_count']}")

# Print error messages
for event in logs['events']:
    if 'ERROR' in event['message']:
        print(f"[{event['timestamp']}] {event['message']}")
```

**Filter for specific patterns:**

```python
# Only get ERROR logs
error_logs = get_lambda_logs(
    "my-function",
    start_minutes=30,
    filter_pattern="ERROR"
)
```

### 2. Query CloudWatch Metrics

```python
from strandkit.tools.cloudwatch import get_metric

# Get Lambda errors over last 2 hours
errors = get_metric(
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": "my-api"},
    statistic="Sum",
    period=300,  # 5-minute intervals
    start_minutes=120
)

print(f"Summary: {errors['summary']}")
# Output: {'min': 0, 'max': 10, 'avg': 2.5, 'count': 24}

# Plot datapoints
for point in errors['datapoints']:
    print(f"{point['timestamp']}: {point['value']}")
```

**Common metrics:**

```python
# Lambda duration (average)
duration = get_metric(
    namespace="AWS/Lambda",
    metric_name="Duration",
    dimensions={"FunctionName": "my-function"},
    statistic="Average"
)

# Lambda invocations (count)
invocations = get_metric(
    namespace="AWS/Lambda",
    metric_name="Invocations",
    dimensions={"FunctionName": "my-function"},
    statistic="Sum"
)

# DynamoDB throttles
throttles = get_metric(
    namespace="AWS/DynamoDB",
    metric_name="UserErrors",
    dimensions={"TableName": "my-table"},
    statistic="Sum"
)
```

### 3. Explain CloudFormation Changeset

```python
from strandkit.tools.cloudformation import explain_changeset

# Analyze a changeset before applying
result = explain_changeset(
    changeset_name="my-app-changeset-123",
    stack_name="my-app-stack"
)

print(f"Status: {result['status']}")
print(f"Total changes: {result['summary']['total_changes']}")

# Check recommendations
for rec in result['recommendations']:
    print(rec)

# Review high-risk changes
for change in result['changes']:
    if change['risk_level'] == 'high':
        print(f"⚠️ {change['details']}")
```

### 4. Using Custom AWS Profiles/Regions

```python
from strandkit.core.aws_client import AWSClient
from strandkit.tools.cloudwatch import get_lambda_logs

# Create client for specific profile and region
aws = AWSClient(profile="dev", region="us-west-2")

# Pass to tools
logs = get_lambda_logs(
    "my-function",
    start_minutes=60,
    aws_client=aws
)
```

## Real-World Examples

### Debug a Lambda Function

```python
from strandkit.tools.cloudwatch import get_lambda_logs, get_metric

function_name = "my-api-function"

# 1. Check error metrics
errors = get_metric(
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": function_name},
    statistic="Sum",
    period=300,
    start_minutes=120
)

if errors['summary']['max'] > 0:
    print(f"⚠️ Found {errors['summary']['max']} errors in a 5-min period")

    # 2. Get error logs
    error_logs = get_lambda_logs(
        function_name,
        start_minutes=120,
        filter_pattern="ERROR"
    )

    # 3. Print recent errors
    print("\nRecent errors:")
    for event in error_logs['events'][-10:]:
        print(f"  {event['timestamp']}: {event['message'][:100]}")
```

### Review CloudFormation Changes Before Deploy

```python
from strandkit.tools.cloudformation import explain_changeset

changeset = explain_changeset("my-changeset", "my-stack")

# Check for dangerous changes
high_risk = [c for c in changeset['changes'] if c['risk_level'] == 'high']

if high_risk:
    print("⚠️ HIGH RISK CHANGES DETECTED:")
    for change in high_risk:
        print(f"  - {change['details']}")

    print("\nRecommendations:")
    for rec in changeset['recommendations']:
        print(f"  {rec}")

    response = input("\nProceed with deployment? (yes/no): ")
    if response.lower() != 'yes':
        print("Deployment cancelled.")
```

### Monitor Multiple Functions

```python
from strandkit.tools.cloudwatch import get_metric

functions = ["auth-api", "user-api", "payment-api"]

print("Error rates (last hour):\n")
for func in functions:
    errors = get_metric(
        namespace="AWS/Lambda",
        metric_name="Errors",
        dimensions={"FunctionName": func},
        statistic="Sum",
        period=3600,  # 1 hour
        start_minutes=60
    )

    total_errors = sum(p['value'] for p in errors['datapoints'])
    status = "🔴" if total_errors > 10 else "🟢"
    print(f"{status} {func}: {total_errors} errors")
```

## Testing Without AWS Calls

Run the import test to verify everything is set up:

```bash
python3 examples/test_imports.py
```

Expected output:
```
============================================================
StrandKit Import Test
============================================================

Testing StrandKit imports...

✓ strandkit.core.aws_client.AWSClient
✓ strandkit.core.schema (ToolSchema, ToolParameter)
✓ strandkit.core.base_agent.BaseAgent
✓ strandkit.tools.cloudwatch (get_lambda_logs, get_metric)
✓ strandkit.tools.cloudformation.explain_changeset
✓ strandkit.agents.infra_debugger.InfraDebuggerAgent
✓ strandkit (top-level imports)

============================================================
All imports successful!
============================================================
```

## Error Handling

All tools return structured JSON even on errors:

```python
logs = get_lambda_logs("non-existent-function", start_minutes=60)

if 'error' in logs or 'warning' in logs:
    print(f"Warning: {logs.get('warning', logs.get('error'))}")
else:
    print(f"Found {logs['total_events']} events")
```

## Next Steps

1. **Try the examples:**
   ```bash
   python3 examples/basic_usage.py
   ```

2. **Customize for your use case:**
   - Replace function names with your actual Lambda functions
   - Adjust time ranges as needed
   - Add error handling for production use

3. **Build on top:**
   - Create scripts for common debugging tasks
   - Integrate with alerting systems
   - Build dashboards using the data

## Troubleshooting

**ImportError: No module named 'strandkit'**
- Add to PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`
- Or use sys.path in your script (see examples/test_imports.py)

**NoCredentialsError**
- Run `aws configure` to set up AWS credentials
- Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

**ResourceNotFound errors**
- Verify the Lambda function/stack exists
- Check you're using the correct AWS region
- Ensure you have permissions to access the resources

## What's Coming

- **Agent framework** (InfraDebuggerAgent) - pending AWS Strands integration
- **CLI interface** - `strandkit run debugger`
- **More tools** - IAM analyzer, cost insights
- **Tests and examples**

For the latest status, see `PROJECT_STATUS.md`.
