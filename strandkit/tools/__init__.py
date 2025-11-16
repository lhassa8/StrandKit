"""
AWS Tools for StrandKit.

This package contains Strands-compatible tools for AWS services:
- cloudwatch: CloudWatch Logs and Metrics tools
- cloudformation: CloudFormation changeset analysis
- iam: IAM policy explanation and analysis

All tools follow consistent patterns:
- Accept simple, well-typed parameters
- Return structured JSON with consistent keys
- Handle pagination automatically
- Include clear error messages
"""

from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
from strandkit.tools.cloudformation import explain_changeset

__all__ = [
    "get_lambda_logs",
    "get_metric",
    "explain_changeset",
]
