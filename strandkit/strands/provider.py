"""
StrandKit ToolProviders for AWS Strands Agents.

This module provides ToolProvider classes that enable lazy-loading of StrandKit
tools into Strands agents. ToolProviders are the recommended way to integrate
StrandKit with AWS Strands Agents.

Example:
    from strands import Agent
    from strandkit.strands import StrandKitToolProvider

    # Create agent with all 60 StrandKit tools
    agent = Agent(tools=[StrandKitToolProvider()])

    # Or with specific categories
    from strandkit.strands import StrandKitCategoryProvider

    agent = Agent(tools=[
        StrandKitCategoryProvider(['iam', 'iam_security', 'ec2'])
    ])
"""

from typing import List, Any
from strands.tools import ToolProvider


class StrandKitToolProvider(ToolProvider):
    """
    Lazy-loading ToolProvider for all 60 StrandKit AWS tools.

    This provider loads all StrandKit tools when requested by a Strands agent.
    Tools are organized across 12 categories covering CloudWatch, IAM, Cost,
    EC2, S3, EBS, and CloudFormation.

    Usage:
        from strands import Agent
        from strandkit.strands import StrandKitToolProvider

        agent = Agent(
            model="anthropic.claude-3-5-haiku",
            tools=[StrandKitToolProvider()],
            system_prompt="You are an AWS infrastructure analyst"
        )

        response = agent("Find security risks in my IAM roles")

    Returns all 60 tools:
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

    async def load_tools(self) -> List[Any]:
        """
        Load all 60 StrandKit tools.

        Returns:
            List of @tool-decorated functions ready for Strands agents
        """
        # Import all tool modules
        from strandkit.tools import (
            cloudwatch,
            cloudwatch_enhanced,
            cloudformation,
            iam,
            iam_security,
            cost,
            cost_analytics,
            cost_waste,
            ec2,
            ec2_advanced,
            s3,
            s3_advanced,
            ebs
        )

        # Return all decorated tool functions
        return [
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
        ]


class StrandKitCategoryProvider(ToolProvider):
    """
    ToolProvider that loads tools from specific categories.

    Use this when you want to create specialized agents that only have
    access to tools from specific categories (e.g., security-only agent,
    cost-only agent).

    Args:
        categories: List of category names to load

    Available Categories:
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

    Usage:
        from strands import Agent
        from strandkit.strands import StrandKitCategoryProvider

        # Security-focused agent
        security_agent = Agent(
            tools=[StrandKitCategoryProvider(['iam', 'iam_security', 'ec2'])],
            system_prompt="You are a security auditor"
        )

        # Cost optimization agent
        cost_agent = Agent(
            tools=[StrandKitCategoryProvider(['cost', 'cost_analytics', 'cost_waste'])],
            system_prompt="You are a cost optimization specialist"
        )

        # Debugging agent
        debug_agent = Agent(
            tools=[StrandKitCategoryProvider(['cloudwatch', 'ec2', 'ec2_advanced'])],
            system_prompt="You are an infrastructure debugger"
        )
    """

    def __init__(self, categories: List[str]):
        """
        Initialize provider with specified categories.

        Args:
            categories: List of category names (e.g., ['iam', 'cost', 'ec2'])
        """
        self.categories = categories

    async def load_tools(self) -> List[Any]:
        """
        Load tools from specified categories.

        Returns:
            List of @tool-decorated functions from the requested categories
        """
        tools = []

        for category in self.categories:
            if category == 'cloudwatch':
                from strandkit.tools import cloudwatch, cloudwatch_enhanced
                tools.extend([
                    cloudwatch.get_lambda_logs,
                    cloudwatch.get_metric,
                    cloudwatch_enhanced.get_log_insights,
                    cloudwatch_enhanced.get_recent_errors,
                ])

            elif category == 'cloudformation':
                from strandkit.tools import cloudformation
                tools.extend([
                    cloudformation.explain_changeset,
                ])

            elif category == 'iam':
                from strandkit.tools import iam
                tools.extend([
                    iam.analyze_role,
                    iam.explain_policy,
                    iam.find_overpermissive_roles,
                ])

            elif category == 'iam_security':
                from strandkit.tools import iam_security
                tools.extend([
                    iam_security.analyze_iam_users,
                    iam_security.analyze_access_keys,
                    iam_security.analyze_mfa_compliance,
                    iam_security.analyze_password_policy,
                    iam_security.find_cross_account_access,
                    iam_security.detect_privilege_escalation_paths,
                    iam_security.analyze_unused_permissions,
                    iam_security.get_iam_credential_report,
                ])

            elif category == 'cost':
                from strandkit.tools import cost
                tools.extend([
                    cost.get_cost_and_usage,
                    cost.get_cost_by_service,
                    cost.detect_cost_anomalies,
                    cost.get_cost_forecast,
                ])

            elif category == 'cost_analytics':
                from strandkit.tools import cost_analytics
                tools.extend([
                    cost_analytics.get_budget_status,
                    cost_analytics.analyze_reserved_instances,
                    cost_analytics.analyze_savings_plans,
                    cost_analytics.get_rightsizing_recommendations,
                    cost_analytics.analyze_commitment_savings,
                    cost_analytics.find_cost_optimization_opportunities,
                ])

            elif category == 'cost_waste':
                from strandkit.tools import cost_waste
                tools.extend([
                    cost_waste.find_zombie_resources,
                    cost_waste.analyze_idle_resources,
                    cost_waste.analyze_snapshot_waste,
                    cost_waste.analyze_data_transfer_costs,
                    cost_waste.get_cost_allocation_tags,
                ])

            elif category == 'ec2':
                from strandkit.tools import ec2
                tools.extend([
                    ec2.analyze_ec2_instance,
                    ec2.get_ec2_inventory,
                    ec2.find_unused_resources,
                    ec2.analyze_security_group,
                    ec2.find_overpermissive_security_groups,
                ])

            elif category == 'ec2_advanced':
                from strandkit.tools import ec2_advanced
                tools.extend([
                    ec2_advanced.analyze_ec2_performance,
                    ec2_advanced.analyze_auto_scaling_groups,
                    ec2_advanced.analyze_load_balancers,
                    ec2_advanced.get_ec2_spot_recommendations,
                ])

            elif category == 's3':
                from strandkit.tools import s3
                tools.extend([
                    s3.analyze_s3_bucket,
                    s3.find_public_buckets,
                    s3.get_s3_cost_analysis,
                    s3.analyze_bucket_access,
                    s3.find_unused_buckets,
                ])

            elif category == 's3_advanced':
                from strandkit.tools import s3_advanced
                tools.extend([
                    s3_advanced.analyze_s3_storage_classes,
                    s3_advanced.analyze_s3_lifecycle_policies,
                    s3_advanced.find_s3_versioning_waste,
                    s3_advanced.find_incomplete_multipart_uploads,
                    s3_advanced.analyze_s3_replication,
                    s3_advanced.analyze_s3_request_costs,
                    s3_advanced.analyze_large_s3_objects,
                ])

            elif category == 'ebs':
                from strandkit.tools import ebs
                tools.extend([
                    ebs.analyze_ebs_volumes,
                    ebs.analyze_ebs_snapshots_lifecycle,
                    ebs.get_ebs_iops_recommendations,
                    ebs.analyze_ebs_encryption,
                    ebs.find_ebs_volume_anomalies,
                    ebs.analyze_ami_usage,
                ])

        return tools
