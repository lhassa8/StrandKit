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

__version__ = "0.1.0"
__author__ = "Your Name"

# Import main agent templates for easy access
from strandkit.agents.infra_debugger import InfraDebuggerAgent

# Import commonly used tools
from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
from strandkit.tools.cloudformation import explain_changeset

__all__ = [
    "InfraDebuggerAgent",
    "get_lambda_logs",
    "get_metric",
    "explain_changeset",
]
