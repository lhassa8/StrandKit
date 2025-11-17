"""
IAM tools for StrandKit.

This module provides tools for analyzing AWS IAM policies and permissions:
- analyze_role: Analyze IAM role permissions and assess risk
- explain_policy: Parse and explain IAM policy in plain English
- find_overpermissive_roles: Detect roles with excessive permissions

These tools help with security auditing and IAM policy review.
"""

from typing import Any, Dict, List, Optional, Set
import json
from strandkit.core.aws_client import AWSClient
from strands import tool


@tool
def analyze_role(
    role_name: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze an IAM role's permissions and assess security risk.

    This tool retrieves an IAM role, analyzes its attached policies,
    and provides a comprehensive security assessment including:
    - List of all permissions
    - Risk level assessment
    - Overly permissive patterns
    - Recommendations

    Args:
        role_name: Name of the IAM role to analyze
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "role_name": str,
            "role_arn": str,
            "created_date": str (ISO format),
            "attached_policies": [
                {
                    "policy_name": str,
                    "policy_arn": str,
                    "policy_type": str  # "AWS Managed", "Customer Managed", "Inline"
                }
            ],
            "permissions_summary": {
                "total_statements": int,
                "services_accessed": list[str],
                "has_admin_access": bool,
                "has_wildcard_resources": bool,
                "has_wildcard_actions": bool
            },
            "risk_assessment": {
                "risk_level": str,  # "critical", "high", "medium", "low"
                "risk_factors": list[str],
                "overpermissive_patterns": list[str]
            },
            "recommendations": list[str]
        }

    Example:
        >>> analysis = analyze_role("MyAppRole")
        >>> if analysis['risk_assessment']['risk_level'] == 'high':
        ...     print("⚠️ High risk role detected!")
        ...     for factor in analysis['risk_assessment']['risk_factors']:
        ...         print(f"  - {factor}")

    Tool Schema (for LLMs):
        {
            "name": "analyze_role",
            "description": "Analyze IAM role permissions and security risks",
            "parameters": {
                "role_name": {
                    "type": "string",
                    "description": "IAM role name",
                    "required": true
                }
            }
        }
    """
    # Create AWS client if not provided
    if aws_client is None:
        aws_client = AWSClient()

    iam_client = aws_client.get_client("iam")

    try:
        # Get role details
        role_response = iam_client.get_role(RoleName=role_name)
        role = role_response["Role"]

        # Get attached managed policies
        attached_policies_response = iam_client.list_attached_role_policies(
            RoleName=role_name
        )

        # Get inline policies
        inline_policies_response = iam_client.list_role_policies(
            RoleName=role_name
        )

        # Build policies list
        policies = []
        all_statements = []
        services_accessed = set()
        has_admin_access = False
        has_wildcard_resources = False
        has_wildcard_actions = False

        # Process managed policies
        for policy_ref in attached_policies_response.get("AttachedPolicies", []):
            policy_arn = policy_ref["PolicyArn"]
            policy_name = policy_ref["PolicyName"]

            # Determine if AWS managed or customer managed
            policy_type = "AWS Managed" if policy_arn.startswith("arn:aws:iam::aws:") else "Customer Managed"

            policies.append({
                "policy_name": policy_name,
                "policy_arn": policy_arn,
                "policy_type": policy_type
            })

            # Get policy document for analysis
            try:
                # Get default version
                policy_response = iam_client.get_policy(PolicyArn=policy_arn)
                default_version_id = policy_response["Policy"]["DefaultVersionId"]

                # Get policy version document
                version_response = iam_client.get_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=default_version_id
                )

                policy_document = version_response["PolicyVersion"]["Document"]
                statements = policy_document.get("Statement", [])
                if isinstance(statements, dict):
                    statements = [statements]

                all_statements.extend(statements)

                # Analyze statements
                for statement in statements:
                    _analyze_statement(
                        statement,
                        services_accessed,
                        has_admin_access,
                        has_wildcard_resources,
                        has_wildcard_actions
                    )

            except Exception as e:
                # Skip if we can't read the policy (permissions issue)
                pass

        # Process inline policies
        for policy_name in inline_policies_response.get("PolicyNames", []):
            policies.append({
                "policy_name": policy_name,
                "policy_arn": "N/A",
                "policy_type": "Inline"
            })

            # Get inline policy document
            try:
                policy_response = iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )

                policy_document = policy_response["PolicyDocument"]
                statements = policy_document.get("Statement", [])
                if isinstance(statements, dict):
                    statements = [statements]

                all_statements.extend(statements)

                # Analyze statements
                for statement in statements:
                    services, admin, wildcard_res, wildcard_act = _analyze_statement(statement)
                    services_accessed.update(services)
                    has_admin_access = has_admin_access or admin
                    has_wildcard_resources = has_wildcard_resources or wildcard_res
                    has_wildcard_actions = has_wildcard_actions or wildcard_act

            except Exception:
                pass

        # Risk assessment
        risk_factors = []
        overpermissive_patterns = []

        if has_admin_access:
            risk_factors.append("Has administrator access (*:*)")
            overpermissive_patterns.append("Action: *, Resource: *")

        if has_wildcard_actions:
            risk_factors.append("Uses wildcard actions (e.g., s3:*)")
            overpermissive_patterns.append("Wildcard actions detected")

        if has_wildcard_resources:
            risk_factors.append("Uses wildcard resources (e.g., Resource: *)")
            overpermissive_patterns.append("Wildcard resources detected")

        # Check for sensitive services
        sensitive_services = {"iam", "sts", "kms", "secretsmanager", "organizations"}
        accessed_sensitive = services_accessed.intersection(sensitive_services)
        if accessed_sensitive:
            risk_factors.append(f"Access to sensitive services: {', '.join(accessed_sensitive)}")

        # Determine risk level
        if has_admin_access:
            risk_level = "critical"
        elif len(risk_factors) >= 3:
            risk_level = "high"
        elif len(risk_factors) >= 1:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate recommendations
        recommendations = []
        if has_admin_access:
            recommendations.append("🔴 Remove administrator access and grant only necessary permissions")

        if has_wildcard_resources:
            recommendations.append("⚠️ Replace wildcard resources (*) with specific resource ARNs")

        if has_wildcard_actions:
            recommendations.append("⚠️ Replace wildcard actions with specific action names")

        if accessed_sensitive:
            recommendations.append(f"🔒 Review access to sensitive services: {', '.join(accessed_sensitive)}")

        if not recommendations:
            recommendations.append("✅ No immediate security concerns detected")

        # Build response
        return {
            "role_name": role_name,
            "role_arn": role["Arn"],
            "created_date": role["CreateDate"].isoformat() + "Z" if hasattr(role["CreateDate"], 'isoformat') else str(role["CreateDate"]),
            "attached_policies": policies,
            "permissions_summary": {
                "total_statements": len(all_statements),
                "total_policies": len(policies),
                "services_accessed": sorted(list(services_accessed)),
                "has_admin_access": has_admin_access,
                "has_wildcard_resources": has_wildcard_resources,
                "has_wildcard_actions": has_wildcard_actions
            },
            "risk_assessment": {
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "overpermissive_patterns": overpermissive_patterns
            },
            "recommendations": recommendations
        }

    except iam_client.exceptions.NoSuchEntityException:
        return {
            "role_name": role_name,
            "role_arn": "",
            "created_date": "",
            "attached_policies": [],
            "permissions_summary": {
                "total_statements": 0,
                "total_policies": 0,
                "services_accessed": [],
                "has_admin_access": False,
                "has_wildcard_resources": False,
                "has_wildcard_actions": False
            },
            "risk_assessment": {
                "risk_level": "unknown",
                "risk_factors": [],
                "overpermissive_patterns": []
            },
            "recommendations": [],
            "error": f"Role '{role_name}' not found"
        }

    except Exception as e:
        return {
            "role_name": role_name,
            "role_arn": "",
            "created_date": "",
            "attached_policies": [],
            "permissions_summary": {
                "total_statements": 0,
                "total_policies": 0,
                "services_accessed": [],
                "has_admin_access": False,
                "has_wildcard_resources": False,
                "has_wildcard_actions": False
            },
            "risk_assessment": {
                "risk_level": "unknown",
                "risk_factors": [],
                "overpermissive_patterns": []
            },
            "recommendations": [],
            "error": str(e)
        }


@tool
def _analyze_statement(statement: Dict[str, Any]) -> tuple:
    """
    Analyze a single IAM policy statement.

    Returns:
        Tuple of (services_set, has_admin, has_wildcard_resources, has_wildcard_actions)
    """
    services = set()
    has_admin = False
    has_wildcard_resources = False
    has_wildcard_actions = False

    # Only analyze Allow statements
    if statement.get("Effect") != "Allow":
        return services, has_admin, has_wildcard_resources, has_wildcard_actions

    # Extract actions
    actions = statement.get("Action", [])
    if isinstance(actions, str):
        actions = [actions]

    for action in actions:
        # Check for admin access
        if action == "*":
            has_admin = True
            has_wildcard_actions = True
        elif "*" in action:
            has_wildcard_actions = True

        # Extract service name (before the :)
        if ":" in action:
            service = action.split(":")[0]
            services.add(service)

    # Extract resources
    resources = statement.get("Resource", [])
    if isinstance(resources, str):
        resources = [resources]

    for resource in resources:
        if resource == "*":
            has_wildcard_resources = True
            if has_wildcard_actions or any(a == "*" for a in actions):
                has_admin = True

    return services, has_admin, has_wildcard_resources, has_wildcard_actions


@tool
def explain_policy(
    policy_document: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Explain an IAM policy document in plain English.

    Args:
        policy_document: JSON string of IAM policy document
        aws_client: Optional AWSClient instance (unused, for consistency)

    Returns:
        Dictionary containing:
        {
            "statements": [
                {
                    "effect": str,  # "Allow" or "Deny"
                    "actions": list[str],
                    "resources": list[str],
                    "explanation": str  # Plain English explanation
                }
            ],
            "summary": str,
            "risk_level": str
        }

    Example:
        >>> policy = '''{
        ...   "Statement": [{
        ...     "Effect": "Allow",
        ...     "Action": "s3:*",
        ...     "Resource": "*"
        ...   }]
        ... }'''
        >>> result = explain_policy(policy)
        >>> print(result['summary'])
    """
    try:
        # Parse JSON
        if isinstance(policy_document, str):
            policy = json.loads(policy_document)
        else:
            policy = policy_document

        statements = policy.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]

        explained_statements = []
        risk_level = "low"

        for stmt in statements:
            effect = stmt.get("Effect", "Allow")
            actions = stmt.get("Action", [])
            resources = stmt.get("Resource", [])

            if isinstance(actions, str):
                actions = [actions]
            if isinstance(resources, str):
                resources = [resources]

            # Generate explanation
            explanation = _generate_policy_explanation(effect, actions, resources)

            # Assess risk
            if "*" in actions and "*" in resources:
                risk_level = "critical"
            elif "*" in actions or "*" in resources:
                if risk_level not in ["critical"]:
                    risk_level = "high"

            explained_statements.append({
                "effect": effect,
                "actions": actions,
                "resources": resources,
                "explanation": explanation
            })

        # Generate summary
        if len(explained_statements) == 1:
            summary = explained_statements[0]["explanation"]
        else:
            summary = f"Policy contains {len(explained_statements)} statement(s)"

        return {
            "statements": explained_statements,
            "summary": summary,
            "risk_level": risk_level
        }

    except Exception as e:
        return {
            "statements": [],
            "summary": "",
            "risk_level": "unknown",
            "error": str(e)
        }


@tool
def _generate_policy_explanation(effect: str, actions: List[str], resources: List[str]) -> str:
    """Generate plain English explanation of a policy statement."""

    action_desc = ", ".join(actions[:3])
    if len(actions) > 3:
        action_desc += f" (and {len(actions) - 3} more)"

    resource_desc = ", ".join(resources[:2])
    if len(resources) > 2:
        resource_desc += f" (and {len(resources) - 2} more)"

    if effect == "Allow":
        return f"Allows {action_desc} on {resource_desc}"
    else:
        return f"Denies {action_desc} on {resource_desc}"


@tool
def find_overpermissive_roles(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Scan all IAM roles and find overpermissive ones.

    This tool lists all IAM roles and identifies those with:
    - Administrator access
    - Wildcard resources
    - Wildcard actions

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "total_roles": int,
            "scanned_roles": int,
            "overpermissive_roles": [
                {
                    "role_name": str,
                    "risk_level": str,
                    "risk_factors": list[str]
                }
            ],
            "summary": {
                "critical": int,
                "high": int,
                "medium": int,
                "low": int
            }
        }

    Example:
        >>> results = find_overpermissive_roles()
        >>> print(f"Found {len(results['overpermissive_roles'])} risky roles")
        >>> for role in results['overpermissive_roles']:
        ...     if role['risk_level'] == 'critical':
        ...         print(f"⚠️ {role['role_name']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    iam_client = aws_client.get_client("iam")

    try:
        # List all roles
        paginator = iam_client.get_paginator('list_roles')
        all_roles = []

        for page in paginator.paginate():
            all_roles.extend(page['Roles'])

        total_roles = len(all_roles)
        overpermissive = []
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        # Analyze each role (limit to first 50 to avoid timeouts)
        for role in all_roles[:50]:
            role_name = role['RoleName']

            # Quick check - skip AWS service roles
            if role_name.startswith('AWS') or 'Service' in role_name:
                continue

            try:
                analysis = analyze_role(role_name, aws_client)

                risk_level = analysis['risk_assessment']['risk_level']

                if risk_level in ['critical', 'high', 'medium']:
                    overpermissive.append({
                        "role_name": role_name,
                        "risk_level": risk_level,
                        "risk_factors": analysis['risk_assessment']['risk_factors']
                    })

                if risk_level in summary:
                    summary[risk_level] += 1

            except Exception:
                # Skip roles we can't analyze
                continue

        # Sort by risk level
        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        overpermissive.sort(key=lambda x: risk_order.get(x['risk_level'], 4))

        return {
            "total_roles": total_roles,
            "scanned_roles": min(50, total_roles),
            "overpermissive_roles": overpermissive,
            "summary": summary
        }

    except Exception as e:
        return {
            "total_roles": 0,
            "scanned_roles": 0,
            "overpermissive_roles": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "error": str(e)
        }
