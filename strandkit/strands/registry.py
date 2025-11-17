"""
Tool registry for Strands agents.

This module provides a registry of all StrandKit tools with their schemas,
organized by category for easy discovery and use.
"""

from typing import List, Dict, Any, Optional
from strandkit.strands.schemas import generate_tool_schema, create_tool_wrapper

# Import all tools
from strandkit.tools import (
    # CloudWatch
    get_lambda_logs, get_metric, get_log_insights, get_recent_errors,
    # CloudFormation
    explain_changeset,
    # IAM
    analyze_role, explain_policy, find_overpermissive_roles,
    # IAM Security
    analyze_iam_users, analyze_access_keys, analyze_mfa_compliance,
    analyze_password_policy, find_cross_account_access,
    detect_privilege_escalation_paths, analyze_unused_permissions,
    get_iam_credential_report,
    # Cost
    get_cost_and_usage, get_cost_by_service, detect_cost_anomalies,
    get_cost_forecast,
    # Cost Analytics
    get_budget_status, analyze_reserved_instances, analyze_savings_plans,
    get_rightsizing_recommendations, analyze_commitment_savings,
    find_cost_optimization_opportunities,
    # Cost Waste
    find_zombie_resources, analyze_idle_resources, analyze_snapshot_waste,
    analyze_data_transfer_costs, get_cost_allocation_tags,
    # EC2
    analyze_ec2_instance, get_ec2_inventory, find_unused_resources,
    analyze_security_group, find_overpermissive_security_groups,
    # S3
    analyze_s3_bucket, find_public_buckets, get_s3_cost_analysis,
    analyze_bucket_access, find_unused_buckets,
    # EBS
    analyze_ebs_volumes, analyze_ebs_snapshots_lifecycle,
    get_ebs_iops_recommendations, analyze_ebs_encryption,
    find_ebs_volume_anomalies, analyze_ami_usage,
    # S3 Advanced
    analyze_s3_storage_classes, analyze_s3_lifecycle_policies,
    find_s3_versioning_waste, find_incomplete_multipart_uploads,
    analyze_s3_replication, analyze_s3_request_costs,
    analyze_large_s3_objects,
    # EC2 Advanced
    analyze_ec2_performance, analyze_auto_scaling_groups,
    analyze_load_balancers, get_ec2_spot_recommendations
)

# Tool categories for organization
TOOL_CATEGORIES = {
    'cloudwatch': {
        'name': 'CloudWatch',
        'description': 'Logs, metrics, and monitoring tools',
        'tools': [
            get_lambda_logs,
            get_metric,
            get_log_insights,
            get_recent_errors
        ]
    },
    'cloudformation': {
        'name': 'CloudFormation',
        'description': 'Infrastructure as code analysis',
        'tools': [
            explain_changeset
        ]
    },
    'iam': {
        'name': 'IAM',
        'description': 'Identity and access management',
        'tools': [
            analyze_role,
            explain_policy,
            find_overpermissive_roles
        ]
    },
    'iam_security': {
        'name': 'IAM Security',
        'description': 'Advanced IAM security auditing and compliance',
        'tools': [
            analyze_iam_users,
            analyze_access_keys,
            analyze_mfa_compliance,
            analyze_password_policy,
            find_cross_account_access,
            detect_privilege_escalation_paths,
            analyze_unused_permissions,
            get_iam_credential_report
        ]
    },
    'cost': {
        'name': 'Cost Explorer',
        'description': 'Cost analysis and forecasting',
        'tools': [
            get_cost_and_usage,
            get_cost_by_service,
            detect_cost_anomalies,
            get_cost_forecast
        ]
    },
    'cost_analytics': {
        'name': 'Cost Analytics',
        'description': 'Advanced cost optimization and savings',
        'tools': [
            get_budget_status,
            analyze_reserved_instances,
            analyze_savings_plans,
            get_rightsizing_recommendations,
            analyze_commitment_savings,
            find_cost_optimization_opportunities
        ]
    },
    'cost_waste': {
        'name': 'Cost Waste Detection',
        'description': 'Find wasted spend and unused resources',
        'tools': [
            find_zombie_resources,
            analyze_idle_resources,
            analyze_snapshot_waste,
            analyze_data_transfer_costs,
            get_cost_allocation_tags
        ]
    },
    'ec2': {
        'name': 'EC2',
        'description': 'EC2 instance and security group analysis',
        'tools': [
            analyze_ec2_instance,
            get_ec2_inventory,
            find_unused_resources,
            analyze_security_group,
            find_overpermissive_security_groups
        ]
    },
    's3': {
        'name': 'S3',
        'description': 'S3 bucket security and cost optimization',
        'tools': [
            analyze_s3_bucket,
            find_public_buckets,
            get_s3_cost_analysis,
            analyze_bucket_access,
            find_unused_buckets
        ]
    },
    'ebs': {
        'name': 'EBS',
        'description': 'EBS volume and snapshot optimization',
        'tools': [
            analyze_ebs_volumes,
            analyze_ebs_snapshots_lifecycle,
            get_ebs_iops_recommendations,
            analyze_ebs_encryption,
            find_ebs_volume_anomalies,
            analyze_ami_usage
        ]
    },
    's3_advanced': {
        'name': 'S3 Advanced',
        'description': 'Advanced S3 storage optimization',
        'tools': [
            analyze_s3_storage_classes,
            analyze_s3_lifecycle_policies,
            find_s3_versioning_waste,
            find_incomplete_multipart_uploads,
            analyze_s3_replication,
            analyze_s3_request_costs,
            analyze_large_s3_objects
        ]
    },
    'ec2_advanced': {
        'name': 'EC2 Advanced',
        'description': 'Advanced EC2 performance and optimization',
        'tools': [
            analyze_ec2_performance,
            analyze_auto_scaling_groups,
            analyze_load_balancers,
            get_ec2_spot_recommendations
        ]
    }
}


def get_all_tools() -> List[Dict[str, Any]]:
    """
    Get all StrandKit tools with their schemas.

    Returns:
        List of tool dictionaries with name, description, schema, and function

    Example:
        >>> tools = get_all_tools()
        >>> len(tools)
        60
        >>> tools[0]['name']
        'get_lambda_logs'
    """
    all_tools = []

    for category_info in TOOL_CATEGORIES.values():
        for func in category_info['tools']:
            schema = generate_tool_schema(func)
            tool = create_tool_wrapper(func, schema)
            tool['category'] = category_info['name']
            all_tools.append(tool)

    return all_tools


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get tools for a specific category.

    Args:
        category: Category key (e.g., 'iam', 'cost', 'ec2')

    Returns:
        List of tools in that category

    Example:
        >>> iam_tools = get_tools_by_category('iam')
        >>> len(iam_tools)
        3
    """
    if category not in TOOL_CATEGORIES:
        raise ValueError(f"Unknown category: {category}. Use list_tool_categories() to see available categories.")

    category_info = TOOL_CATEGORIES[category]
    tools = []

    for func in category_info['tools']:
        schema = generate_tool_schema(func)
        tool = create_tool_wrapper(func, schema)
        tool['category'] = category_info['name']
        tools.append(tool)

    return tools


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific tool by name.

    Args:
        name: Tool function name (e.g., 'find_overpermissive_roles')

    Returns:
        Tool dictionary or None if not found

    Example:
        >>> tool = get_tool('find_overpermissive_roles')
        >>> tool['name']
        'find_overpermissive_roles'
    """
    all_tools = get_all_tools()

    for tool in all_tools:
        if tool['name'] == name:
            return tool

    return None


def list_tool_categories() -> Dict[str, str]:
    """
    List all available tool categories.

    Returns:
        Dictionary mapping category keys to descriptions

    Example:
        >>> categories = list_tool_categories()
        >>> categories['iam']
        'Identity and access management'
    """
    return {
        key: info['description']
        for key, info in TOOL_CATEGORIES.items()
    }


def get_category_summary() -> Dict[str, Any]:
    """
    Get summary statistics for each category.

    Returns:
        Dictionary with category statistics

    Example:
        >>> summary = get_category_summary()
        >>> summary['iam']['tool_count']
        3
    """
    summary = {}

    for key, info in TOOL_CATEGORIES.items():
        summary[key] = {
            'name': info['name'],
            'description': info['description'],
            'tool_count': len(info['tools']),
            'tools': [func.__name__ for func in info['tools']]
        }

    return summary
