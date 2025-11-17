"""
Base Agent class for StrandKit Strands agents.

This module provides the BaseAgent class that uses Claude (Anthropic) to create
AI agents that can reason about AWS infrastructure and use StrandKit tools.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import os


class BaseAgent:
    """
    Base class for all StrandKit Strands agents.

    This class provides an AI agent that can use StrandKit tools to analyze
    AWS infrastructure, answer questions, and provide recommendations.

    Subclasses should:
    1. Define SYSTEM_PROMPT_FILE (path to markdown prompt)
    2. Override _get_tools() to return agent-specific tools
    3. Optionally override _process_response() for custom output formatting

    Attributes:
        profile: AWS profile name for tool execution
        region: AWS region for tool execution
        api_key: Anthropic API key (from env var ANTHROPIC_API_KEY)
        model: Claude model to use (default: claude-3-5-sonnet-20241022)
        max_iterations: Maximum tool-use iterations (default: 10)

    Example:
        >>> from strandkit.strands.agents import InfraDebuggerAgent
        >>> agent = InfraDebuggerAgent(profile="prod", region="us-east-1")
        >>> result = agent.run("Why is my Lambda function failing?")
        >>> print(result['answer'])
    """

    # Subclasses should override this
    SYSTEM_PROMPT_FILE: Optional[str] = None

    def __init__(
        self,
        profile: Optional[str] = None,
        region: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_iterations: int = 10,
        verbose: bool = False
    ):
        """
        Initialize a StrandKit Strands agent.

        Args:
            profile: AWS CLI profile name for tool execution
            region: AWS region for tool execution
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_iterations: Maximum tool-use iterations
            verbose: Whether to print debug information
        """
        self.profile = profile
        self.region = region
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.model = model
        self.max_iterations = max_iterations
        self.verbose = verbose

        # Lazy initialization
        self._client = None
        self._tools = None
        self._system_prompt = None

    def _get_client(self):
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic SDK not installed. Install with: pip install anthropic"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Anthropic client: {e}")

        return self._client

    def _load_system_prompt(self) -> str:
        """
        Load system prompt from markdown file.

        Returns:
            System prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if self.SYSTEM_PROMPT_FILE is None:
            return "You are a helpful AWS infrastructure assistant."

        prompt_path = Path(__file__).parent.parent / self.SYSTEM_PROMPT_FILE
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt file not found: {prompt_path}")

        return prompt_path.read_text()

    def _get_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of tools for this agent.

        Subclasses must override this method.

        Returns:
            List of tool dictionaries with schemas
        """
        raise NotImplementedError("Subclasses must implement _get_tools()")

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with given input.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result
        """
        # Find tool
        tools = self._get_tools()
        tool = None
        for t in tools:
            if t['name'] == tool_name:
                tool = t
                break

        if tool is None:
            return {'error': f'Tool not found: {tool_name}'}

        # Execute tool function
        try:
            func = tool['function']

            # Add AWS client parameters if function accepts them
            import inspect
            sig = inspect.signature(func)
            if 'aws_client' in sig.parameters:
                from strandkit.core.aws_client import AWSClient
                tool_input['aws_client'] = AWSClient(
                    profile=self.profile,
                    region=self.region
                )

            result = func(**tool_input)
            return result

        except Exception as e:
            return {'error': str(e)}

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Run a natural language query against the agent.

        Args:
            query: Natural language question or command
            **kwargs: Additional arguments (not currently used)

        Returns:
            Structured response dictionary containing:
            - answer: Natural language response from the agent
            - tool_calls: List of tools called with their results
            - iterations: Number of agent-tool iterations

        Example:
            >>> agent = InfraDebuggerAgent(region="us-east-1")
            >>> response = agent.run("Show me Lambda errors from the last hour")
            >>> print(response["answer"])
            >>> for call in response["tool_calls"]:
            ...     print(f"Called: {call['tool']}")
        """
        client = self._get_client()

        # Load system prompt and tools
        if self._system_prompt is None:
            self._system_prompt = self._load_system_prompt()

        if self._tools is None:
            self._tools = self._get_tools()

        # Convert tools to Claude format
        claude_tools = []
        for tool in self._tools:
            claude_tools.append({
                'name': tool['name'],
                'description': tool['description'],
                'input_schema': tool['input_schema']
            })

        # Initialize conversation
        messages = [
            {"role": "user", "content": query}
        ]

        tool_calls = []
        iterations = 0

        # Agent loop
        while iterations < self.max_iterations:
            iterations += 1

            if self.verbose:
                print(f"\n[Iteration {iterations}]")
                print(f"Messages: {len(messages)}")

            # Call Claude
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self._system_prompt,
                tools=claude_tools,
                messages=messages
            )

            if self.verbose:
                print(f"Stop reason: {response.stop_reason}")

            # Check stop reason
            if response.stop_reason == 'end_turn':
                # Agent is done, extract final answer
                final_text = ""
                for block in response.content:
                    if block.type == 'text':
                        final_text += block.text

                return {
                    'answer': final_text,
                    'tool_calls': tool_calls,
                    'iterations': iterations
                }

            elif response.stop_reason == 'tool_use':
                # Agent wants to use tools
                assistant_content = []

                for block in response.content:
                    assistant_content.append({
                        'type': block.type,
                        'text': block.text if hasattr(block, 'text') else None,
                        'id': block.id if hasattr(block, 'id') else None,
                        'name': block.name if hasattr(block, 'name') else None,
                        'input': block.input if hasattr(block, 'input') else None
                    })

                # Add assistant message
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute tools
                tool_results = []
                for block in response.content:
                    if block.type == 'tool_use':
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        if self.verbose:
                            print(f"  Calling tool: {tool_name}")
                            print(f"  Input: {json.dumps(tool_input, indent=2)}")

                        # Execute tool
                        result = self._execute_tool(tool_name, tool_input)

                        if self.verbose:
                            print(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")

                        # Record tool call
                        tool_calls.append({
                            'tool': tool_name,
                            'input': tool_input,
                            'result': result
                        })

                        # Add tool result to conversation
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result)
                        })

                # Add user message with tool results
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            else:
                # Unexpected stop reason
                return {
                    'answer': f"Agent stopped unexpectedly: {response.stop_reason}",
                    'tool_calls': tool_calls,
                    'iterations': iterations
                }

        # Max iterations reached
        return {
            'answer': f"Agent reached maximum iterations ({self.max_iterations}) without completing.",
            'tool_calls': tool_calls,
            'iterations': iterations
        }

    def _process_response(self, raw_response: Any) -> Dict[str, Any]:
        """
        Process raw Strands response into structured format.

        Subclasses can override this for custom formatting.

        Args:
            raw_response: Raw response from Claude

        Returns:
            Processed response dictionary
        """
        # Default implementation - just return as-is
        return raw_response
