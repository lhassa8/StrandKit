"""
AWS Tools for StrandKit.

This package contains Strands-compatible tools for AWS services:
- cloudwatch: CloudWatch Logs and Metrics tools
- cloudwatch_enhanced: Advanced CloudWatch Logs Insights queries
- cloudformation: CloudFormation changeset analysis
- iam: IAM policy analysis and security auditing
- cost: Cost Explorer for spending analysis and forecasting

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
from strandkit.tools.cost import (
    get_cost_and_usage,
    get_cost_by_service,
    detect_cost_anomalies,
    get_cost_forecast
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
    # Cost
    "get_cost_and_usage",
    "get_cost_by_service",
    "detect_cost_anomalies",
    "get_cost_forecast",
]
