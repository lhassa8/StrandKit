"""
Base Agent class for StrandKit.

This module provides the BaseAgent class that wraps AWS Strands agents
with a simpler, more Pythonic API.

The BaseAgent class handles:
- Loading system prompts from markdown files
- Registering tools with the Strands agent
- Managing AWS credentials
- Providing a simple .run() interface
"""

from typing import Any, Dict, List, Optional
from pathlib import Path


class BaseAgent:
    """
    Base class for all StrandKit agents.

    This class wraps an AWS Strands agent and provides:
    - Simplified configuration
    - Tool registration
    - System prompt loading
    - Natural language query interface

    Subclasses should:
    1. Define SYSTEM_PROMPT_FILE (path to markdown prompt)
    2. Override _get_tools() to return agent-specific tools
    3. Optionally override _process_response() for custom output formatting

    Attributes:
        profile: AWS profile name
        region: AWS region
        agent: Underlying Strands agent (initialized lazily)

    Example:
        >>> class MyAgent(BaseAgent):
        ...     SYSTEM_PROMPT_FILE = "prompts/my_agent.md"
        ...
        ...     def _get_tools(self):
        ...         return [get_lambda_logs, get_metric]
        >>>
        >>> agent = MyAgent(profile="dev", region="us-east-1")
        >>> result = agent.run("What's wrong with my Lambda?")
    """

    # Subclasses should override this
    SYSTEM_PROMPT_FILE: Optional[str] = None

    def __init__(
        self,
        profile: Optional[str] = None,
        region: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize a StrandKit agent.

        Args:
            profile: AWS CLI profile name
            region: AWS region
            verbose: Whether to print debug information
        """
        pass

    def _load_system_prompt(self) -> str:
        """
        Load system prompt from markdown file.

        Returns:
            System prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        pass

    def _get_tools(self) -> List[Any]:
        """
        Get list of tools for this agent.

        Subclasses must override this method.

        Returns:
            List of Strands-compatible tool objects
        """
        raise NotImplementedError("Subclasses must implement _get_tools()")

    def _initialize_agent(self) -> None:
        """
        Initialize the underlying Strands agent.

        This is called lazily on first .run() call.
        """
        pass

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Run a natural language query against the agent.

        Args:
            query: Natural language question or command
            **kwargs: Additional arguments passed to Strands agent

        Returns:
            Structured response dictionary containing:
            - answer: Natural language response
            - tool_calls: List of tools called (if any)
            - raw_response: Raw Strands agent response

        Example:
            >>> agent = InfraDebuggerAgent(region="us-east-1")
            >>> response = agent.run("Show me Lambda errors from the last hour")
            >>> print(response["answer"])
        """
        pass

    def _process_response(self, raw_response: Any) -> Dict[str, Any]:
        """
        Process raw Strands response into structured format.

        Subclasses can override this for custom formatting.

        Args:
            raw_response: Raw response from Strands agent

        Returns:
            Processed response dictionary
        """
        pass
