"""
Tool schema generation for Strands agents.

This module provides utilities to convert Python functions into
Claude-compatible tool schemas for agent use.
"""

import inspect
from typing import Any, Dict, Callable, get_type_hints, get_origin, get_args, Optional


def generate_tool_schema(func: Callable) -> Dict[str, Any]:
    """
    Generate a Claude-compatible tool schema from a Python function.

    Args:
        func: Python function to convert to tool schema

    Returns:
        Dictionary with tool schema in Claude format

    Example:
        >>> def my_tool(instance_id: str, verbose: bool = False) -> Dict:
        ...     '''Analyze an EC2 instance.'''
        ...     pass
        >>> schema = generate_tool_schema(my_tool)
        >>> schema['name']
        'my_tool'
    """
    # Get function metadata
    name = func.__name__
    doc = inspect.getdoc(func) or f"Execute {name}"

    # Parse docstring for description
    description = doc.split('\n\n')[0] if doc else f"Execute {name}"

    # Get function signature
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Build parameter schema
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    for param_name, param in sig.parameters.items():
        # Skip aws_client parameter (internal)
        if param_name == 'aws_client':
            continue

        param_type = type_hints.get(param_name, Any)
        param_schema = _python_type_to_json_schema(param_type)

        # Extract description from docstring
        param_desc = _extract_param_description(doc, param_name)
        if param_desc:
            param_schema['description'] = param_desc

        parameters['properties'][param_name] = param_schema

        # Mark as required if no default value
        if param.default == inspect.Parameter.empty:
            parameters['required'].append(param_name)

    return {
        "name": name,
        "description": description,
        "input_schema": parameters
    }


def _python_type_to_json_schema(python_type: type) -> Dict[str, Any]:
    """
    Convert Python type hint to JSON Schema type.

    Args:
        python_type: Python type or type hint

    Returns:
        JSON Schema type definition
    """
    # Handle Optional types
    origin = get_origin(python_type)
    if origin is Optional or (origin is type(None)):
        args = get_args(python_type)
        if args:
            return _python_type_to_json_schema(args[0])

    # Map Python types to JSON Schema types
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
        Dict: {"type": "object"},
        Any: {"type": "string"}  # Default to string for Any
    }

    # Handle generic types
    if origin:
        if origin is list:
            return {"type": "array"}
        elif origin is dict:
            return {"type": "object"}

    # Direct type mapping
    return type_map.get(python_type, {"type": "string"})


def _extract_param_description(docstring: Optional[str], param_name: str) -> Optional[str]:
    """
    Extract parameter description from docstring.

    Args:
        docstring: Function docstring
        param_name: Parameter name to find

    Returns:
        Parameter description or None
    """
    if not docstring:
        return None

    lines = docstring.split('\n')
    in_args_section = False

    for i, line in enumerate(lines):
        # Find Args section
        if line.strip().startswith('Args:'):
            in_args_section = True
            continue

        # Exit Args section
        if in_args_section and line.strip() and not line.startswith(' '):
            break

        # Look for parameter
        if in_args_section and param_name in line:
            # Extract description after colon
            if ':' in line:
                desc = line.split(':', 1)[1].strip()

                # Handle multi-line descriptions
                full_desc = [desc]
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    if next_line.strip() and not next_line.startswith('        '):
                        break
                    if next_line.strip():
                        full_desc.append(next_line.strip())

                return ' '.join(full_desc)

    return None


def create_tool_wrapper(func: Callable, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a tool wrapper that combines function and schema.

    Args:
        func: Python function
        schema: Tool schema from generate_tool_schema()

    Returns:
        Tool dictionary with both function and schema
    """
    return {
        'name': schema['name'],
        'description': schema['description'],
        'input_schema': schema['input_schema'],
        'function': func
    }
