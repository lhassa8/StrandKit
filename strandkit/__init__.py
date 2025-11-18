"""
StrandKit - Companion SDK for AWS Strands Agents

StrandKit is not a new agent framework; it extends AWS Strands by providing:
- AWS-focused tools (CloudWatch, CloudFormation, IAM, EC2, S3, Cost Explorer)
- Prebuilt agent templates (InfraDebuggerAgent, etc.)
- High-level Python APIs that hide Strands boilerplate
- Clean JSON schemas for all tools
- AI-friendly documentation and examples

Example usage:
    >>> from strandkit import InfraDebuggerAgent
    >>> agent = InfraDebuggerAgent(profile="dev", region="us-east-1")
    >>> response = agent.run("Why are errors spiking in the auth service?")
    >>> print(response)

For more information, see: https://github.com/yourusername/strandkit
"""

__version__ = "2.3.0"
__author__ = "Your Name"

# Import main agent templates for easy access
from strandkit.agents.infra_debugger import InfraDebuggerAgent

# Import commonly used tools
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
from strandkit.tools.orchestrators import (
    audit_security,
    optimize_costs,
    diagnose_issue,
    get_aws_overview
)
from strandkit.tools.rds import (
    analyze_rds_instance,
    find_idle_databases,
    analyze_rds_backups,
    get_rds_recommendations,
    find_rds_security_issues
)
from strandkit.tools.vpc import (
    find_unused_nat_gateways,
    analyze_vpc_configuration,
    analyze_data_transfer_costs,
    analyze_vpc_endpoints,
    find_network_bottlenecks
)
from strandkit.tools.bedrock import (
    analyze_bedrock_usage,
    list_available_models,
    get_model_details,
    analyze_model_performance,
    compare_models,
    get_model_invocation_logs
)

__all__ = [
    # Agents
    "InfraDebuggerAgent",
    # CloudWatch tools
    "get_lambda_logs",
    "get_metric",
    "get_log_insights",
    "get_recent_errors",
    # CloudFormation tools
    "explain_changeset",
    # IAM tools
    "analyze_role",
    "explain_policy",
    "find_overpermissive_roles",
    # IAM Security tools
    "analyze_iam_users",
    "analyze_access_keys",
    "analyze_mfa_compliance",
    "analyze_password_policy",
    "find_cross_account_access",
    "detect_privilege_escalation_paths",
    "analyze_unused_permissions",
    "get_iam_credential_report",
    # Cost tools
    "get_cost_and_usage",
    "get_cost_by_service",
    "detect_cost_anomalies",
    "get_cost_forecast",
    # Cost Analytics tools
    "get_budget_status",
    "analyze_reserved_instances",
    "analyze_savings_plans",
    "get_rightsizing_recommendations",
    "analyze_commitment_savings",
    "find_cost_optimization_opportunities",
    # Cost Waste Detection tools
    "find_zombie_resources",
    "analyze_idle_resources",
    "analyze_snapshot_waste",
    "analyze_data_transfer_costs",
    "get_cost_allocation_tags",
    # EC2 tools
    "analyze_ec2_instance",
    "get_ec2_inventory",
    "find_unused_resources",
    "analyze_security_group",
    "find_overpermissive_security_groups",
    # S3 tools
    "analyze_s3_bucket",
    "find_public_buckets",
    "get_s3_cost_analysis",
    "analyze_bucket_access",
    "find_unused_buckets",
    # EBS tools
    "analyze_ebs_volumes",
    "analyze_ebs_snapshots_lifecycle",
    "get_ebs_iops_recommendations",
    "analyze_ebs_encryption",
    "find_ebs_volume_anomalies",
    "analyze_ami_usage",
    # S3 Advanced tools
    "analyze_s3_storage_classes",
    "analyze_s3_lifecycle_policies",
    "find_s3_versioning_waste",
    "find_incomplete_multipart_uploads",
    "analyze_s3_replication",
    "analyze_s3_request_costs",
    "analyze_large_s3_objects",
    # EC2 Advanced tools
    "analyze_ec2_performance",
    "analyze_auto_scaling_groups",
    "analyze_load_balancers",
    "get_ec2_spot_recommendations",
    # Orchestrator tools (high-level)
    "audit_security",
    "optimize_costs",
    "diagnose_issue",
    "get_aws_overview",
    # RDS/Database tools
    "analyze_rds_instance",
    "find_idle_databases",
    "analyze_rds_backups",
    "get_rds_recommendations",
    "find_rds_security_issues",
    # VPC/Networking tools
    "find_unused_nat_gateways",
    "analyze_vpc_configuration",
    "analyze_data_transfer_costs",
    "analyze_vpc_endpoints",
    "find_network_bottlenecks",
    # Bedrock/AI tools
    "analyze_bedrock_usage",
    "list_available_models",
    "get_model_details",
    "analyze_model_performance",
    "compare_models",
    "get_model_invocation_logs",
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
from strandkit.tools.ec2_advanced import (
    analyze_ec2_performance,
    analyze_auto_scaling_groups,
    analyze_load_balancers,
    get_ec2_spot_recommendations
)
