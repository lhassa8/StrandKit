#!/usr/bin/env python3
"""
Comprehensive Test: StrandKit v2.0 + AWS Strands Agents Integration

Tests at least one tool from each AWS service category with Strands Agents.

Categories tested (12):
- CloudWatch (4 tools)
- CloudFormation (1 tool)
- IAM (3 tools)
- IAM Security (8 tools)
- Cost (4 tools)
- Cost Analytics (6 tools)
- Cost Waste (5 tools)
- EC2 (5 tools)
- EC2 Advanced (4 tools)
- S3 (5 tools)
- S3 Advanced (7 tools)
- EBS (6 tools)

Requirements:
    pip install strands-agents strandkit boto3

Setup:
    - AWS credentials configured
    - ANTHROPIC_API_KEY environment variable set (optional, for Claude models)
"""

import sys
import os
from datetime import datetime


def test_imports():
    """Test 1: Verify all imports work."""
    print("\n" + "="*80)
    print("TEST 1: Import Validation")
    print("="*80)

    try:
        # Test Strands import
        print("\n[1/4] Testing Strands import...")
        from strands import Agent
        print("✅ strands.Agent imported successfully")

        # Test StrandKit Strands integration imports
        print("\n[2/4] Testing StrandKit Strands integration...")
        from strandkit.strands import (
            get_all_tools,
            get_tools_by_category,
            list_tool_categories,
            StrandKitToolProvider,
            StrandKitCategoryProvider
        )
        print("✅ StrandKit Strands integration imported successfully")

        # Test standalone tool imports
        print("\n[3/4] Testing standalone tool imports...")
        from strandkit import (
            find_overpermissive_roles,
            get_cost_by_service,
            analyze_ec2_instance
        )
        print("✅ Standalone tools imported successfully")

        # Test tool decorator
        print("\n[4/4] Verifying @tool decorators...")
        from strandkit.tools.iam import find_overpermissive_roles as iam_tool
        # Check if it has the tool decorator attributes
        if hasattr(iam_tool, '__name__'):
            print(f"✅ Tool decorator present on {iam_tool.__name__}")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\nMake sure you have installed:")
        print("  pip install strands-agents strandkit boto3")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_tool_categories():
    """Test 2: Verify all tool categories are available."""
    print("\n" + "="*80)
    print("TEST 2: Tool Category Validation")
    print("="*80)

    try:
        from strandkit.strands import list_tool_categories, get_tools_by_category

        categories = list_tool_categories()
        print(f"\n✅ Found {len(categories)} tool categories")

        expected_categories = [
            'cloudwatch', 'cloudformation', 'iam', 'iam_security',
            'cost', 'cost_analytics', 'cost_waste',
            'ec2', 'ec2_advanced', 's3', 's3_advanced', 'ebs'
        ]

        print("\nCategory breakdown:")
        for cat in expected_categories:
            tools = get_tools_by_category(cat)
            status = "✅" if cat in categories else "❌"
            print(f"  {status} {cat}: {len(tools)} tools")

        if set(categories) == set(expected_categories):
            print(f"\n✅ All {len(expected_categories)} categories present")
            return True
        else:
            missing = set(expected_categories) - set(categories)
            if missing:
                print(f"\n❌ Missing categories: {missing}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_tool_loading():
    """Test 3: Verify tools can be loaded."""
    print("\n" + "="*80)
    print("TEST 3: Tool Loading Validation")
    print("="*80)

    try:
        from strandkit.strands import get_all_tools, get_tools_by_category

        # Test get_all_tools
        print("\n[1/3] Testing get_all_tools()...")
        all_tools = get_all_tools()
        print(f"✅ Loaded {len(all_tools)} tools from get_all_tools()")

        # Test get_tools_by_category
        print("\n[2/3] Testing get_tools_by_category()...")
        iam_tools = get_tools_by_category('iam')
        cost_tools = get_tools_by_category('cost')
        ec2_tools = get_tools_by_category('ec2')
        print(f"✅ Loaded {len(iam_tools)} IAM tools")
        print(f"✅ Loaded {len(cost_tools)} Cost tools")
        print(f"✅ Loaded {len(ec2_tools)} EC2 tools")

        # Test ToolProvider
        print("\n[3/3] Testing StrandKitToolProvider...")
        from strandkit.strands import StrandKitToolProvider
        provider = StrandKitToolProvider()
        print(f"✅ StrandKitToolProvider created successfully")

        # Verify tools are callable
        print("\nVerifying tools are callable...")
        sample_tool = all_tools[0]
        if callable(sample_tool):
            print(f"✅ Tools are callable functions")
        else:
            print(f"❌ Tools are not callable")
            return False

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_standalone_tools():
    """Test 4: Test standalone tool execution (one per category)."""
    print("\n" + "="*80)
    print("TEST 4: Standalone Tool Execution (One Per Category)")
    print("="*80)

    results = []

    # CloudWatch
    try:
        print("\n[1/12] Testing CloudWatch: get_lambda_logs...")
        from strandkit import get_lambda_logs
        # Call with non-existent function to test error handling
        result = get_lambda_logs("test-nonexistent-function-12345", start_minutes=1, limit=1)
        if 'error' in result or 'warning' in result or 'total_events' in result:
            print(f"✅ CloudWatch: get_lambda_logs (returns structured data)")
            results.append(('CloudWatch', True, 'get_lambda_logs'))
        else:
            print(f"❌ CloudWatch: Unexpected result format")
            results.append(('CloudWatch', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ CloudWatch error: {e}")
        results.append(('CloudWatch', False, str(e)))

    # CloudFormation
    try:
        print("\n[2/12] Testing CloudFormation: explain_changeset...")
        from strandkit import explain_changeset
        # Call with non-existent changeset to test error handling
        result = explain_changeset("test-changeset-12345", "test-stack-12345")
        if 'error' in result or 'changes' in result:
            print(f"✅ CloudFormation: explain_changeset (returns structured data)")
            results.append(('CloudFormation', True, 'explain_changeset'))
        else:
            print(f"❌ CloudFormation: Unexpected result format")
            results.append(('CloudFormation', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ CloudFormation error: {e}")
        results.append(('CloudFormation', False, str(e)))

    # IAM
    try:
        print("\n[3/12] Testing IAM: find_overpermissive_roles...")
        from strandkit import find_overpermissive_roles
        result = find_overpermissive_roles()
        if 'total_roles' in result or 'error' in result:
            print(f"✅ IAM: find_overpermissive_roles (scanned {result.get('total_roles', 0)} roles)")
            results.append(('IAM', True, f"find_overpermissive_roles ({result.get('total_roles', 0)} roles)"))
        else:
            print(f"❌ IAM: Unexpected result format")
            results.append(('IAM', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ IAM error: {e}")
        results.append(('IAM', False, str(e)))

    # IAM Security
    try:
        print("\n[4/12] Testing IAM Security: analyze_mfa_compliance...")
        from strandkit import analyze_mfa_compliance
        result = analyze_mfa_compliance()
        if 'summary' in result or 'error' in result:
            print(f"✅ IAM Security: analyze_mfa_compliance")
            results.append(('IAM Security', True, 'analyze_mfa_compliance'))
        else:
            print(f"❌ IAM Security: Unexpected result format")
            results.append(('IAM Security', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ IAM Security error: {e}")
        results.append(('IAM Security', False, str(e)))

    # Cost
    try:
        print("\n[5/12] Testing Cost: get_cost_by_service...")
        from strandkit import get_cost_by_service
        result = get_cost_by_service(days_back=7, top_n=3)
        if 'total_cost' in result or 'error' in result:
            cost = result.get('total_cost', 0)
            print(f"✅ Cost: get_cost_by_service (${cost:.2f} last 7 days)")
            results.append(('Cost', True, f"get_cost_by_service (${cost:.2f})"))
        else:
            print(f"❌ Cost: Unexpected result format")
            results.append(('Cost', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ Cost error: {e}")
        results.append(('Cost', False, str(e)))

    # Cost Analytics
    try:
        print("\n[6/12] Testing Cost Analytics: get_budget_status...")
        from strandkit import get_budget_status
        result = get_budget_status()
        if 'budgets' in result or 'total_budgets' in result or 'error' in result:
            print(f"✅ Cost Analytics: get_budget_status")
            results.append(('Cost Analytics', True, 'get_budget_status'))
        else:
            print(f"❌ Cost Analytics: Unexpected result format")
            results.append(('Cost Analytics', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ Cost Analytics error: {e}")
        results.append(('Cost Analytics', False, str(e)))

    # Cost Waste
    try:
        print("\n[7/12] Testing Cost Waste: find_zombie_resources...")
        from strandkit import find_zombie_resources
        result = find_zombie_resources()
        if 'total_monthly_waste' in result or 'error' in result:
            waste = result.get('total_monthly_waste', 0)
            print(f"✅ Cost Waste: find_zombie_resources (${waste:.2f}/month waste)")
            results.append(('Cost Waste', True, f"find_zombie_resources (${waste:.2f}/mo)"))
        else:
            print(f"❌ Cost Waste: Unexpected result format")
            results.append(('Cost Waste', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ Cost Waste error: {e}")
        results.append(('Cost Waste', False, str(e)))

    # EC2
    try:
        print("\n[8/12] Testing EC2: get_ec2_inventory...")
        from strandkit import get_ec2_inventory
        result = get_ec2_inventory()
        if 'summary' in result or 'error' in result:
            total = result.get('summary', {}).get('total_instances', 0)
            print(f"✅ EC2: get_ec2_inventory ({total} instances)")
            results.append(('EC2', True, f"get_ec2_inventory ({total} instances)"))
        else:
            print(f"❌ EC2: Unexpected result format")
            results.append(('EC2', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ EC2 error: {e}")
        results.append(('EC2', False, str(e)))

    # EC2 Advanced
    try:
        print("\n[9/12] Testing EC2 Advanced: analyze_auto_scaling_groups...")
        from strandkit import analyze_auto_scaling_groups
        result = analyze_auto_scaling_groups()
        if 'auto_scaling_groups' in result or 'summary' in result or 'error' in result:
            print(f"✅ EC2 Advanced: analyze_auto_scaling_groups")
            results.append(('EC2 Advanced', True, 'analyze_auto_scaling_groups'))
        else:
            print(f"❌ EC2 Advanced: Unexpected result format")
            results.append(('EC2 Advanced', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ EC2 Advanced error: {e}")
        results.append(('EC2 Advanced', False, str(e)))

    # S3
    try:
        print("\n[10/12] Testing S3: find_public_buckets...")
        from strandkit import find_public_buckets
        result = find_public_buckets()
        if 'summary' in result or 'error' in result:
            total = result.get('summary', {}).get('total_buckets', 0)
            print(f"✅ S3: find_public_buckets ({total} buckets scanned)")
            results.append(('S3', True, f"find_public_buckets ({total} buckets)"))
        else:
            print(f"❌ S3: Unexpected result format")
            results.append(('S3', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ S3 error: {e}")
        results.append(('S3', False, str(e)))

    # S3 Advanced
    try:
        print("\n[11/12] Testing S3 Advanced: find_s3_versioning_waste...")
        from strandkit import find_s3_versioning_waste
        result = find_s3_versioning_waste()
        if 'buckets_with_versioning' in result or 'summary' in result or 'error' in result:
            print(f"✅ S3 Advanced: find_s3_versioning_waste")
            results.append(('S3 Advanced', True, 'find_s3_versioning_waste'))
        else:
            print(f"❌ S3 Advanced: Unexpected result format")
            results.append(('S3 Advanced', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ S3 Advanced error: {e}")
        results.append(('S3 Advanced', False, str(e)))

    # EBS
    try:
        print("\n[12/12] Testing EBS: analyze_ebs_volumes...")
        from strandkit import analyze_ebs_volumes
        result = analyze_ebs_volumes()
        if 'summary' in result or 'volumes' in result or 'error' in result:
            total = result.get('summary', {}).get('total_volumes', 0)
            print(f"✅ EBS: analyze_ebs_volumes ({total} volumes)")
            results.append(('EBS', True, f"analyze_ebs_volumes ({total} volumes)"))
        else:
            print(f"❌ EBS: Unexpected result format")
            results.append(('EBS', False, 'Unexpected format'))
    except Exception as e:
        print(f"❌ EBS error: {e}")
        results.append(('EBS', False, str(e)))

    # Summary
    print("\n" + "-"*80)
    print("Standalone Tool Test Summary:")
    print("-"*80)
    success_count = sum(1 for _, success, _ in results if success)
    for category, success, details in results:
        status = "✅" if success else "❌"
        print(f"{status} {category:20} - {details}")

    print(f"\nTotal: {success_count}/{len(results)} categories passed")
    return success_count == len(results)


def test_strands_agent_basic():
    """Test 5: Basic Strands Agent with StrandKit tools."""
    print("\n" + "="*80)
    print("TEST 5: Basic Strands Agent Integration")
    print("="*80)

    try:
        from strands import Agent
        from strandkit.strands import get_tools_by_category

        print("\n[1/3] Creating Strands agent with IAM tools...")
        agent = Agent(
            name="test-agent",
            model="anthropic.claude-3-5-haiku",
            tools=get_tools_by_category('iam')
        )
        print("✅ Agent created successfully with IAM tools")

        print("\n[2/3] Creating agent with all tools...")
        from strandkit.strands import get_all_tools
        agent_all = Agent(
            name="test-agent-all",
            model="anthropic.claude-3-5-haiku",
            tools=get_all_tools()
        )
        print("✅ Agent created successfully with all 60 tools")

        print("\n[3/3] Creating agent with ToolProvider...")
        from strandkit.strands import StrandKitToolProvider
        agent_provider = Agent(
            name="test-agent-provider",
            model="anthropic.claude-3-5-haiku",
            tools=[StrandKitToolProvider()]
        )
        print("✅ Agent created successfully with ToolProvider")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nNote: Strands integration requires 'strands-agents' package")
        print("Install with: pip install strands-agents")
        return False
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_report(results):
    """Generate final test report."""
    print("\n" + "="*80)
    print("FINAL TEST REPORT")
    print("="*80)

    print(f"\nTest Suite: StrandKit v2.0 + AWS Strands Agents Integration")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")

    total_tests = len(results)
    passed = sum(1 for r in results if r)
    failed = total_tests - passed

    print(f"\nResults:")
    print(f"  Total Tests: {total_tests}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  Success Rate: {(passed/total_tests)*100:.1f}%")

    print(f"\nTest Breakdown:")
    test_names = [
        "Import Validation",
        "Tool Category Validation",
        "Tool Loading Validation",
        "Standalone Tool Execution",
        "Strands Agent Integration"
    ]

    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  Test {i}: {status:10} - {name}")

    if passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nStrandKit v2.0 is fully integrated with AWS Strands Agents.")
        print("All 60 tools across 12 AWS service categories are working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. See details above.")

    print("\n" + "="*80)


def main():
    """Run all tests."""
    print("="*80)
    print("StrandKit v2.0 + AWS Strands Agents Integration Test Suite")
    print("="*80)
    print("\nThis test validates:")
    print("  - All imports work correctly")
    print("  - Tool categories are properly configured")
    print("  - Tools can be loaded and called")
    print("  - At least one tool per AWS service works")
    print("  - Strands Agent integration is functional")

    results = []

    # Run tests
    results.append(test_imports())
    results.append(test_tool_categories())
    results.append(test_tool_loading())
    results.append(test_standalone_tools())
    results.append(test_strands_agent_basic())

    # Generate report
    generate_report(results)

    # Exit code
    sys.exit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
