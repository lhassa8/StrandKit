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

## EC2 & Compute Tools

### analyze_ec2_instance()

Perform comprehensive analysis of an EC2 instance.

**Parameters:**
- `instance_id` (str): EC2 instance ID (e.g., "i-1234567890abcdef0")
- `include_metrics` (bool): Whether to fetch CloudWatch metrics (default: True)
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "instance_id": "i-1234567890abcdef0",
  "instance_details": {
    "instance_id": "i-1234567890abcdef0",
    "instance_type": "t3.medium",
    "state": "running",
    "launch_time": "2025-01-15T10:30:00Z",
    "uptime_days": 30,
    "availability_zone": "us-east-1a",
    "private_ip": "10.0.1.50",
    "public_ip": "54.123.45.67"
  },
  "security_groups": [
    {
      "group_id": "sg-abc123",
      "group_name": "web-servers",
      "ingress_rules_count": 3,
      "egress_rules_count": 1
    }
  ],
  "volumes": [
    {
      "volume_id": "vol-xyz789",
      "device_name": "/dev/xvda",
      "size_gb": 100,
      "volume_type": "gp3",
      "encrypted": true,
      "state": "in-use"
    }
  ],
  "cost_estimate": {
    "monthly_cost": 45.50,
    "instance_cost": 35.50,
    "storage_cost": 10.00
  },
  "metrics": {
    "cpu_utilization": {
      "average": 12.5,
      "maximum": 45.2
    }
  },
  "health_check": {
    "health_status": "healthy",
    "issues": [],
    "warnings": []
  },
  "recommendations": [
    "✅ Instance configuration looks good"
  ]
}
```

**Example:**
```python
from strandkit import analyze_ec2_instance

analysis = analyze_ec2_instance("i-1234567890abcdef0")
print(f"Monthly cost: ${analysis['cost_estimate']['monthly_cost']:.2f}")
print(f"CPU average: {analysis['metrics']['cpu_utilization']['average']:.1f}%")
```

---

### get_ec2_inventory()

Get comprehensive inventory of all EC2 instances.

**Parameters:**
- `filters` (dict, optional): EC2 filters (e.g., {"instance-state-name": ["running"]})
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "instances": [
    {
      "instance_id": "i-abc123",
      "name": "web-server-1",
      "instance_type": "t3.medium",
      "state": "running",
      "uptime_days": 45,
      "private_ip": "10.0.1.10",
      "availability_zone": "us-east-1a",
      "estimated_monthly_cost": 35.50
    }
  ],
  "summary": {
    "total_instances": 10,
    "by_state": {
      "running": 8,
      "stopped": 2
    },
    "by_type": {
      "t3.medium": 6,
      "t3.large": 4
    },
    "by_az": {
      "us-east-1a": 5,
      "us-east-1b": 5
    }
  },
  "total_monthly_cost": 355.00
}
```

**Example:**
```python
from strandkit import get_ec2_inventory

# Get all running instances
inventory = get_ec2_inventory(filters={"instance-state-name": ["running"]})
print(f"Running instances: {inventory['summary']['by_state']['running']}")
print(f"Total monthly cost: ${inventory['total_monthly_cost']:.2f}")
```

---

### find_unused_resources()

Find unused or underutilized EC2 resources to reduce costs.

**Parameters:**
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "stopped_instances": [
    {
      "instance_id": "i-xyz789",
      "name": "old-test-server",
      "instance_type": "t3.large",
      "availability_zone": "us-east-1a"
    }
  ],
  "stopped_instances_count": 3,
  "unattached_volumes": [
    {
      "volume_id": "vol-abc123",
      "size_gb": 100,
      "volume_type": "gp2",
      "availability_zone": "us-east-1a",
      "estimated_monthly_cost": 10.00
    }
  ],
  "unattached_volumes_count": 5,
  "unused_elastic_ips": [
    {
      "allocation_id": "eipalloc-abc123",
      "public_ip": "54.123.45.67",
      "estimated_monthly_cost": 3.65
    }
  ],
  "unused_elastic_ips_count": 2,
  "old_snapshots": [
    {
      "snapshot_id": "snap-xyz789",
      "size_gb": 50,
      "age_days": 180,
      "estimated_monthly_cost": 2.50
    }
  ],
  "old_snapshots_count": 15,
  "total_potential_savings": 125.50,
  "breakdown": {
    "volumes": 50.00,
    "elastic_ips": 7.30,
    "snapshots": 68.20
  },
  "recommendations": [
    "💰 5 unattached volume(s) found - potential savings: $50.00/month"
  ]
}
```

**Example:**
```python
from strandkit import find_unused_resources

unused = find_unused_resources()
print(f"Potential monthly savings: ${unused['total_potential_savings']:.2f}")
print(f"Stopped instances: {unused['stopped_instances_count']}")
print(f"Unattached volumes: {unused['unattached_volumes_count']}")
```

---

### analyze_security_group()

Analyze security group rules and assess security risks.

**Parameters:**
- `group_id` (str): Security group ID (e.g., "sg-1234567890abcdef0")
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "group_id": "sg-abc123",
  "group_details": {
    "group_id": "sg-abc123",
    "group_name": "web-servers",
    "description": "Security group for web servers",
    "vpc_id": "vpc-xyz789"
  },
  "ingress_rules": [
    {
      "direction": "ingress",
      "protocol": "tcp",
      "from_port": 443,
      "to_port": 443,
      "sources": [
        {"type": "cidr", "value": "0.0.0.0/0"}
      ],
      "risk_level": "high",
      "risk_reason": "Public access to port 443"
    }
  ],
  "ingress_rules_count": 3,
  "egress_rules_count": 1,
  "risk_assessment": {
    "risk_level": "high",
    "risk_factors": [
      "Public access to port 443"
    ]
  },
  "attached_resources": {
    "instances": 5
  },
  "recommendations": [
    "🔒 Restrict public access (0.0.0.0/0) to specific IP ranges where possible"
  ]
}
```

**Example:**
```python
from strandkit import analyze_security_group

sg = analyze_security_group("sg-1234567890abcdef0")
print(f"Risk level: {sg['risk_assessment']['risk_level']}")
print(f"Attached instances: {sg['attached_resources']['instances']}")
```

---

### find_overpermissive_security_groups()

Scan all security groups for overly permissive rules.

**Parameters:**
- `aws_client` (AWSClient, optional): Custom AWS client

**Returns:**
```json
{
  "security_groups": [
    {
      "group_id": "sg-abc123",
      "group_name": "ssh-access",
      "risk_level": "critical",
      "risk_factors": [
        "Allows SSH (22) from 0.0.0.0/0"
      ],
      "ingress_rules_count": 1,
      "is_unused": false
    }
  ],
  "risky_groups": [
    {
      "group_id": "sg-abc123",
      "group_name": "ssh-access",
      "risk_level": "critical",
      "risk_factors": [
        "Allows SSH (22) from 0.0.0.0/0"
      ]
    }
  ],
  "unused_groups": [],
  "summary": {
    "total_groups": 25,
    "critical": 2,
    "high": 5,
    "medium": 8,
    "low": 10,
    "unused": 3
  },
  "recommendations": [
    "🔴 URGENT: 2 security group(s) with CRITICAL risk - immediate action required",
    "⚠️ 5 security group(s) with HIGH risk - review and restrict access"
  ]
}
```

**Example:**
```python
from strandkit import find_overpermissive_security_groups

scan = find_overpermissive_security_groups()
print(f"Total groups: {scan['summary']['total_groups']}")
print(f"Critical risks: {scan['summary']['critical']}")

# Review critical groups
for sg in scan['risky_groups']:
    if sg['risk_level'] == 'critical':
        print(f"🔴 {sg['group_name']}: {sg['risk_factors']}")
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
| **Security** | analyze_role, explain_policy, find_overpermissive_roles, analyze_security_group, find_overpermissive_security_groups | Security audits and compliance |
| **Cost** | get_cost_and_usage, get_cost_by_service, get_cost_forecast, find_unused_resources | Budget management and optimization |
| **Infrastructure** | explain_changeset, analyze_ec2_instance, get_ec2_inventory | Change management, deployments, and inventory |

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
