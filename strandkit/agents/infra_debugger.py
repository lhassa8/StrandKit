"""
Infrastructure Debugger Agent for StrandKit.

This agent helps diagnose AWS infrastructure issues by:
- Analyzing CloudWatch logs and metrics
- Correlating errors with deployment events
- Identifying patterns in failures
- Suggesting remediation steps

Example usage:
    >>> from strandkit import InfraDebuggerAgent
    >>> agent = InfraDebuggerAgent(profile="dev", region="us-east-1")
    >>>
    >>> # Diagnose Lambda errors
    >>> response = agent.run("Why is my auth-api Lambda failing?")
    >>> print(response['answer'])
    >>>
    >>> # Check for metric spikes
    >>> response = agent.run("Show me error spikes in the last 2 hours")
"""

from typing import Any, Dict, List
from strandkit.core.base_agent import BaseAgent
from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
from strandkit.tools.cloudformation import explain_changeset


class InfraDebuggerAgent(BaseAgent):
    """
    Agent specialized in debugging AWS infrastructure issues.

    This agent combines CloudWatch logs, metrics, and CloudFormation
    changeset analysis to help diagnose infrastructure problems.

    Capabilities:
    - Retrieve and analyze Lambda logs
    - Query CloudWatch metrics for anomalies
    - Explain recent infrastructure changes
    - Correlate errors with deployments
    - Suggest debugging steps

    Example:
        >>> agent = InfraDebuggerAgent(region="us-west-2")
        >>> result = agent.run(
        ...     "My Lambda function started erroring 30 minutes ago. "
        ...     "What happened?"
        ... )
        >>> print(result['answer'])
    """

    SYSTEM_PROMPT_FILE = "prompts/infra_debugger_system.md"

    def _get_tools(self) -> List[Any]:
        """
        Return tools for infrastructure debugging.

        Returns:
            List containing:
            - get_lambda_logs
            - get_metric
            - explain_changeset
        """
        pass

    def _process_response(self, raw_response: Any) -> Dict[str, Any]:
        """
        Process agent response with infrastructure-specific formatting.

        Adds:
        - Detected issues summary
        - Suggested next steps
        - Related AWS resources

        Args:
            raw_response: Raw Strands agent response

        Returns:
            Enhanced response dictionary
        """
        pass
