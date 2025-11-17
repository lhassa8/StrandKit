"""
Infrastructure Debugger Agent for StrandKit.

This agent helps diagnose AWS infrastructure issues by analyzing logs,
metrics, and configurations using Claude and StrandKit tools.
"""

from typing import Any, Dict, List
from strandkit.core.base_agent import BaseAgent
from strandkit.strands.registry import get_tools_by_category


class InfraDebuggerAgent(BaseAgent):
    """
    Agent specialized in debugging AWS infrastructure issues.

    This agent uses Claude with StrandKit tools to help diagnose problems across:
    - Lambda functions and CloudWatch logs
    - EC2 instances and performance metrics
    - Auto Scaling Groups and Load Balancers
    - CloudFormation deployments
    - IAM and security issues

    The agent can correlate information from multiple AWS services to identify
    root causes and provide actionable remediation steps.

    Example:
        >>> agent = InfraDebuggerAgent(region="us-east-1")
        >>> result = agent.run(
        ...     "My Lambda function started erroring 30 minutes ago. "
        ...     "What happened?"
        ... )
        >>> print(result['answer'])

        >>> # With AWS profile
        >>> agent = InfraDebuggerAgent(profile="prod", region="us-west-2")
        >>> result = agent.run("Why is my EC2 instance showing high CPU?")

        >>> # Verbose mode to see tool calls
        >>> agent = InfraDebuggerAgent(verbose=True)
        >>> result = agent.run("Check for security group misconfigurations")
    """

    SYSTEM_PROMPT_FILE = "prompts/infra_debugger_system.md"

    def _get_tools(self) -> List[Dict[str, Any]]:
        """
        Get tools for infrastructure debugging.

        Returns comprehensive set of tools for debugging:
        - CloudWatch (logs, metrics, insights)
        - EC2 (instances, security groups, performance)
        - EC2 Advanced (ASG, load balancers, performance analysis)
        - CloudFormation (changeset analysis)
        - IAM (basic role analysis)
        - Cost (for spotting anomalies that might indicate issues)

        Returns:
            List of tool dictionaries with schemas
        """
        tools = []

        # Core debugging tools
        tools.extend(get_tools_by_category('cloudwatch'))
        tools.extend(get_tools_by_category('ec2'))
        tools.extend(get_tools_by_category('ec2_advanced'))
        tools.extend(get_tools_by_category('cloudformation'))

        # Additional context tools
        tools.extend(get_tools_by_category('iam'))
        tools.extend(get_tools_by_category('cost'))

        return tools
