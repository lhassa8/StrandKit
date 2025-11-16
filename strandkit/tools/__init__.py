"""
AWS Tools for StrandKit.

This package contains Strands-compatible tools for AWS services:
- cloudwatch: CloudWatch Logs and Metrics tools
- cloudwatch_enhanced: Advanced CloudWatch Logs Insights queries
- cloudformation: CloudFormation changeset analysis
- iam: IAM policy analysis and security auditing
- iam_security: IAM security compliance and user auditing
- cost: Cost Explorer for spending analysis and forecasting
- cost_analytics: Advanced cost optimization (RI/SP, rightsizing, budgets)
- cost_waste: Waste detection (zombie resources, idle instances, etc.)
- ec2: EC2 instance and security group analysis
- s3: S3 bucket security and cost optimization

All tools follow consistent patterns:
- Accept simple, well-typed parameters
- Return structured JSON with consistent keys
- Handle pagination automatically
- Include clear error messages
"""

from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
from strandkit.tools.cloudwatch_enhanced import get_log_insights, get_recent_errors
from strandkit.tools.cloudformation import explain_changeset
from strandkit.tools.iam import analyze_role, explain_policy, find_overpermissive_roles
from strandkit.tools.iam_security import (
    analyze_iam_users,
    analyze_access_keys,
    analyze_mfa_compliance,
    analyze_password_policy,
    find_cross_account_access,
    detect_privilege_escalation_paths,
    analyze_unused_permissions,
    get_iam_credential_report
)
from strandkit.tools.cost import (
    get_cost_and_usage,
    get_cost_by_service,
    detect_cost_anomalies,
    get_cost_forecast
)
from strandkit.tools.cost_analytics import (
    get_budget_status,
    analyze_reserved_instances,
    analyze_savings_plans,
    get_rightsizing_recommendations,
    analyze_commitment_savings,
    find_cost_optimization_opportunities
)
from strandkit.tools.cost_waste import (
    find_zombie_resources,
    analyze_idle_resources,
    analyze_snapshot_waste,
    analyze_data_transfer_costs,
    get_cost_allocation_tags
)
from strandkit.tools.ec2 import (
    analyze_ec2_instance,
    get_ec2_inventory,
    find_unused_resources,
    analyze_security_group,
    find_overpermissive_security_groups
)
from strandkit.tools.s3 import (
    analyze_s3_bucket,
    find_public_buckets,
    get_s3_cost_analysis,
    analyze_bucket_access,
    find_unused_buckets
)
from strandkit.tools.ebs import (
    analyze_ebs_volumes,
    analyze_ebs_snapshots_lifecycle,
    get_ebs_iops_recommendations,
    analyze_ebs_encryption,
    find_ebs_volume_anomalies,
    analyze_ami_usage
)

__all__ = [
    # CloudWatch
    "get_lambda_logs",
    "get_metric",
    "get_log_insights",
    "get_recent_errors",
    # CloudFormation
    "explain_changeset",
    # IAM
    "analyze_role",
    "explain_policy",
    "find_overpermissive_roles",
    # IAM Security
    "analyze_iam_users",
    "analyze_access_keys",
    "analyze_mfa_compliance",
    "analyze_password_policy",
    "find_cross_account_access",
    "detect_privilege_escalation_paths",
    "analyze_unused_permissions",
    "get_iam_credential_report",
    # Cost
    "get_cost_and_usage",
    "get_cost_by_service",
    "detect_cost_anomalies",
    "get_cost_forecast",
    # Cost Analytics
    "get_budget_status",
    "analyze_reserved_instances",
    "analyze_savings_plans",
    "get_rightsizing_recommendations",
    "analyze_commitment_savings",
    "find_cost_optimization_opportunities",
    # Cost Waste Detection
    "find_zombie_resources",
    "analyze_idle_resources",
    "analyze_snapshot_waste",
    "analyze_data_transfer_costs",
    "get_cost_allocation_tags",
    # EC2
    "analyze_ec2_instance",
    "get_ec2_inventory",
    "find_unused_resources",
    "analyze_security_group",
    "find_overpermissive_security_groups",
    # S3
    "analyze_s3_bucket",
    "find_public_buckets",
    "get_s3_cost_analysis",
    "analyze_bucket_access",
    "find_unused_buckets",
    # EBS
    "analyze_ebs_volumes",
    "analyze_ebs_snapshots_lifecycle",
    "get_ebs_iops_recommendations",
    "analyze_ebs_encryption",
    "find_ebs_volume_anomalies",
    "analyze_ami_usage",
    # S3 Advanced
    "analyze_s3_storage_classes",
    "analyze_s3_lifecycle_policies",
    "find_s3_versioning_waste",
    "find_incomplete_multipart_uploads",
    "analyze_s3_replication",
    "analyze_s3_request_costs",
    "analyze_large_s3_objects",
]
from strandkit.tools.s3_advanced import (
    analyze_s3_storage_classes,
    analyze_s3_lifecycle_policies,
    find_s3_versioning_waste,
    find_incomplete_multipart_uploads,
    analyze_s3_replication,
    analyze_s3_request_costs,
    analyze_large_s3_objects
)
