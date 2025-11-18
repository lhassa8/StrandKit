"""
Tool registry for AWS Strands Agents integration.

This module provides simple functions to get StrandKit tools for use with
AWS Strands Agents. All tools are @tool-decorated functions ready to be
passed directly to Strands Agent instances.

Example:
    from strands import Agent
    from strandkit.strands import get_all_tools

    agent = Agent(tools=get_all_tools())

For v2.0.0: This module has been simplified to return decorated functions
instead of schema dictionaries, for proper Strands integration.
"""

from typing import List, Any


def get_all_tools() -> List[Any]:
    """
    Get all 72 StrandKit tools as @tool-decorated functions.

    Returns list of functions ready to pass to Strands Agent.

    Usage:
        from strands import Agent
        from strandkit.strands import get_all_tools

        agent = Agent(
            model="anthropic.claude-3-5-haiku",
            tools=get_all_tools()
        )

    Returns:
        List of 64 @tool-decorated functions organized by category:
        - Orchestrators: 4 tools (high-level)
        - CloudWatch: 4 tools
        - CloudFormation: 1 tool
        - IAM: 3 tools
        - IAM Security: 8 tools
        - Cost: 4 tools
        - Cost Analytics: 6 tools
        - Cost Waste: 5 tools
        - EC2: 5 tools
        - EC2 Advanced: 4 tools
        - S3: 5 tools
        - S3 Advanced: 7 tools
        - EBS: 6 tools
    """
    # Import all tool modules
    from strandkit.tools import (
        # CloudWatch modules
        cloudwatch, cloudwatch_enhanced,
        # Other modules
        cloudformation, iam, iam_security,
        cost, cost_analytics, cost_waste,
        ec2, ec2_advanced, s3, s3_advanced, ebs,
        # Database and networking
        rds, vpc,
        # Orchestrator module
        orchestrators
    )

    return [
        # Orchestrators (4 high-level tools)
        orchestrators.audit_security,
        orchestrators.optimize_costs,
        orchestrators.diagnose_issue,
        orchestrators.get_aws_overview,

        # CloudWatch (4 tools)
        cloudwatch.get_lambda_logs,
        cloudwatch.get_metric,
        cloudwatch_enhanced.get_log_insights,
        cloudwatch_enhanced.get_recent_errors,

        # CloudFormation (1 tool)
        cloudformation.explain_changeset,

        # IAM (3 tools)
        iam.analyze_role,
        iam.explain_policy,
        iam.find_overpermissive_roles,

        # IAM Security (8 tools)
        iam_security.analyze_iam_users,
        iam_security.analyze_access_keys,
        iam_security.analyze_mfa_compliance,
        iam_security.analyze_password_policy,
        iam_security.find_cross_account_access,
        iam_security.detect_privilege_escalation_paths,
        iam_security.analyze_unused_permissions,
        iam_security.get_iam_credential_report,

        # Cost (4 tools)
        cost.get_cost_and_usage,
        cost.get_cost_by_service,
        cost.detect_cost_anomalies,
        cost.get_cost_forecast,

        # Cost Analytics (6 tools)
        cost_analytics.get_budget_status,
        cost_analytics.analyze_reserved_instances,
        cost_analytics.analyze_savings_plans,
        cost_analytics.get_rightsizing_recommendations,
        cost_analytics.analyze_commitment_savings,
        cost_analytics.find_cost_optimization_opportunities,

        # Cost Waste (5 tools)
        cost_waste.find_zombie_resources,
        cost_waste.analyze_idle_resources,
        cost_waste.analyze_snapshot_waste,
        cost_waste.analyze_data_transfer_costs,
        cost_waste.get_cost_allocation_tags,

        # EC2 (5 tools)
        ec2.analyze_ec2_instance,
        ec2.get_ec2_inventory,
        ec2.find_unused_resources,
        ec2.analyze_security_group,
        ec2.find_overpermissive_security_groups,

        # EC2 Advanced (4 tools)
        ec2_advanced.analyze_ec2_performance,
        ec2_advanced.analyze_auto_scaling_groups,
        ec2_advanced.analyze_load_balancers,
        ec2_advanced.get_ec2_spot_recommendations,

        # S3 (5 tools)
        s3.analyze_s3_bucket,
        s3.find_public_buckets,
        s3.get_s3_cost_analysis,
        s3.analyze_bucket_access,
        s3.find_unused_buckets,

        # S3 Advanced (7 tools)
        s3_advanced.analyze_s3_storage_classes,
        s3_advanced.analyze_s3_lifecycle_policies,
        s3_advanced.find_s3_versioning_waste,
        s3_advanced.find_incomplete_multipart_uploads,
        s3_advanced.analyze_s3_replication,
        s3_advanced.analyze_s3_request_costs,
        s3_advanced.analyze_large_s3_objects,

        # EBS (6 tools)
        ebs.analyze_ebs_volumes,
        ebs.analyze_ebs_snapshots_lifecycle,
        ebs.get_ebs_iops_recommendations,
        ebs.analyze_ebs_encryption,
        ebs.find_ebs_volume_anomalies,
        ebs.analyze_ami_usage,

        # RDS (5 tools)
        rds.analyze_rds_instance,
        rds.find_idle_databases,
        rds.analyze_rds_backups,
        rds.get_rds_recommendations,
        rds.find_rds_security_issues,

        # VPC (5 tools)
        vpc.find_unused_nat_gateways,
        vpc.analyze_vpc_configuration,
        vpc.analyze_data_transfer_costs,
        vpc.analyze_vpc_endpoints,
        vpc.find_network_bottlenecks,
    ]


def get_tools_by_category(category: str) -> List[Any]:
    """
    Get tools for a specific category.

    Args:
        category: Tool category name. Available categories:
            - 'orchestrators': High-level composite tools (4 tools)
            - 'cloudwatch': CloudWatch Logs and Metrics (4 tools)
            - 'cloudformation': CloudFormation changesets (1 tool)
            - 'iam': IAM role and policy analysis (3 tools)
            - 'iam_security': IAM security auditing (8 tools)
            - 'cost': Cost Explorer (4 tools)
            - 'cost_analytics': Cost optimization (6 tools)
            - 'cost_waste': Waste detection (5 tools)
            - 'ec2': EC2 instance analysis (5 tools)
            - 'ec2_advanced': EC2 performance/scaling (4 tools)
            - 's3': S3 bucket analysis (5 tools)
            - 's3_advanced': S3 optimization (7 tools)
            - 'ebs': EBS volume optimization (6 tools)
            - 'rds': RDS database analysis (5 tools)
            - 'vpc': VPC networking analysis (5 tools)

    Returns:
        List of @tool-decorated functions for the category

    Usage:
        from strands import Agent
        from strandkit.strands import get_tools_by_category

        # Security-focused agent
        agent = Agent(tools=(
            get_tools_by_category('iam') +
            get_tools_by_category('iam_security') +
            get_tools_by_category('ec2')
        ))

        # Cost optimization agent
        agent = Agent(tools=(
            get_tools_by_category('cost') +
            get_tools_by_category('cost_analytics') +
            get_tools_by_category('cost_waste')
        ))
    """
    # Import modules on-demand
    if category == 'orchestrators':
        from strandkit.tools import orchestrators
        return [
            orchestrators.audit_security,
            orchestrators.optimize_costs,
            orchestrators.diagnose_issue,
            orchestrators.get_aws_overview,
        ]

    elif category == 'cloudwatch':
        from strandkit.tools import cloudwatch, cloudwatch_enhanced
        return [
            cloudwatch.get_lambda_logs,
            cloudwatch.get_metric,
            cloudwatch_enhanced.get_log_insights,
            cloudwatch_enhanced.get_recent_errors,
        ]

    elif category == 'cloudformation':
        from strandkit.tools import cloudformation
        return [cloudformation.explain_changeset]

    elif category == 'iam':
        from strandkit.tools import iam
        return [
            iam.analyze_role,
            iam.explain_policy,
            iam.find_overpermissive_roles,
        ]

    elif category == 'iam_security':
        from strandkit.tools import iam_security
        return [
            iam_security.analyze_iam_users,
            iam_security.analyze_access_keys,
            iam_security.analyze_mfa_compliance,
            iam_security.analyze_password_policy,
            iam_security.find_cross_account_access,
            iam_security.detect_privilege_escalation_paths,
            iam_security.analyze_unused_permissions,
            iam_security.get_iam_credential_report,
        ]

    elif category == 'cost':
        from strandkit.tools import cost
        return [
            cost.get_cost_and_usage,
            cost.get_cost_by_service,
            cost.detect_cost_anomalies,
            cost.get_cost_forecast,
        ]

    elif category == 'cost_analytics':
        from strandkit.tools import cost_analytics
        return [
            cost_analytics.get_budget_status,
            cost_analytics.analyze_reserved_instances,
            cost_analytics.analyze_savings_plans,
            cost_analytics.get_rightsizing_recommendations,
            cost_analytics.analyze_commitment_savings,
            cost_analytics.find_cost_optimization_opportunities,
        ]

    elif category == 'cost_waste':
        from strandkit.tools import cost_waste
        return [
            cost_waste.find_zombie_resources,
            cost_waste.analyze_idle_resources,
            cost_waste.analyze_snapshot_waste,
            cost_waste.analyze_data_transfer_costs,
            cost_waste.get_cost_allocation_tags,
        ]

    elif category == 'ec2':
        from strandkit.tools import ec2
        return [
            ec2.analyze_ec2_instance,
            ec2.get_ec2_inventory,
            ec2.find_unused_resources,
            ec2.analyze_security_group,
            ec2.find_overpermissive_security_groups,
        ]

    elif category == 'ec2_advanced':
        from strandkit.tools import ec2_advanced
        return [
            ec2_advanced.analyze_ec2_performance,
            ec2_advanced.analyze_auto_scaling_groups,
            ec2_advanced.analyze_load_balancers,
            ec2_advanced.get_ec2_spot_recommendations,
        ]

    elif category == 's3':
        from strandkit.tools import s3
        return [
            s3.analyze_s3_bucket,
            s3.find_public_buckets,
            s3.get_s3_cost_analysis,
            s3.analyze_bucket_access,
            s3.find_unused_buckets,
        ]

    elif category == 's3_advanced':
        from strandkit.tools import s3_advanced
        return [
            s3_advanced.analyze_s3_storage_classes,
            s3_advanced.analyze_s3_lifecycle_policies,
            s3_advanced.find_s3_versioning_waste,
            s3_advanced.find_incomplete_multipart_uploads,
            s3_advanced.analyze_s3_replication,
            s3_advanced.analyze_s3_request_costs,
            s3_advanced.analyze_large_s3_objects,
        ]

    elif category == 'ebs':
        from strandkit.tools import ebs
        return [
            ebs.analyze_ebs_volumes,
            ebs.analyze_ebs_snapshots_lifecycle,
            ebs.get_ebs_iops_recommendations,
            ebs.analyze_ebs_encryption,
            ebs.find_ebs_volume_anomalies,
            ebs.analyze_ami_usage,
        ]

    elif category == 'rds':
        from strandkit.tools import rds
        return [
            rds.analyze_rds_instance,
            rds.find_idle_databases,
            rds.analyze_rds_backups,
            rds.get_rds_recommendations,
            rds.find_rds_security_issues,
        ]

    elif category == 'vpc':
        from strandkit.tools import vpc
        return [
            vpc.find_unused_nat_gateways,
            vpc.analyze_vpc_configuration,
            vpc.analyze_data_transfer_costs,
            vpc.analyze_vpc_endpoints,
            vpc.find_network_bottlenecks,
        ]

    else:
        return []


def list_tool_categories() -> List[str]:
    """
    List all available tool categories.

    Returns:
        List of category names

    Usage:
        from strandkit.strands import list_tool_categories

        categories = list_tool_categories()
        print(f"Available categories: {', '.join(categories)}")
    """
    return [
        'orchestrators',
        'cloudwatch',
        'cloudformation',
        'iam',
        'iam_security',
        'cost',
        'cost_analytics',
        'cost_waste',
        'ec2',
        'ec2_advanced',
        's3',
        's3_advanced',
        'ebs',
        'rds',
        'vpc',
    ]
