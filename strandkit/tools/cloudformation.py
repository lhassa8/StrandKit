"""
CloudFormation tools for StrandKit.

This module provides tools for analyzing CloudFormation changesets:
- explain_changeset: Parse and explain infrastructure changes in plain English

These tools help developers understand the impact of infrastructure changes
before they're applied.
"""

from typing import Any, Dict, List, Optional
from strandkit.core.aws_client import AWSClient
from strands import tool


@tool
def explain_changeset(
    changeset_name: str,
    stack_name: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Explain a CloudFormation changeset in plain English.

    This tool retrieves a CloudFormation changeset, analyzes the proposed
    changes, and categorizes them by risk level and impact type.

    Args:
        changeset_name: Name or ARN of the changeset
        stack_name: Name of the CloudFormation stack
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "changeset_name": str,
            "stack_name": str,
            "status": str,
            "created_at": str (ISO format),
            "changes": [
                {
                    "resource_type": str,
                    "logical_id": str,
                    "physical_id": str,
                    "action": str,  # "Add", "Modify", "Remove"
                    "replacement": str,  # "True", "False", "Conditional", "N/A"
                    "scope": list[str],  # ["Properties", "Tags", etc.]
                    "details": str,  # Plain English explanation
                    "risk_level": str  # "high", "medium", "low"
                },
                ...
            ],
            "summary": {
                "total_changes": int,
                "adds": int,
                "modifies": int,
                "removes": int,
                "high_risk_changes": int,
                "requires_replacement": int
            },
            "high_risk_resources": list[str],  # Resource types flagged as risky
            "recommendations": list[str]  # Suggested actions
        }

    Example:
        >>> changeset = explain_changeset(
        ...     changeset_name="my-changeset",
        ...     stack_name="my-stack"
        ... )
        >>> print(changeset['summary'])
        >>> for change in changeset['changes']:
        ...     if change['risk_level'] == 'high':
        ...         print(f"⚠️ {change['details']}")

    Tool Schema (for LLMs):
        {
            "name": "explain_changeset",
            "description": "Explain CloudFormation changeset in plain English",
            "parameters": {
                "changeset_name": {
                    "type": "string",
                    "description": "Changeset name or ARN",
                    "required": true
                },
                "stack_name": {
                    "type": "string",
                    "description": "CloudFormation stack name",
                    "required": true
                }
            }
        }
    """
    # Create AWS client if not provided
    if aws_client is None:
        aws_client = AWSClient()

    cfn_client = aws_client.get_client("cloudformation")

    # High-risk resource types that require special attention
    HIGH_RISK_TYPES = {
        "AWS::IAM::Role",
        "AWS::IAM::Policy",
        "AWS::IAM::ManagedPolicy",
        "AWS::RDS::DBInstance",
        "AWS::RDS::DBCluster",
        "AWS::DynamoDB::Table",
        "AWS::S3::Bucket",
        "AWS::EC2::SecurityGroup",
        "AWS::EC2::VPC",
    }

    # Sensitive resource types that require replacement caution
    SENSITIVE_TYPES = {
        "AWS::Lambda::Function",
        "AWS::ECS::Service",
        "AWS::ECS::TaskDefinition",
        "AWS::ElasticLoadBalancingV2::LoadBalancer",
    }

    try:
        # Describe the changeset
        response = cfn_client.describe_change_set(
            ChangeSetName=changeset_name,
            StackName=stack_name
        )

        # Extract metadata
        changeset_status = response.get("Status", "UNKNOWN")
        created_time = response.get("CreationTime")
        created_at = created_time.isoformat() + "Z" if hasattr(created_time, 'isoformat') else str(created_time)

        # Parse changes
        changes = []
        summary_stats = {
            "adds": 0,
            "modifies": 0,
            "removes": 0,
            "high_risk_changes": 0,
            "requires_replacement": 0
        }
        high_risk_resources = []
        recommendations = []

        for change in response.get("Changes", []):
            if change.get("Type") != "Resource":
                continue

            resource_change = change.get("ResourceChange", {})

            # Extract change details
            resource_type = resource_change.get("ResourceType", "Unknown")
            logical_id = resource_change.get("LogicalResourceId", "")
            physical_id = resource_change.get("PhysicalResourceId", "N/A")
            action = resource_change.get("Action", "Unknown")
            replacement = resource_change.get("Replacement", "N/A")
            scope = resource_change.get("Scope", [])

            # Determine risk level
            risk_level = _determine_risk_level(
                resource_type, action, replacement, HIGH_RISK_TYPES, SENSITIVE_TYPES
            )

            # Generate plain English explanation
            details = _generate_change_explanation(
                resource_type, logical_id, action, replacement, scope
            )

            changes.append({
                "resource_type": resource_type,
                "logical_id": logical_id,
                "physical_id": physical_id,
                "action": action,
                "replacement": replacement,
                "scope": scope,
                "details": details,
                "risk_level": risk_level
            })

            # Update summary statistics
            if action == "Add":
                summary_stats["adds"] += 1
            elif action == "Modify":
                summary_stats["modifies"] += 1
            elif action == "Remove":
                summary_stats["removes"] += 1

            if risk_level == "high":
                summary_stats["high_risk_changes"] += 1
                if resource_type not in high_risk_resources:
                    high_risk_resources.append(resource_type)

            if replacement in ["True", "Conditional"]:
                summary_stats["requires_replacement"] += 1

        # Generate recommendations
        if summary_stats["removes"] > 0:
            recommendations.append("⚠️ This changeset includes resource deletions. Ensure you have backups if needed.")

        if summary_stats["requires_replacement"] > 0:
            recommendations.append("⚠️ Some resources will be replaced (deleted and recreated). This may cause downtime.")

        if "AWS::IAM::Role" in high_risk_resources or "AWS::IAM::Policy" in high_risk_resources:
            recommendations.append("🔒 IAM changes detected. Review permissions carefully.")

        if "AWS::RDS::DBInstance" in high_risk_resources or "AWS::DynamoDB::Table" in high_risk_resources:
            recommendations.append("💾 Database changes detected. Ensure data migration plan is in place.")

        if not recommendations:
            recommendations.append("✅ No high-risk changes detected. Review changes and apply when ready.")

        # Build response
        return {
            "changeset_name": changeset_name,
            "stack_name": stack_name,
            "status": changeset_status,
            "created_at": created_at,
            "changes": changes,
            "summary": {
                "total_changes": len(changes),
                **summary_stats
            },
            "high_risk_resources": high_risk_resources,
            "recommendations": recommendations
        }

    except cfn_client.exceptions.ChangeSetNotFoundException:
        return {
            "changeset_name": changeset_name,
            "stack_name": stack_name,
            "status": "NOT_FOUND",
            "created_at": "",
            "changes": [],
            "summary": {
                "total_changes": 0,
                "adds": 0,
                "modifies": 0,
                "removes": 0,
                "high_risk_changes": 0,
                "requires_replacement": 0
            },
            "high_risk_resources": [],
            "recommendations": [],
            "error": f"Changeset '{changeset_name}' not found in stack '{stack_name}'"
        }

    except Exception as e:
        return {
            "changeset_name": changeset_name,
            "stack_name": stack_name,
            "status": "ERROR",
            "created_at": "",
            "changes": [],
            "summary": {
                "total_changes": 0,
                "adds": 0,
                "modifies": 0,
                "removes": 0,
                "high_risk_changes": 0,
                "requires_replacement": 0
            },
            "high_risk_resources": [],
            "recommendations": [],
            "error": str(e)
        }


@tool
def _determine_risk_level(
    resource_type: str,
    action: str,
    replacement: str,
    high_risk_types: set,
    sensitive_types: set
) -> str:
    """
    Determine the risk level of a change.

    Args:
        resource_type: AWS resource type
        action: Add, Modify, or Remove
        replacement: Whether replacement is required
        high_risk_types: Set of high-risk resource types
        sensitive_types: Set of sensitive resource types

    Returns:
        Risk level: "high", "medium", or "low"
    """
    # Removals are always high risk
    if action == "Remove":
        return "high"

    # Replacements of sensitive resources are high risk
    if replacement == "True" and (resource_type in high_risk_types or resource_type in sensitive_types):
        return "high"

    # Changes to high-risk resource types
    if resource_type in high_risk_types:
        return "high"

    # Conditional replacements are medium risk
    if replacement == "Conditional":
        return "medium"

    # Modifications with replacement are medium risk
    if action == "Modify" and replacement == "True":
        return "medium"

    # Everything else is low risk
    return "low"


@tool
def _generate_change_explanation(
    resource_type: str,
    logical_id: str,
    action: str,
    replacement: str,
    scope: List[str]
) -> str:
    """
    Generate plain English explanation of a change.

    Args:
        resource_type: AWS resource type
        logical_id: Logical resource ID
        action: Add, Modify, or Remove
        replacement: Whether replacement is required
        scope: What's being changed (Properties, Tags, etc.)

    Returns:
        Human-readable explanation
    """
    # Extract simple resource name from type (e.g., "AWS::Lambda::Function" -> "Lambda Function")
    simple_type = resource_type.replace("AWS::", "").replace("::", " ")

    if action == "Add":
        return f"Creating new {simple_type} '{logical_id}'"

    elif action == "Remove":
        return f"⚠️ DELETING {simple_type} '{logical_id}'"

    elif action == "Modify":
        if replacement == "True":
            scope_desc = ", ".join(scope) if scope else "properties"
            return f"⚠️ REPLACING {simple_type} '{logical_id}' (changes to {scope_desc} require replacement)"

        elif replacement == "Conditional":
            scope_desc = ", ".join(scope) if scope else "properties"
            return f"Modifying {simple_type} '{logical_id}' (changes to {scope_desc} may require replacement)"

        else:
            scope_desc = ", ".join(scope) if scope else "properties"
            return f"Updating {simple_type} '{logical_id}' ({scope_desc})"

    return f"{action} {simple_type} '{logical_id}'"
