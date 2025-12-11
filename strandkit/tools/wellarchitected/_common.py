"""
Common utilities for Well-Architected Framework tools.

This module provides shared functions for scoring, formatting,
and consistent output across all pillar tools.
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class ComplianceStatus(str, Enum):
    """Compliance status for Well-Architected checks."""
    PASS = "PASS"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    HIGH_RISK = "HIGH_RISK"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


class Severity(str, Enum):
    """Severity levels for findings."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Effort(str, Enum):
    """Effort levels for remediation."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Pillar(str, Enum):
    """Well-Architected Framework pillars."""
    SECURITY = "Security"
    RELIABILITY = "Reliability"
    COST_OPTIMIZATION = "Cost Optimization"
    OPERATIONAL_EXCELLENCE = "Operational Excellence"
    PERFORMANCE_EFFICIENCY = "Performance Efficiency"
    SUSTAINABILITY = "Sustainability"


def create_finding(
    resource: str,
    issue: str,
    severity: str = "MEDIUM",
    recommendation: str = "",
    effort: str = "MEDIUM",
    impact: str = "MEDIUM",
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized finding object.

    Args:
        resource: ARN or identifier of the resource
        issue: Description of the issue found
        severity: CRITICAL, HIGH, MEDIUM, LOW, or INFO
        recommendation: Suggested remediation action
        effort: LOW, MEDIUM, or HIGH effort to fix
        impact: LOW, MEDIUM, or HIGH impact of the issue
        details: Additional details about the finding

    Returns:
        Standardized finding dictionary
    """
    finding = {
        "resource": resource,
        "issue": issue,
        "severity": severity,
        "recommendation": recommendation,
        "effort": effort,
        "impact": impact,
    }
    if details:
        finding["details"] = details
    return finding


def calculate_score(total: int, compliant: int) -> int:
    """
    Calculate compliance score as percentage.

    Args:
        total: Total number of resources/checks
        compliant: Number of compliant resources/checks

    Returns:
        Score from 0-100
    """
    if total == 0:
        return 100
    return int((compliant / total) * 100)


def determine_status(score: int) -> str:
    """
    Determine compliance status based on score.

    Args:
        score: Score from 0-100

    Returns:
        ComplianceStatus string
    """
    if score >= 90:
        return ComplianceStatus.PASS.value
    elif score >= 60:
        return ComplianceStatus.NEEDS_ATTENTION.value
    else:
        return ComplianceStatus.HIGH_RISK.value


def create_check_result(
    pillar: str,
    check_name: str,
    findings: List[Dict[str, Any]],
    total_resources: int,
    compliant_resources: int,
    best_practices: Optional[List[str]] = None,
    summary_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized check result.

    Args:
        pillar: The Well-Architected pillar name
        check_name: Name of the check function
        findings: List of finding dictionaries
        total_resources: Total resources checked
        compliant_resources: Resources that passed the check
        best_practices: List of best practice recommendations
        summary_details: Additional summary information

    Returns:
        Standardized check result dictionary
    """
    score = calculate_score(total_resources, compliant_resources)
    status = determine_status(score)

    non_compliant = total_resources - compliant_resources
    compliance_pct = (compliant_resources / total_resources * 100) if total_resources > 0 else 100.0

    result = {
        "pillar": pillar,
        "check": check_name,
        "status": status,
        "score": score,
        "findings": findings,
        "summary": {
            "total_resources": total_resources,
            "compliant": compliant_resources,
            "non_compliant": non_compliant,
            "compliance_percentage": round(compliance_pct, 1),
        },
        "best_practices": best_practices or [],
    }

    if summary_details:
        result["summary"].update(summary_details)

    return result


def create_pillar_review_result(
    pillar: str,
    check_results: List[Dict[str, Any]],
    recommendations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a comprehensive pillar review result.

    Args:
        pillar: The Well-Architected pillar name
        check_results: List of individual check results
        recommendations: High-level recommendations

    Returns:
        Comprehensive pillar review dictionary
    """
    total_checks = len(check_results)
    passed_checks = sum(1 for r in check_results if r.get("status") == ComplianceStatus.PASS.value)

    # Calculate aggregate score
    if check_results:
        avg_score = sum(r.get("score", 0) for r in check_results) / len(check_results)
    else:
        avg_score = 100

    overall_status = determine_status(int(avg_score))

    # Collect all findings by severity
    all_findings = []
    for result in check_results:
        all_findings.extend(result.get("findings", []))

    findings_by_severity = {
        "critical": sum(1 for f in all_findings if f.get("severity") == "CRITICAL"),
        "high": sum(1 for f in all_findings if f.get("severity") == "HIGH"),
        "medium": sum(1 for f in all_findings if f.get("severity") == "MEDIUM"),
        "low": sum(1 for f in all_findings if f.get("severity") == "LOW"),
        "info": sum(1 for f in all_findings if f.get("severity") == "INFO"),
    }

    # Get top issues (critical and high severity)
    top_issues = [
        f for f in all_findings
        if f.get("severity") in ["CRITICAL", "HIGH"]
    ][:10]  # Limit to top 10

    return {
        "pillar": pillar,
        "status": overall_status,
        "score": int(avg_score),
        "summary": {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "total_findings": len(all_findings),
            "findings_by_severity": findings_by_severity,
        },
        "top_issues": top_issues,
        "check_results": check_results,
        "recommendations": recommendations or [],
    }


def get_account_id(sts_client) -> str:
    """Get the current AWS account ID."""
    try:
        return sts_client.get_caller_identity()["Account"]
    except Exception:
        return "unknown"


def get_all_regions(ec2_client) -> List[str]:
    """Get all enabled AWS regions."""
    try:
        response = ec2_client.describe_regions(
            Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}]
        )
        return [r["RegionName"] for r in response.get("Regions", [])]
    except Exception:
        return ["us-east-1"]  # Fallback to default region


def paginate_results(client, method_name: str, key: str, **kwargs) -> List[Any]:
    """
    Helper to paginate AWS API calls.

    Args:
        client: boto3 client
        method_name: Name of the method to call
        key: Key in response containing the results
        **kwargs: Additional arguments to pass to the method

    Returns:
        List of all results across all pages
    """
    results = []
    paginator = client.get_paginator(method_name)

    try:
        for page in paginator.paginate(**kwargs):
            results.extend(page.get(key, []))
    except Exception:
        # If pagination not supported, try single call
        try:
            method = getattr(client, method_name)
            response = method(**kwargs)
            results = response.get(key, [])
        except Exception:
            pass

    return results
