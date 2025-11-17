# StrandKit Tools Reference

Complete API reference for all **60 AWS tools** in StrandKit v2.0.0.

All tools are decorated with `@tool` for AWS Strands Agents integration and can also be used standalone.

---

## Table of Contents

- [CloudWatch (4 tools)](#cloudwatch-tools)
- [CloudFormation (1 tool)](#cloudformation-tools)
- [IAM (3 tools)](#iam-tools)
- [IAM Security (8 tools)](#iam-security-tools)
- [Cost Explorer (4 tools)](#cost-explorer-tools)
- [Cost Analytics (6 tools)](#cost-analytics-tools)
- [Cost Waste (5 tools)](#cost-waste-tools)
- [EC2 (5 tools)](#ec2-tools)
- [EC2 Advanced (4 tools)](#ec2-advanced-tools)
- [S3 (5 tools)](#s3-tools)
- [S3 Advanced (7 tools)](#s3-advanced-tools)
- [EBS (6 tools)](#ebs-tools)

---

## CloudWatch Tools

### get_lambda_logs()

Retrieve CloudWatch logs for a Lambda function.

```python
from strandkit import get_lambda_logs

logs = get_lambda_logs(
    function_name="my-function",
    start_minutes=60,
    filter_pattern="ERROR",  # optional
    limit=100
)
```

**Returns:** Log events with timestamps, error count, and time range.

### get_metric()

Query CloudWatch metrics with statistics.

```python
from strandkit import get_metric

metrics = get_metric(
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": "my-api"},
    statistic="Sum",  # Average, Sum, Maximum, Minimum
    period=300,
    start_minutes=120
)
```

**Returns:** Datapoints with summary statistics (min, max, avg, count).

### get_log_insights()

Run advanced CloudWatch Logs Insights queries.

```python
from strandkit import get_log_insights

results = get_log_insights(
    log_group_names=["/aws/lambda/my-function"],
    query_string="""
        fields @timestamp, @message
        | filter @message like /ERROR/
        | stats count() by bin(5m)
    """,
    start_minutes=120
)
```

**Returns:** Query results with statistics (records scanned/matched).

### get_recent_errors()

Quick helper to find recent errors across log groups.

```python
from strandkit import get_recent_errors

errors = get_recent_errors(
    log_group_pattern="/aws/lambda/",
    start_minutes=60,
    limit=50
)
```

**Returns:** Error events from all matching log groups.

---

## CloudFormation Tools

### explain_changeset()

Analyze CloudFormation changeset with risk assessment.

```python
from strandkit import explain_changeset

analysis = explain_changeset(
    changeset_name="my-changeset",
    stack_name="my-stack"
)
```

**Returns:** Changes with risk levels, recommendations, and replacement info.

---

## IAM Tools

### analyze_role()

Analyze IAM role permissions and security risks.

```python
from strandkit import analyze_role

role = analyze_role("MyAppRole")
```

**Returns:** Attached policies, permissions summary, risk assessment, and recommendations.

### explain_policy()

Explain IAM policy document in plain English.

```python
from strandkit import explain_policy

policy_json = '{"Statement": [...]}'
explanation = explain_policy(policy_json)
```

**Returns:** Statement-by-statement explanation with overall risk level.

### find_overpermissive_roles()

Scan all IAM roles for security issues.

```python
from strandkit import find_overpermissive_roles

audit = find_overpermissive_roles()
```

**Returns:** List of risky roles with severity breakdown (critical/high/medium/low).

---

## IAM Security Tools

### analyze_iam_users()

Analyze all IAM users for security compliance.

```python
from strandkit import analyze_iam_users

users = analyze_iam_users()
```

**Returns:** User details, access key age, password policy compliance, MFA status.

### analyze_access_keys()

Analyze IAM access keys for rotation and usage.

```python
from strandkit import analyze_access_keys

keys = analyze_access_keys(max_age_days=90)
```

**Returns:** Access keys older than threshold, last used dates, rotation recommendations.

### analyze_mfa_compliance()

Check MFA compliance across all users.

```python
from strandkit import analyze_mfa_compliance

mfa = analyze_mfa_compliance()
```

**Returns:** Users without MFA, compliance rate, security recommendations.

### analyze_password_policy()

Analyze account password policy.

```python
from strandkit import analyze_password_policy

policy = analyze_password_policy()
```

**Returns:** Current settings vs. best practices, compliance score, recommendations.

### find_cross_account_access()

Find IAM roles with cross-account access.

```python
from strandkit import find_cross_account_access

cross_account = find_cross_account_access()
```

**Returns:** Roles with external account access, trust relationships, risk assessment.

### detect_privilege_escalation_paths()

Detect potential privilege escalation risks.

```python
from strandkit import detect_privilege_escalation_paths

escalation = detect_privilege_escalation_paths()
```

**Returns:** Roles/users with dangerous permission combinations.

### analyze_unused_permissions()

Find unused IAM permissions (requires IAM Access Analyzer).

```python
from strandkit import analyze_unused_permissions

unused = analyze_unused_permissions(days_back=90)
```

**Returns:** Permissions granted but not used, optimization opportunities.

### get_iam_credential_report()

Get IAM credential report with security insights.

```python
from strandkit import get_iam_credential_report

report = get_iam_credential_report()
```

**Returns:** Comprehensive credential report with password/key ages, MFA status.

---

## Cost Explorer Tools

### get_cost_and_usage()

Get AWS cost and usage data for a time period.

```python
from strandkit import get_cost_and_usage

costs = get_cost_and_usage(
    days_back=30,
    granularity="DAILY"  # DAILY, MONTHLY, HOURLY
)
```

**Returns:** Total cost, daily breakdown, summary statistics.

### get_cost_by_service()

Get cost breakdown by AWS service.

```python
from strandkit import get_cost_by_service

costs = get_cost_by_service(
    days_back=30,
    top_n=10
)
```

**Returns:** Services ranked by cost with percentages.

### detect_cost_anomalies()

Detect unusual spending patterns.

```python
from strandkit import detect_cost_anomalies

anomalies = detect_cost_anomalies(
    days_back=30,
    threshold_percentage=20.0
)
```

**Returns:** Days with unusual costs, deviation percentages, severity levels.

### get_cost_forecast()

Forecast future AWS costs.

```python
from strandkit import get_cost_forecast

forecast = get_cost_forecast(days_forward=30)  # max 90
```

**Returns:** Predicted costs with confidence intervals.

---

## Cost Analytics Tools

### get_budget_status()

Get AWS Budget status and alerts.

```python
from strandkit import get_budget_status

budgets = get_budget_status()
```

**Returns:** All budgets with current spend vs. limit, forecast status.

### analyze_reserved_instances()

Analyze Reserved Instance utilization and coverage.

```python
from strandkit import analyze_reserved_instances

ri = analyze_reserved_instances(days_back=30)
```

**Returns:** RI utilization rates, coverage gaps, savings opportunities.

### analyze_savings_plans()

Analyze Savings Plans utilization and recommendations.

```python
from strandkit import analyze_savings_plans

savings = analyze_savings_plans(days_back=30)
```

**Returns:** Savings Plans utilization, coverage, potential savings.

### get_rightsizing_recommendations()

Get EC2 rightsizing recommendations from Cost Explorer.

```python
from strandkit import get_rightsizing_recommendations

recommendations = get_rightsizing_recommendations()
```

**Returns:** Under/over-provisioned instances with cost savings.

### analyze_commitment_savings()

Analyze savings from commitments (RI + Savings Plans).

```python
from strandkit import analyze_commitment_savings

commitments = analyze_commitment_savings(days_back=30)
```

**Returns:** Total savings, utilization rates, recommendations.

### find_cost_optimization_opportunities()

Find comprehensive cost optimization opportunities.

```python
from strandkit import find_cost_optimization_opportunities

opportunities = find_cost_optimization_opportunities()
```

**Returns:** Rightsizing, idle resources, commitment recommendations.

---

## Cost Waste Tools

### find_zombie_resources()

Find unused resources across AWS services.

```python
from strandkit import find_zombie_resources

zombies = find_zombie_resources()
```

**Returns:** Unattached volumes, old snapshots, unused IPs, stopped instances with costs.

### analyze_idle_resources()

Find idle EC2 instances and RDS databases.

```python
from strandkit import analyze_idle_resources

idle = analyze_idle_resources(
    cpu_threshold=5.0,
    days_back=7
)
```

**Returns:** Resources with low CPU utilization, potential savings.

### analyze_snapshot_waste()

Analyze EBS snapshot waste (old/orphaned snapshots).

```python
from strandkit import analyze_snapshot_waste

snapshots = analyze_snapshot_waste(
    age_threshold_days=90,
    include_ami_snapshots=False
)
```

**Returns:** Old snapshots, orphaned snapshots, potential savings.

### analyze_data_transfer_costs()

Analyze data transfer costs between regions/AZs.

```python
from strandkit import analyze_data_transfer_costs

transfer = analyze_data_transfer_costs(days_back=30)
```

**Returns:** Data transfer costs by type, optimization recommendations.

### get_cost_allocation_tags()

Analyze cost allocation tag coverage.

```python
from strandkit import get_cost_allocation_tags

tags = get_cost_allocation_tags()
```

**Returns:** Resources with/without tags, coverage percentages, untagged costs.

---

## EC2 Tools

### analyze_ec2_instance()

Comprehensive analysis of an EC2 instance.

```python
from strandkit import analyze_ec2_instance

analysis = analyze_ec2_instance(
    instance_id="i-1234567890abcdef0",
    include_metrics=True
)
```

**Returns:** Instance details, volumes, security groups, cost estimate, metrics, health check.

### get_ec2_inventory()

Get comprehensive EC2 instance inventory.

```python
from strandkit import get_ec2_inventory

inventory = get_ec2_inventory(
    filters={"instance-state-name": ["running"]}
)
```

**Returns:** All instances with summary by state/type/AZ, total monthly cost.

### find_unused_resources()

Find unused EC2 resources (stopped instances, unattached volumes, etc.).

```python
from strandkit import find_unused_resources

unused = find_unused_resources()
```

**Returns:** Stopped instances, unattached volumes/IPs, old snapshots with savings.

### analyze_security_group()

Analyze security group rules and assess risks.

```python
from strandkit import analyze_security_group

sg = analyze_security_group("sg-1234567890abcdef0")
```

**Returns:** Rules with risk assessment, attached resources, recommendations.

### find_overpermissive_security_groups()

Scan all security groups for overly permissive rules.

```python
from strandkit import find_overpermissive_security_groups

scan = find_overpermissive_security_groups()
```

**Returns:** Risky groups by severity, unused groups, security recommendations.

---

## EC2 Advanced Tools

### analyze_ec2_performance()

Analyze EC2 instance performance metrics.

```python
from strandkit import analyze_ec2_performance

perf = analyze_ec2_performance(
    instance_id="i-1234567890abcdef0",
    days_back=7
)
```

**Returns:** CPU, memory, disk, network metrics with bottleneck analysis.

### analyze_auto_scaling_groups()

Analyze Auto Scaling Groups efficiency.

```python
from strandkit import analyze_auto_scaling_groups

asg = analyze_auto_scaling_groups()
```

**Returns:** ASG details, scaling history, efficiency metrics, recommendations.

### analyze_load_balancers()

Analyze Load Balancer health and performance.

```python
from strandkit import analyze_load_balancers

lb = analyze_load_balancers()
```

**Returns:** LB details, target health, metrics, cost analysis.

### get_ec2_spot_recommendations()

Get EC2 Spot instance recommendations.

```python
from strandkit import get_ec2_spot_recommendations

spot = get_ec2_spot_recommendations()
```

**Returns:** Instances suitable for Spot, potential savings, interruption risk.

---

## S3 Tools

### analyze_s3_bucket()

Comprehensive S3 bucket analysis.

```python
from strandkit import analyze_s3_bucket

bucket = analyze_s3_bucket("my-bucket")
```

**Returns:** Bucket details, size, object count, versioning, encryption, public access.

### find_public_buckets()

Find S3 buckets with public access.

```python
from strandkit import find_public_buckets

public = find_public_buckets()
```

**Returns:** Buckets with public access, risk levels, remediation steps.

### get_s3_cost_analysis()

Analyze S3 costs by bucket.

```python
from strandkit import get_s3_cost_analysis

costs = get_s3_cost_analysis(days_back=30)
```

**Returns:** Per-bucket costs, storage class breakdown, optimization opportunities.

### analyze_bucket_access()

Analyze S3 bucket access patterns and permissions.

```python
from strandkit import analyze_bucket_access

access = analyze_bucket_access("my-bucket")
```

**Returns:** Bucket policy, ACLs, public access blocks, risk assessment.

### find_unused_buckets()

Find S3 buckets with no recent access.

```python
from strandkit import find_unused_buckets

unused = find_unused_buckets(days_threshold=90)
```

**Returns:** Buckets with no recent uploads/downloads, costs, deletion candidates.

---

## S3 Advanced Tools

### analyze_s3_storage_classes()

Analyze S3 storage class distribution and optimization.

```python
from strandkit import analyze_s3_storage_classes

storage = analyze_s3_storage_classes("my-bucket")
```

**Returns:** Objects by storage class, lifecycle rule recommendations, potential savings.

### analyze_s3_lifecycle_policies()

Analyze S3 lifecycle policies.

```python
from strandkit import analyze_s3_lifecycle_policies

lifecycle = analyze_s3_lifecycle_policies("my-bucket")
```

**Returns:** Current policies, coverage gaps, optimization recommendations.

### find_s3_versioning_waste()

Find S3 buckets wasting storage on old versions.

```python
from strandkit import find_s3_versioning_waste

versioning = find_s3_versioning_waste()
```

**Returns:** Buckets with excessive versions, costs, cleanup recommendations.

### find_incomplete_multipart_uploads()

Find incomplete S3 multipart uploads.

```python
from strandkit import find_incomplete_multipart_uploads

uploads = find_incomplete_multipart_uploads()
```

**Returns:** Incomplete uploads by bucket, storage waste, cleanup recommendations.

### analyze_s3_replication()

Analyze S3 replication configuration and costs.

```python
from strandkit import analyze_s3_replication

replication = analyze_s3_replication()
```

**Returns:** Replication rules, costs, efficiency metrics.

### analyze_s3_request_costs()

Analyze S3 request costs (GET, PUT, etc.).

```python
from strandkit import analyze_s3_request_costs

requests = analyze_s3_request_costs(days_back=30)
```

**Returns:** Request counts by type, costs, optimization recommendations.

### analyze_large_s3_objects()

Find large S3 objects consuming storage.

```python
from strandkit import analyze_large_s3_objects

large = analyze_large_s3_objects(
    min_size_mb=100,
    bucket_name="my-bucket"  # optional
)
```

**Returns:** Large objects ranked by size, storage costs, archival candidates.

---

## EBS Tools

### analyze_ebs_volumes()

Analyze EBS volumes for optimization.

```python
from strandkit import analyze_ebs_volumes

volumes = analyze_ebs_volumes()
```

**Returns:** Volume details, costs, underutilized volumes, rightsizing recommendations.

### analyze_ebs_snapshots_lifecycle()

Analyze EBS snapshot lifecycle and retention.

```python
from strandkit import analyze_ebs_snapshots_lifecycle

snapshots = analyze_ebs_snapshots_lifecycle()
```

**Returns:** Snapshots by age, retention analysis, cleanup recommendations.

### get_ebs_iops_recommendations()

Get IOPS optimization recommendations for EBS.

```python
from strandkit import get_ebs_iops_recommendations

iops = get_ebs_iops_recommendations()
```

**Returns:** Over/under-provisioned IOPS, potential savings.

### analyze_ebs_encryption()

Analyze EBS encryption compliance.

```python
from strandkit import analyze_ebs_encryption

encryption = analyze_ebs_encryption()
```

**Returns:** Encrypted vs. unencrypted volumes, compliance gaps, remediation.

### find_ebs_volume_anomalies()

Find EBS volumes with unusual characteristics.

```python
from strandkit import find_ebs_volume_anomalies

anomalies = find_ebs_volume_anomalies()
```

**Returns:** Oversized volumes, high-cost volumes, unusual IOPS configurations.

### analyze_ami_usage()

Analyze AMI usage and cleanup opportunities.

```python
from strandkit import analyze_ami_usage

amis = analyze_ami_usage(age_threshold_days=180)
```

**Returns:** Old/unused AMIs, associated snapshots, storage costs, cleanup recommendations.

---

## Usage Patterns

### With Strands Agents

```python
from strands import Agent
from strandkit.strands import get_all_tools

agent = Agent(
    model="anthropic.claude-3-5-haiku",
    tools=get_all_tools()
)

response = agent("Find overpermissive IAM roles and security groups")
```

### By Category

```python
from strandkit.strands import get_tools_by_category

cost_tools = get_tools_by_category('cost')
security_tools = get_tools_by_category('iam_security')
```

### Standalone

```python
from strandkit import find_overpermissive_roles, get_cost_by_service

roles = find_overpermissive_roles()
costs = get_cost_by_service(days_back=30)
```

### Custom AWS Client

```python
from strandkit.core.aws_client import AWSClient
from strandkit import get_cost_by_service

aws = AWSClient(profile="prod", region="us-west-2")
costs = get_cost_by_service(days_back=30, aws_client=aws)
```

---

## Tool Categories

| Category | Count | Purpose |
|----------|-------|---------|
| `cloudwatch` | 4 | CloudWatch Logs and Metrics |
| `cloudformation` | 1 | CloudFormation changesets |
| `iam` | 3 | IAM role and policy analysis |
| `iam_security` | 8 | IAM security auditing |
| `cost` | 4 | Cost Explorer basics |
| `cost_analytics` | 6 | Advanced cost analysis |
| `cost_waste` | 5 | Waste detection |
| `ec2` | 5 | EC2 instance analysis |
| `ec2_advanced` | 4 | EC2 performance/scaling |
| `s3` | 5 | S3 bucket analysis |
| `s3_advanced` | 7 | S3 optimization |
| `ebs` | 6 | EBS volume optimization |

---

## Error Handling

All tools return structured JSON, even on errors:

```python
result = analyze_ec2_instance("i-nonexistent")

if 'error' in result:
    print(f"Error: {result['error']}")
elif 'warning' in result:
    print(f"Warning: {result['warning']}")
else:
    # Success - use the data
    print(result)
```

---

## Best Practices

1. **Start broad, then narrow**: Use inventory/listing tools before detailed analysis
2. **Cache results**: Store results for repeated analysis
3. **Use filters**: Reduce data volume with appropriate filters
4. **Handle errors**: Always check for 'error' or 'warning' in responses
5. **Custom clients**: Use AWSClient for multi-account/region scenarios
6. **Time ranges**: Adjust `days_back` parameters based on your needs

---

## Examples

See the [examples](examples/) directory:
- `strands_integration.py` - 9 Strands integration patterns
- `basic_usage.py` - Standalone tool usage
- `test_imports.py` - Verify installation

---

## More Information

- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [AWS Strands Docs](https://strandsagents.com/) - Official Strands framework

---

**StrandKit v2.0.0** - 60 AWS tools for building AI agents
