"""
StrandKit - Companion SDK for AWS Strands Agents

StrandKit is not a new agent framework; it extends AWS Strands by providing:
- AWS-focused tools (CloudWatch, CloudFormation, IAM)
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

__version__ = "0.2.0"
__author__ = "Your Name"

# Import main agent templates for easy access
from strandkit.agents.infra_debugger import InfraDebuggerAgent

# Import commonly used tools
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
    # Cost tools
    "get_cost_and_usage",
    "get_cost_by_service",
    "detect_cost_anomalies",
    "get_cost_forecast",
]
