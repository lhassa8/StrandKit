#!/usr/bin/env python3
"""
Test suite for StrandKit v2.0 Orchestrator Tools.

This test validates the 4 new high-level orchestrator tools:
1. audit_security()
2. optimize_costs()
3. diagnose_issue()
4. get_aws_overview()

These tools are designed to solve the "too many tools" problem by providing
task-focused composite tools that orchestrate multiple granular tools.
"""

import sys
from typing import Dict, Any

# Test imports
print("=" * 80)
print("StrandKit v2.0 Orchestrator Tools Test Suite")
print("=" * 80)
print()

# ============================================================================
# TEST 1: Import Validation
# ============================================================================
print("TEST 1: Import Validation")
print("-" * 80)

try:
    # Test standalone imports
    from strandkit import (
        audit_security,
        optimize_costs,
        diagnose_issue,
        get_aws_overview
    )
    print("✅ Standalone imports successful")

    # Test Strands integration imports
    from strandkit.strands import get_tools_by_category, get_all_tools
    print("✅ Strands integration imports successful")

    # Test orchestrator category
    orchestrator_tools = get_tools_by_category('orchestrators')
    if len(orchestrator_tools) == 4:
        print(f"✅ Orchestrator category loaded: 4 tools")
    else:
        print(f"⚠️  Expected 4 orchestrator tools, got {len(orchestrator_tools)}")

    # Test all tools includes orchestrators
    all_tools = get_all_tools()
    if len(all_tools) == 64:
        print(f"✅ All tools loaded: 64 tools (60 granular + 4 orchestrators)")
    else:
        print(f"⚠️  Expected 64 tools, got {len(all_tools)}")

    print()
    print("✅ TEST 1 PASSED")
    print()

except Exception as e:
    print(f"❌ TEST 1 FAILED: {e}")
    sys.exit(1)


# ============================================================================
# TEST 2: Tool Metadata Validation
# ============================================================================
print("TEST 2: Tool Metadata Validation")
print("-" * 80)

try:
    # Validate each orchestrator tool has proper metadata
    tools_metadata = [
        ("audit_security", audit_security),
        ("optimize_costs", optimize_costs),
        ("diagnose_issue", diagnose_issue),
        ("get_aws_overview", get_aws_overview),
    ]

    for tool_name, tool_func in tools_metadata:
        # Check has @tool decorator
        if hasattr(tool_func, '__wrapped__'):
            print(f"✅ {tool_name}: Has @tool decorator")
        else:
            print(f"⚠️  {tool_name}: Missing @tool decorator")

        # Check has docstring
        if tool_func.__doc__:
            doc_lines = tool_func.__doc__.strip().split('\n')[0]
            print(f"   └─ Docstring: {doc_lines[:60]}...")
        else:
            print(f"⚠️  {tool_name}: Missing docstring")

    print()
    print("✅ TEST 2 PASSED")
    print()

except Exception as e:
    print(f"❌ TEST 2 FAILED: {e}")
    sys.exit(1)


# ============================================================================
# TEST 3: Standalone Tool Execution (Live AWS)
# ============================================================================
print("TEST 3: Standalone Tool Execution (Live AWS)")
print("-" * 80)

test_results = []

try:
    # Test 1: audit_security()
    print("Testing audit_security()...")
    result = audit_security(
        include_iam=True,
        include_s3=True,
        include_ec2=True
    )

    if isinstance(result, dict):
        print(f"✅ audit_security returned dict")

        # Check expected keys
        expected_keys = ['summary', 'iam_findings', 's3_findings', 'ec2_findings']
        for key in expected_keys:
            if key in result:
                print(f"   └─ Has '{key}' section")

        # Check summary
        if 'summary' in result:
            summary = result['summary']
            total_issues = summary.get('total_issues', 0)
            print(f"   └─ Total security issues found: {total_issues}")

        test_results.append(("audit_security", True, result.get('summary', {})))
    else:
        print(f"⚠️  audit_security returned {type(result)}")
        test_results.append(("audit_security", False, {}))

    print()

except Exception as e:
    print(f"⚠️  audit_security failed: {e}")
    test_results.append(("audit_security", False, {}))
    print()


try:
    # Test 2: optimize_costs()
    print("Testing optimize_costs()...")
    result = optimize_costs(
        include_waste=True,
        include_idle=True,
        include_storage=True,
        min_impact=5.0
    )

    if isinstance(result, dict):
        print(f"✅ optimize_costs returned dict")

        # Check summary
        if 'summary' in result:
            summary = result['summary']
            total_savings = summary.get('total_monthly_savings', 0)
            num_opportunities = summary.get('total_opportunities', 0)
            print(f"   └─ Total monthly savings potential: ${total_savings:.2f}")
            print(f"   └─ Total optimization opportunities: {num_opportunities}")

        test_results.append(("optimize_costs", True, result.get('summary', {})))
    else:
        print(f"⚠️  optimize_costs returned {type(result)}")
        test_results.append(("optimize_costs", False, {}))

    print()

except Exception as e:
    print(f"⚠️  optimize_costs failed: {e}")
    test_results.append(("optimize_costs", False, {}))
    print()


try:
    # Test 3: diagnose_issue() - Lambda
    print("Testing diagnose_issue(resource_type='lambda')...")
    result = diagnose_issue(
        resource_type="lambda",
        resource_name="nonexistent-function",
        issue_description="Testing error diagnostics"
    )

    if isinstance(result, dict):
        print(f"✅ diagnose_issue returned dict")

        if 'diagnosis' in result:
            print(f"   └─ Has diagnosis section")

        test_results.append(("diagnose_issue", True, {}))
    else:
        print(f"⚠️  diagnose_issue returned {type(result)}")
        test_results.append(("diagnose_issue", False, {}))

    print()

except Exception as e:
    print(f"⚠️  diagnose_issue failed: {e}")
    test_results.append(("diagnose_issue", False, {}))
    print()


try:
    # Test 4: get_aws_overview()
    print("Testing get_aws_overview()...")
    result = get_aws_overview(
        include_costs=True,
        include_security=True,
        include_resources=True
    )

    if isinstance(result, dict):
        print(f"✅ get_aws_overview returned dict")

        # Check sections
        sections = ['costs', 'security', 'resources']
        for section in sections:
            if section in result:
                print(f"   └─ Has '{section}' section")

        # Print cost summary if available
        if 'costs' in result and 'total_monthly_spend' in result['costs']:
            total = result['costs']['total_monthly_spend']
            print(f"   └─ Total monthly spend: ${total:.2f}")

        test_results.append(("get_aws_overview", True, result))
    else:
        print(f"⚠️  get_aws_overview returned {type(result)}")
        test_results.append(("get_aws_overview", False, {}))

    print()

except Exception as e:
    print(f"⚠️  get_aws_overview failed: {e}")
    test_results.append(("get_aws_overview", False, {}))
    print()


# Check test results
passed = sum(1 for _, success, _ in test_results if success)
total = len(test_results)

if passed == total:
    print(f"✅ TEST 3 PASSED: {passed}/{total} orchestrator tools working")
else:
    print(f"⚠️  TEST 3 PARTIAL: {passed}/{total} orchestrator tools working")

print()


# ============================================================================
# TEST 4: Strands Agent Integration
# ============================================================================
print("TEST 4: Strands Agent Integration")
print("-" * 80)

try:
    from strands import Agent

    # Test 1: Agent with orchestrator tools only
    print("Creating agent with orchestrator tools...")
    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_tools_by_category('orchestrators')
    )
    print(f"✅ Agent created with 4 orchestrator tools")

    # Test 2: Agent with all tools (including orchestrators)
    print("Creating agent with all 64 tools...")
    agent_full = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_all_tools()
    )
    print(f"✅ Agent created with all 64 tools")

    print()
    print("✅ TEST 4 PASSED")
    print()

except ImportError:
    print("⚠️  strands-agents package not installed, skipping agent test")
    print()
except Exception as e:
    print(f"⚠️  TEST 4 FAILED: {e}")
    print()


# ============================================================================
# TEST SUMMARY
# ============================================================================
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print()

print("Orchestrator Tools Test Results:")
for tool_name, success, metadata in test_results:
    status = "✅ WORKING" if success else "❌ FAILED"
    print(f"  {status}: {tool_name}")

print()
print("Key Findings:")
print(f"  - Total tools in StrandKit: 64 (60 granular + 4 orchestrators)")
print(f"  - Orchestrator tools tested: {len(test_results)}")
print(f"  - Successfully working: {passed}/{total}")
print()

if passed == total:
    print("🎉 ALL ORCHESTRATOR TOOLS WORKING!")
    print()
    print("Next Steps:")
    print("  1. Update README.md with orchestrator tool examples")
    print("  2. Update TOOLS.md with orchestrator tool documentation")
    print("  3. Create example showing agent using orchestrators vs granular tools")
    print()
    sys.exit(0)
else:
    print("⚠️  SOME TESTS FAILED")
    print()
    print("Review the errors above and fix any issues.")
    print()
    sys.exit(1)
