# StrandKit Tools Reference

Complete reference for all 14 StrandKit tools.

---

## CloudWatch Tools

### get_lambda_logs()

Retrieve CloudWatch logs for a Lambda function.

**Parameters:**
- `function_name` (str): Lambda function name
- `start_minutes` (int): Minutes to look back (default: 60)
- `filter_pattern` (str, optional): CloudWatch filter pattern
- `limit` (int): Max events to return (default: 100)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "function_name": "my-function",
  "log_group": "/aws/lambda/my-function",
  "time_range": {"start": "...", "end": "..."},
  "total_events": 42,
  "error_count": 5,
  "has_errors": true,
  "events": [
    {
      "timestamp": "2025-11-16T10:30:00Z",
      "message": "Error processing request",
      "stream": "2025/11/16/[$LATEST]abc123"
    }
  ]
}
```

**Example:**
```python
logs = get_lambda_logs("my-function", start_minutes=60, filter_pattern="ERROR")
```

---

### get_metric()

Query CloudWatch metrics with statistics.

**Parameters:**
- `namespace` (str): CloudWatch namespace (e.g., "AWS/Lambda")
- `metric_name` (str): Metric name (e.g., "Errors", "Duration")
- `dimensions` (dict, optional): Metric dimensions
- `statistic` (str): Statistic type (default: "Average")
  - Options: "Average", "Sum", "Maximum", "Minimum", "SampleCount"
- `period` (int): Period in seconds (default: 300)
- `start_minutes` (int): Minutes to look back (default: 120)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "namespace": "AWS/Lambda",
  "metric_name": "Errors",
  "dimensions": {"FunctionName": "my-api"},
  "statistic": "Sum",
  "datapoints": [
    {"timestamp": "2025-11-16T10:00:00Z", "value": 5.0, "unit": "Count"}
  ],
  "summary": {"min": 0, "max": 10, "avg": 3.5, "count": 24}
}
```

**Example:**
```python
errors = get_metric(
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": "my-function"},
    statistic="Sum",
    period=300
)
```

---

### get_log_insights()

Run advanced CloudWatch Logs Insights queries.

**Parameters:**
- `log_group_names` (list[str]): Log groups to query
- `query_string` (str): Logs Insights query
- `start_minutes` (int): Minutes to look back (default: 60)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "log_groups": ["/aws/lambda/my-function"],
  "query": "fields @timestamp, @message | filter @message like /ERROR/",
  "results": [
    {
      "timestamp": "2025-11-16T10:30:00Z",
      "fields": {"@message": "Error occurred"}
    }
  ],
  "statistics": {
    "records_matched": 10,
    "records_scanned": 1000,
    "bytes_scanned": 50000
  },
  "status": "Complete"
}
```

**Example:**
```python
results = get_log_insights(
    log_group_names=["/aws/lambda/my-function"],
    query_string="fields @timestamp, @message | filter @message like /ERROR/ | limit 20"
)
```

---

### get_recent_errors()

Quick helper to find recent errors across log groups.

**Parameters:**
- `log_group_pattern` (str): Pattern to match (default: "/aws/lambda/")
- `start_minutes` (int): Minutes to look back (default: 60)
- `limit` (int): Max errors to return (default: 50)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "log_groups_scanned": 10,
  "total_errors": 15,
  "errors": [
    {
      "timestamp": "2025-11-16T10:30:00Z",
      "log_group": "my-function",
      "message": "Error processing request"
    }
  ]
}
```

**Example:**
```python
errors = get_recent_errors("/aws/lambda/", start_minutes=60)
```

---

## CloudFormation Tools

### explain_changeset()

Analyze CloudFormation changeset with risk assessment.

**Parameters:**
- `changeset_name` (str): Changeset name or ARN
- `stack_name` (str): CloudFormation stack name
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "changeset_name": "my-changeset",
  "stack_name": "my-stack",
  "status": "CREATE_COMPLETE",
  "changes": [
    {
      "resource_type": "AWS::Lambda::Function",
      "logical_id": "MyFunction",
      "action": "Modify",
      "replacement": "True",
      "risk_level": "high",
      "details": "⚠️ REPLACING Lambda Function 'MyFunction'..."
    }
  ],
  "summary": {
    "total_changes": 5,
    "high_risk_changes": 2,
    "requires_replacement": 1
  },
  "recommendations": ["⚠️ Some resources will be replaced..."]
}
```

**Example:**
```python
analysis = explain_changeset("my-changeset", "my-stack")
```

---

## IAM Tools

### analyze_role()

Analyze IAM role permissions and security risks.

**Parameters:**
- `role_name` (str): IAM role name
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "role_name": "MyAppRole",
  "role_arn": "arn:aws:iam::123456789:role/MyAppRole",
  "attached_policies": [
    {
      "policy_name": "MyPolicy",
      "policy_arn": "arn:aws:iam::...",
      "policy_type": "Customer Managed"
    }
  ],
  "permissions_summary": {
    "total_statements": 5,
    "services_accessed": ["s3", "dynamodb"],
    "has_admin_access": false,
    "has_wildcard_resources": true,
    "has_wildcard_actions": false
  },
  "risk_assessment": {
    "risk_level": "medium",
    "risk_factors": ["Uses wildcard resources (e.g., Resource: *)"],
    "overpermissive_patterns": ["Wildcard resources detected"]
  },
  "recommendations": ["⚠️ Replace wildcard resources with specific ARNs"]
}
```

**Example:**
```python
analysis = analyze_role("MyAppRole")
```

---

### explain_policy()

Explain IAM policy document in plain English.

**Parameters:**
- `policy_document` (str): JSON policy document
- `aws_client` (AWSClient, optional): Not used, for consistency

**Returns:**
```json
{
  "statements": [
    {
      "effect": "Allow",
      "actions": ["s3:*"],
      "resources": ["*"],
      "explanation": "Allows s3:* on *"
    }
  ],
  "summary": "Policy contains 1 statement(s)",
  "risk_level": "critical"
}
```

**Example:**
```python
policy_json = '{"Statement": [...]}'
explanation = explain_policy(policy_json)
```

---

### find_overpermissive_roles()

Scan all IAM roles for security issues.

**Parameters:**
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "total_roles": 50,
  "scanned_roles": 50,
  "overpermissive_roles": [
    {
      "role_name": "AdminRole",
      "risk_level": "critical",
      "risk_factors": ["Has administrator access (*:*)"]
    }
  ],
  "summary": {
    "critical": 1,
    "high": 3,
    "medium": 12,
    "low": 34
  }
}
```

**Example:**
```python
audit = find_overpermissive_roles()
```

---

## Cost Explorer Tools

### get_cost_and_usage()

Get AWS cost and usage data for a time period.

**Parameters:**
- `start_date` (str, optional): Start date (YYYY-MM-DD)
- `end_date` (str, optional): End date (YYYY-MM-DD)
- `days_back` (int): Days to look back if dates not specified (default: 30)
- `granularity` (str): "DAILY", "MONTHLY", or "HOURLY" (default: "DAILY")
- `metrics` (list[str], optional): Metrics to retrieve
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "time_period": {"start": "2025-10-17", "end": "2025-11-16"},
  "granularity": "DAILY",
  "total_cost": 148.84,
  "currency": "USD",
  "results_by_time": [
    {"date": "2025-11-15", "amount": 4.85, "unit": "USD"}
  ],
  "summary": {
    "total": 148.84,
    "average_daily": 4.96,
    "min_daily": 3.68,
    "max_daily": 5.36
  }
}
```

**Example:**
```python
costs = get_cost_and_usage(days_back=30)
```

---

### get_cost_by_service()

Get cost breakdown by AWS service.

**Parameters:**
- `days_back` (int): Days to look back (default: 30)
- `top_n` (int): Number of top services (default: 10)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "time_period": {"start": "2025-10-17", "end": "2025-11-16"},
  "total_cost": 148.84,
  "currency": "USD",
  "services": [
    {
      "service": "Amazon Relational Database Service",
      "cost": 130.78,
      "percentage": 87.9
    }
  ]
}
```

**Example:**
```python
costs = get_cost_by_service(days_back=30, top_n=5)
```

---

### detect_cost_anomalies()

Detect unusual spending patterns.

**Parameters:**
- `days_back` (int): Days to analyze (default: 30)
- `threshold_percentage` (float): % above average to flag (default: 20.0)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "baseline": {
    "average_daily_cost": 4.96,
    "median_daily_cost": 4.90
  },
  "anomalies": [
    {
      "date": "2025-11-10",
      "cost": 8.50,
      "deviation_percentage": 71.4,
      "severity": "high"
    }
  ],
  "total_anomalies": 1,
  "recommendations": ["⚠️ 1 day(s) with high cost anomalies..."]
}
```

**Example:**
```python
anomalies = detect_cost_anomalies(days_back=30, threshold_percentage=25)
```

---

### get_cost_forecast()

Forecast future AWS costs.

**Parameters:**
- `days_forward` (int): Days to forecast (default: 30, max: 90)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "time_period": {"start": "2025-11-17", "end": "2025-12-17"},
  "forecast": {
    "predicted_cost": 141.23,
    "prediction_interval_lower": 127.11,
    "prediction_interval_upper": 155.35,
    "currency": "USD"
  },
  "daily_forecast": [
    {"date": "2025-11-17", "amount": 4.86}
  ]
}
```

**Example:**
```python
forecast = get_cost_forecast(days_forward=30)
```

---

## Common Patterns

### Error Handling

All tools return structured JSON even on error:

```python
result = get_lambda_logs("non-existent-function")
if "error" in result or "warning" in result:
    print(f"Issue: {result.get('error', result.get('warning'))}")
```

### Custom AWS Client

Use custom profile/region:

```python
from strandkit.core.aws_client import AWSClient

client = AWSClient(profile="prod", region="us-west-2")
logs = get_lambda_logs("my-function", aws_client=client)
```

### Chaining Tools

Combine tools for comprehensive analysis:

```python
# Find errors
errors = get_metric("AWS/Lambda", "Errors", {"FunctionName": "my-api"}, "Sum")

if errors['summary']['max'] > 0:
    # Get error logs
    logs = get_lambda_logs("my-api", filter_pattern="ERROR")

    # Analyze the role
    role = analyze_role("my-api-execution-role")

    # Check costs
    costs = get_cost_by_service(days_back=7)
```

---

## Tool Categories

| Category | Tools | Use Case |
|----------|-------|----------|
| **Monitoring** | get_lambda_logs, get_metric, get_recent_errors | Real-time monitoring and alerting |
| **Analysis** | get_log_insights, detect_cost_anomalies | Deep dive investigations |
| **Security** | analyze_role, explain_policy, find_overpermissive_roles | Security audits and compliance |
| **Cost** | get_cost_and_usage, get_cost_by_service, get_cost_forecast | Budget management and optimization |
| **Infrastructure** | explain_changeset | Change management and deployments |

---

## Best Practices

1. **Start with metrics** before diving into logs (faster)
2. **Use filter patterns** to reduce log volume
3. **Set appropriate time ranges** to avoid timeouts
4. **Cache results** when running repeated queries
5. **Use custom clients** for multi-account/region scenarios
6. **Handle errors gracefully** - all tools return structured errors

---

For more examples, see:
- [examples/basic_usage.py](examples/basic_usage.py)
- [examples/test_new_tools.py](examples/test_new_tools.py)
- [demo_real_insights.py](demo_real_insights.py)
