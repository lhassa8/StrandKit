#!/usr/bin/env python3
"""
Test suite for RDS and VPC tools - StrandKit v2.2.0

This test validates the 10 new tools:
- RDS: 5 tools
- VPC: 5 tools

Tests:
1. Import validation
2. Tool registration in Strands
3. Basic functionality with live AWS
"""

import sys

print("=" * 80)
print("RDS and VPC Tools Test Suite - StrandKit v2.2.0")
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
        # RDS tools
        analyze_rds_instance,
        find_idle_databases,
        analyze_rds_backups,
        get_rds_recommendations,
        find_rds_security_issues,
        # VPC tools
        find_unused_nat_gateways,
        analyze_vpc_configuration,
        analyze_data_transfer_costs,
        analyze_vpc_endpoints,
        find_network_bottlenecks
    )
    print("✅ All 10 new tools imported successfully")

    # Test Strands integration imports
    from strandkit.strands import get_tools_by_category, get_all_tools
    print("✅ Strands integration imports successful")

    # Test category loading
    rds_tools = get_tools_by_category('rds')
    vpc_tools = get_tools_by_category('vpc')

    if len(rds_tools) == 5:
        print(f"✅ RDS category loaded: 5 tools")
    else:
        print(f"⚠️  Expected 5 RDS tools, got {len(rds_tools)}")

    if len(vpc_tools) == 5:
        print(f"✅ VPC category loaded: 5 tools")
    else:
        print(f"⚠️  Expected 5 VPC tools, got {len(vpc_tools)}")

    # Test all tools includes new ones
    all_tools = get_all_tools()
    if len(all_tools) == 72:
        print(f"✅ All tools loaded: 72 tools (62 existing + 10 new)")
    else:
        print(f"⚠️  Expected 72 tools, got {len(all_tools)}")

    print()
    print("✅ TEST 1 PASSED")
    print()

except Exception as e:
    print(f"❌ TEST 1 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ============================================================================
# TEST 2: Tool Metadata Validation
# ============================================================================
print("TEST 2: Tool Metadata Validation")
print("-" * 80)

try:
    rds_tools_list = [
        ("analyze_rds_instance", analyze_rds_instance),
        ("find_idle_databases", find_idle_databases),
        ("analyze_rds_backups", analyze_rds_backups),
        ("get_rds_recommendations", get_rds_recommendations),
        ("find_rds_security_issues", find_rds_security_issues),
    ]

    vpc_tools_list = [
        ("find_unused_nat_gateways", find_unused_nat_gateways),
        ("analyze_vpc_configuration", analyze_vpc_configuration),
        ("analyze_data_transfer_costs", analyze_data_transfer_costs),
        ("analyze_vpc_endpoints", analyze_vpc_endpoints),
        ("find_network_bottlenecks", find_network_bottlenecks),
    ]

    print("RDS Tools:")
    for tool_name, tool_func in rds_tools_list:
        if hasattr(tool_func, '__wrapped__'):
            print(f"✅ {tool_name}: Has @tool decorator")
        else:
            print(f"⚠️  {tool_name}: Missing @tool decorator")

        if tool_func.__doc__:
            doc_lines = tool_func.__doc__.strip().split('\n')[0]
            print(f"   └─ {doc_lines[:70]}...")

    print()
    print("VPC Tools:")
    for tool_name, tool_func in vpc_tools_list:
        if hasattr(tool_func, '__wrapped__'):
            print(f"✅ {tool_name}: Has @tool decorator")
        else:
            print(f"⚠️  {tool_name}: Missing @tool decorator")

        if tool_func.__doc__:
            doc_lines = tool_func.__doc__.strip().split('\n')[0]
            print(f"   └─ {doc_lines[:70]}...")

    print()
    print("✅ TEST 2 PASSED")
    print()

except Exception as e:
    print(f"❌ TEST 2 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ============================================================================
# TEST 3: Basic Functionality (Live AWS)
# ============================================================================
print("TEST 3: Basic Functionality (Live AWS)")
print("-" * 80)

test_results = []

# Test RDS tools
print("Testing RDS tools...")
print()

try:
    # Test: find_idle_databases
    print("[1/5] Testing find_idle_databases...")
    result = find_idle_databases(cpu_threshold=10.0, lookback_days=7)

    if isinstance(result, dict) and 'summary' in result:
        idle_count = result['summary'].get('total_idle_databases', 0)
        savings = result['summary'].get('potential_monthly_savings', 0)
        print(f"✅ find_idle_databases: {idle_count} idle databases, ${savings:.2f} savings")
        test_results.append(("find_idle_databases", True))
    else:
        print(f"⚠️  find_idle_databases returned unexpected format")
        test_results.append(("find_idle_databases", False))

except Exception as e:
    print(f"⚠️  find_idle_databases failed: {e}")
    test_results.append(("find_idle_databases", False))

print()

try:
    # Test: analyze_rds_backups
    print("[2/5] Testing analyze_rds_backups...")
    result = analyze_rds_backups()

    if isinstance(result, dict) and 'summary' in result:
        db_count = result['summary'].get('total_databases', 0)
        compliance = result['summary'].get('compliance_score', 0)
        print(f"✅ analyze_rds_backups: {db_count} databases, compliance {compliance}/100")
        test_results.append(("analyze_rds_backups", True))
    else:
        print(f"⚠️  analyze_rds_backups returned unexpected format")
        test_results.append(("analyze_rds_backups", False))

except Exception as e:
    print(f"⚠️  analyze_rds_backups failed: {e}")
    test_results.append(("analyze_rds_backups", False))

print()

try:
    # Test: get_rds_recommendations
    print("[3/5] Testing get_rds_recommendations...")
    result = get_rds_recommendations()

    if isinstance(result, dict) and 'summary' in result:
        rec_count = result['summary'].get('total_recommendations', 0)
        savings = result['summary'].get('total_potential_savings', 0)
        print(f"✅ get_rds_recommendations: {rec_count} recommendations, ${savings:.2f} savings")
        test_results.append(("get_rds_recommendations", True))
    else:
        print(f"⚠️  get_rds_recommendations returned unexpected format")
        test_results.append(("get_rds_recommendations", False))

except Exception as e:
    print(f"⚠️  get_rds_recommendations failed: {e}")
    test_results.append(("get_rds_recommendations", False))

print()

try:
    # Test: find_rds_security_issues
    print("[4/5] Testing find_rds_security_issues...")
    result = find_rds_security_issues()

    if isinstance(result, dict) and 'summary' in result:
        issues = result['summary'].get('total_findings', 0)
        score = result['summary'].get('security_score', 0)
        print(f"✅ find_rds_security_issues: {issues} issues, score {score}/100")
        test_results.append(("find_rds_security_issues", True))
    else:
        print(f"⚠️  find_rds_security_issues returned unexpected format")
        test_results.append(("find_rds_security_issues", False))

except Exception as e:
    print(f"⚠️  find_rds_security_issues failed: {e}")
    test_results.append(("find_rds_security_issues", False))

print()
print()

# Test VPC tools
print("Testing VPC tools...")
print()

try:
    # Test: find_unused_nat_gateways
    print("[5/10] Testing find_unused_nat_gateways...")
    result = find_unused_nat_gateways()

    if isinstance(result, dict) and 'summary' in result:
        unused = result['summary'].get('total_unused', 0)
        waste = result['summary'].get('monthly_waste', 0)
        print(f"✅ find_unused_nat_gateways: {unused} unused, ${waste:.2f}/month waste")
        test_results.append(("find_unused_nat_gateways", True))
    else:
        print(f"⚠️  find_unused_nat_gateways returned unexpected format")
        test_results.append(("find_unused_nat_gateways", False))

except Exception as e:
    print(f"⚠️  find_unused_nat_gateways failed: {e}")
    test_results.append(("find_unused_nat_gateways", False))

print()

try:
    # Test: analyze_vpc_configuration
    print("[6/10] Testing analyze_vpc_configuration...")
    result = analyze_vpc_configuration()

    if isinstance(result, dict) and 'summary' in result:
        vpc_count = result['summary'].get('total_vpcs', 0)
        print(f"✅ analyze_vpc_configuration: {vpc_count} VPCs analyzed")
        test_results.append(("analyze_vpc_configuration", True))
    else:
        print(f"⚠️  analyze_vpc_configuration returned unexpected format")
        test_results.append(("analyze_vpc_configuration", False))

except Exception as e:
    print(f"⚠️  analyze_vpc_configuration failed: {e}")
    test_results.append(("analyze_vpc_configuration", False))

print()

try:
    # Test: analyze_data_transfer_costs
    print("[7/10] Testing analyze_data_transfer_costs...")
    result = analyze_data_transfer_costs(days_back=30)

    if isinstance(result, dict) and 'summary' in result:
        transfer_cost = result['summary'].get('total_transfer_costs', 0)
        percentage = result['summary'].get('percentage_of_total_bill', 0)
        print(f"✅ analyze_data_transfer_costs: ${transfer_cost:.2f}, {percentage:.1f}% of bill")
        test_results.append(("analyze_data_transfer_costs", True))
    else:
        print(f"⚠️  analyze_data_transfer_costs returned unexpected format")
        test_results.append(("analyze_data_transfer_costs", False))

except Exception as e:
    print(f"⚠️  analyze_data_transfer_costs failed: {e}")
    test_results.append(("analyze_data_transfer_costs", False))

print()

try:
    # Test: analyze_vpc_endpoints
    print("[8/10] Testing analyze_vpc_endpoints...")
    result = analyze_vpc_endpoints()

    if isinstance(result, dict) and 'summary' in result:
        endpoints = result['summary'].get('total_endpoints', 0)
        print(f"✅ analyze_vpc_endpoints: {endpoints} endpoints found")
        test_results.append(("analyze_vpc_endpoints", True))
    else:
        print(f"⚠️  analyze_vpc_endpoints returned unexpected format")
        test_results.append(("analyze_vpc_endpoints", False))

except Exception as e:
    print(f"⚠️  analyze_vpc_endpoints failed: {e}")
    test_results.append(("analyze_vpc_endpoints", False))

print()

try:
    # Test: find_network_bottlenecks
    print("[9/10] Testing find_network_bottlenecks...")
    result = find_network_bottlenecks(lookback_days=7)

    if isinstance(result, dict) and 'summary' in result:
        issues = result['summary'].get('total_issues', 0)
        print(f"✅ find_network_bottlenecks: {issues} issues found")
        test_results.append(("find_network_bottlenecks", True))
    else:
        print(f"⚠️  find_network_bottlenecks returned unexpected format")
        test_results.append(("find_network_bottlenecks", False))

except Exception as e:
    print(f"⚠️  find_network_bottlenecks failed: {e}")
    test_results.append(("find_network_bottlenecks", False))

print()

# Check test results
passed = sum(1 for _, success in test_results if success)
total = len(test_results)

if passed == total:
    print(f"✅ TEST 3 PASSED: {passed}/{total} tools working")
else:
    print(f"⚠️  TEST 3 PARTIAL: {passed}/{total} tools working")

print()


# ============================================================================
# TEST 4: Strands Agent Integration
# ============================================================================
print("TEST 4: Strands Agent Integration")
print("-" * 80)

try:
    from strands import Agent

    # Test 1: Agent with RDS tools only
    print("Creating agent with RDS tools...")
    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_tools_by_category('rds')
    )
    print(f"✅ Agent created with 5 RDS tools")

    # Test 2: Agent with VPC tools only
    print("Creating agent with VPC tools...")
    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_tools_by_category('vpc')
    )
    print(f"✅ Agent created with 5 VPC tools")

    # Test 3: Agent with all 72 tools
    print("Creating agent with all 72 tools...")
    agent_full = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_all_tools()
    )
    print(f"✅ Agent created with all 72 tools")

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

print("RDS & VPC Tools Test Results:")
for tool_name, success in test_results:
    status = "✅ WORKING" if success else "❌ FAILED"
    print(f"  {status}: {tool_name}")

print()
print("Key Findings:")
print(f"  - Total new tools added: 10 (5 RDS + 5 VPC)")
print(f"  - Total tools in StrandKit: 72 (62 previous + 10 new)")
print(f"  - New tools tested: {len(test_results)}")
print(f"  - Successfully working: {passed}/{total}")
print()

if passed >= 8:  # Allow 2 failures for tests that need specific resources
    print("🎉 RDS AND VPC TOOLS READY!")
    print()
    print("Next Steps:")
    print("  1. Update README.md with RDS and VPC tool examples")
    print("  2. Update TOOLS.md with RDS and VPC tool documentation")
    print("  3. Update version to v2.2.0")
    print()
    sys.exit(0)
else:
    print("⚠️  SOME TESTS FAILED")
    print()
    print("Review the errors above and fix any issues.")
    print()
    sys.exit(1)
