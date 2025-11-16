"""
JSON Schema definitions for StrandKit tools.

This module provides utilities for defining and validating tool schemas
in a way that's compatible with AWS Strands and easy for LLMs to understand.

All StrandKit tools follow a consistent schema pattern:
- Clear input parameters with types and descriptions
- Structured JSON output format
- Examples of usage
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ToolParameter:
    """
    Defines a single parameter for a tool.

    Attributes:
        name: Parameter name
        type: Parameter type (string, integer, boolean, array, object)
        description: Human-readable description of the parameter
        required: Whether this parameter is required
        default: Default value if not provided
        enum: List of allowed values (for string types)
    """
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class ToolSchema:
    """
    JSON Schema wrapper for StrandKit tools.

    This class generates JSON schemas that are compatible with:
    - AWS Strands Agents
    - OpenAPI 3.0
    - LLM function calling APIs (OpenAI, Anthropic)

    Example:
        >>> schema = ToolSchema(
        ...     name="get_lambda_logs",
        ...     description="Retrieve CloudWatch logs for a Lambda function",
        ...     parameters=[
        ...         ToolParameter("function_name", "string", "Lambda function name"),
        ...         ToolParameter("start_minutes", "integer", "Minutes to look back", required=False, default=60)
        ...     ]
        ... )
        >>> json_schema = schema.to_json()
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: List[ToolParameter],
        examples: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize a tool schema.

        Args:
            name: Tool name (snake_case recommended)
            description: Clear description of what the tool does
            parameters: List of tool parameters
            examples: Optional list of usage examples
        """
        pass

    def to_json(self) -> Dict[str, Any]:
        """
        Convert schema to JSON Schema format.

        Returns:
            JSON Schema dictionary compatible with AWS Strands
        """
        pass

    def to_openapi(self) -> Dict[str, Any]:
        """
        Convert schema to OpenAPI 3.0 format.

        Returns:
            OpenAPI schema dictionary
        """
        pass
