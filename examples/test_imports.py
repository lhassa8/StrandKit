"""
Test that all StrandKit imports work correctly.

This script verifies the package structure without making AWS calls.
"""

import sys
import os

# Add parent directory to path so we can import strandkit without installing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test all StrandKit imports"""
    print("Testing StrandKit imports...\n")

    errors = []

    # Test core imports
    try:
        from strandkit.core.aws_client import AWSClient
        print("✓ strandkit.core.aws_client.AWSClient")
    except Exception as e:
        errors.append(f"✗ strandkit.core.aws_client.AWSClient: {e}")

    try:
        from strandkit.core.schema import ToolSchema, ToolParameter
        print("✓ strandkit.core.schema (ToolSchema, ToolParameter)")
    except Exception as e:
        errors.append(f"✗ strandkit.core.schema: {e}")

    try:
        from strandkit.core.base_agent import BaseAgent
        print("✓ strandkit.core.base_agent.BaseAgent")
    except Exception as e:
        errors.append(f"✗ strandkit.core.base_agent.BaseAgent: {e}")

    # Test tool imports
    try:
        from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
        print("✓ strandkit.tools.cloudwatch (get_lambda_logs, get_metric)")
    except Exception as e:
        errors.append(f"✗ strandkit.tools.cloudwatch: {e}")

    try:
        from strandkit.tools.cloudformation import explain_changeset
        print("✓ strandkit.tools.cloudformation.explain_changeset")
    except Exception as e:
        errors.append(f"✗ strandkit.tools.cloudformation.explain_changeset: {e}")

    # Test agent imports
    try:
        from strandkit.agents.infra_debugger import InfraDebuggerAgent
        print("✓ strandkit.agents.infra_debugger.InfraDebuggerAgent")
    except Exception as e:
        errors.append(f"✗ strandkit.agents.infra_debugger.InfraDebuggerAgent: {e}")

    # Test top-level imports
    try:
        from strandkit import (
            InfraDebuggerAgent,
            get_lambda_logs,
            get_metric,
            explain_changeset
        )
        print("✓ strandkit (top-level imports)")
    except Exception as e:
        errors.append(f"✗ strandkit top-level: {e}")

    # Print results
    print("\n" + "=" * 60)
    if errors:
        print("IMPORT ERRORS:")
        for error in errors:
            print(f"  {error}")
        print("=" * 60)
        return False
    else:
        print("All imports successful!")
        print("=" * 60)
        return True


def test_function_signatures():
    """Verify function signatures are correct"""
    print("\nTesting function signatures...\n")

    from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
    from strandkit.tools.cloudformation import explain_changeset
    import inspect

    # Check get_lambda_logs signature
    sig = inspect.signature(get_lambda_logs)
    params = list(sig.parameters.keys())
    expected = ['function_name', 'start_minutes', 'filter_pattern', 'limit', 'aws_client']
    if params == expected:
        print(f"✓ get_lambda_logs signature: {params}")
    else:
        print(f"✗ get_lambda_logs: expected {expected}, got {params}")

    # Check get_metric signature
    sig = inspect.signature(get_metric)
    params = list(sig.parameters.keys())
    expected = ['namespace', 'metric_name', 'dimensions', 'statistic', 'period', 'start_minutes', 'aws_client']
    if params == expected:
        print(f"✓ get_metric signature: {params}")
    else:
        print(f"✗ get_metric: expected {expected}, got {params}")

    # Check explain_changeset signature
    sig = inspect.signature(explain_changeset)
    params = list(sig.parameters.keys())
    expected = ['changeset_name', 'stack_name', 'aws_client']
    if params == expected:
        print(f"✓ explain_changeset signature: {params}")
    else:
        print(f"✗ explain_changeset: expected {expected}, got {params}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("StrandKit Import Test")
    print("=" * 60 + "\n")

    success = test_imports()
    test_function_signatures()

    print()
    sys.exit(0 if success else 1)
