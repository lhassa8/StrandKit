# StrandKit Quick Start Guide

**Version 0.2.0** - Complete AWS Toolkit with 14 Production-Ready Tools

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

## Available Tools

StrandKit provides 14 tools across 4 categories:
- **CloudWatch** (4 tools): Logs, metrics, insights queries, error detection
- **IAM** (3 tools): Role analysis, policy explanation, security scanning
- **Cost** (4 tools): Usage analysis, forecasting, anomaly detection
- **CloudFormation** (1 tool): Changeset analysis

See [TOOLS.md](TOOLS.md) for complete API reference.

---

## Using the Tools

### CloudWatch: Get Lambda Logs

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

---

### IAM: Analyze Role Security

```python
from strandkit.tools.iam import analyze_role, find_overpermissive_roles

# Analyze a specific role
role = analyze_role("MyAppRole")
print(f"Risk Level: {role['risk_assessment']['risk_level']}")

for recommendation in role['recommendations']:
    print(f"  {recommendation}")

# Scan all roles for issues
audit = find_overpermissive_roles()
print(f"\nFound {len(audit['overpermissive_roles'])} risky roles:")
for r in audit['overpermissive_roles'][:5]:
    print(f"  {r['role_name']} - {r['risk_level']}")
```

**Example output:**
```
Risk Level: medium
  ⚠️ Replace wildcard resources (*) with specific resource ARNs

Found 12 risky roles:
  veridano-admin-dashboard-lambda-role - medium
  veridano-lambda-execution-role - medium
  ...
```

---

### Cost: Analyze Spending

```python
from strandkit.tools.cost import get_cost_by_service, detect_cost_anomalies

# Get cost breakdown
costs = get_cost_by_service(days_back=30, top_n=5)
print(f"Total: ${costs['total_cost']:.2f}\n")
for svc in costs['services']:
    print(f"{svc['service']}: ${svc['cost']:.2f} ({svc['percentage']:.1f}%)")

# Detect anomalies
anomalies = detect_cost_anomalies(days_back=30)
if anomalies['total_anomalies'] > 0:
    print(f"\n⚠️ {anomalies['total_anomalies']} cost spikes detected")
```

**Example output:**
```
Total: $148.84

Amazon RDS: $130.78 (87.9%)
AWS WAF: $7.80 (5.2%)
CloudWatch: $3.93 (2.6%)
VPC: $3.55 (2.4%)
Secrets Manager: $1.18 (0.8%)
```

---

### Advanced: Logs Insights Queries

```python
from strandkit.tools.cloudwatch_enhanced import get_log_insights

# Run custom query
results = get_log_insights(
    log_group_names=["/aws/lambda/my-function"],
    query_string="""
        fields @timestamp, @message
        | filter @message like /ERROR/
        | stats count() by bin(5m)
        | limit 100
    """,
    start_minutes=120
)

print(f"Scanned {results['statistics']['records_scanned']} records")
print(f"Found {results['statistics']['records_matched']} matches")
```

---

## Complete Examples

### Security Audit Workflow

```python
from strandkit import find_overpermissive_roles, analyze_role

# 1. Scan all roles
audit = find_overpermissive_roles()

# 2. Analyze high-risk roles
for role in audit['overpermissive_roles']:
    if role['risk_level'] in ['critical', 'high']:
        details = analyze_role(role['role_name'])
        
        print(f"\n🔴 {role['role_name']}")
        print(f"   Services: {', '.join(details['permissions_summary']['services_accessed'][:3])}")
        
        for rec in details['recommendations']:
            print(f"   {rec}")
```

### Cost Optimization Workflow

```python
from strandkit import (
    get_cost_by_service,
    detect_cost_anomalies,
    get_cost_forecast
)

# 1. Current spending
costs = get_cost_by_service(days_back=30)
print(f"Last 30 days: ${costs['total_cost']:.2f}")

# 2. Check for anomalies
anomalies = detect_cost_anomalies(days_back=30)
if anomalies['total_anomalies'] > 0:
    print(f"⚠️ {anomalies['total_anomalies']} unusual spending days detected")

# 3. Forecast next month
forecast = get_cost_forecast(days_forward=30)
print(f"Predicted next 30 days: ${forecast['forecast']['predicted_cost']:.2f}")
```

### Infrastructure Debugging Workflow

```python
from strandkit import get_lambda_logs, get_metric, analyze_role

function_name = "my-api"

# 1. Check metrics
errors = get_metric(
    "AWS/Lambda", "Errors",
    {"FunctionName": function_name},
    "Sum"
)

if errors['summary']['max'] > 0:
    # 2. Get error logs
    logs = get_lambda_logs(function_name, filter_pattern="ERROR")
    
    # 3. Check permissions
    role_name = f"{function_name}-execution-role"
    role = analyze_role(role_name)
    
    print("Issues found:")
    print(f"  Errors: {errors['summary']['max']}")
    print(f"  Recent log entries: {logs['total_events']}")
    print(f"  Role risk: {role['risk_assessment']['risk_level']}")
```

---

## Real-World Use Cases

### 1. Daily Security Check

```bash
python3 -c "
from strandkit import find_overpermissive_roles
audit = find_overpermissive_roles()
critical = audit['summary']['critical']
high = audit['summary']['high']
if critical > 0 or high > 0:
    print(f'⚠️ Security Alert: {critical} critical, {high} high-risk roles')
    exit(1)
print('✅ Security check passed')
"
```

### 2. Cost Alert Script

```python
from strandkit import detect_cost_anomalies

anomalies = detect_cost_anomalies(days_back=7, threshold_percentage=15)

if anomalies['total_anomalies'] > 0:
    # Send alert
    high_severity = [a for a in anomalies['anomalies'] if a['severity'] == 'high']
    if high_severity:
        send_alert(f"High cost spike detected: {high_severity[0]['date']}")
```

### 3. Lambda Monitor Dashboard

```python
from strandkit import get_metric, get_lambda_logs

functions = ["api-1", "api-2", "worker-1"]

for func in functions:
    errors = get_metric("AWS/Lambda", "Errors", {"FunctionName": func}, "Sum", start_minutes=60)
    invocations = get_metric("AWS/Lambda", "Invocations", {"FunctionName": func}, "Sum", start_minutes=60)
    
    error_rate = (errors['summary']['total'] / invocations['summary']['total'] * 100) if invocations['summary']['total'] > 0 else 0
    
    status = "🔴" if error_rate > 1 else "🟡" if error_rate > 0.1 else "🟢"
    print(f"{status} {func}: {error_rate:.2f}% error rate")
```
