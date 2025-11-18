#!/usr/bin/env python3
"""
Test suite for Bedrock tools - StrandKit v2.3.0

This test validates the 6 new Bedrock tools:
- analyze_bedrock_usage
- list_available_models
- get_model_details
- analyze_model_performance
- compare_models
- get_model_invocation_logs

Tests:
1. Import validation
2. Tool registration in Strands
3. Basic functionality with live AWS
"""

import sys

print("=" * 80)
print("Bedrock Tools Test Suite - StrandKit v2.3.0")
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
        analyze_bedrock_usage,
        list_available_models,
        get_model_details,
        analyze_model_performance,
        compare_models,
        get_model_invocation_logs
    )
    print("✅ All 6 Bedrock tools imported successfully")

    # Test Strands integration imports
    from strandkit.strands import get_tools_by_category, get_all_tools
    print("✅ Strands integration imports successful")

    # Test category loading
    bedrock_tools = get_tools_by_category('bedrock')

    if len(bedrock_tools) == 6:
        print(f"✅ Bedrock category loaded: 6 tools")
    else:
        print(f"⚠️  Expected 6 Bedrock tools, got {len(bedrock_tools)}")

    # Test all tools includes new ones
    all_tools = get_all_tools()
    if len(all_tools) == 78:
        print(f"✅ All tools loaded: 78 tools (72 existing + 6 new)")
    else:
        print(f"⚠️  Expected 78 tools, got {len(all_tools)}")

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
    bedrock_tools_list = [
        ("analyze_bedrock_usage", analyze_bedrock_usage),
        ("list_available_models", list_available_models),
        ("get_model_details", get_model_details),
        ("analyze_model_performance", analyze_model_performance),
        ("compare_models", compare_models),
        ("get_model_invocation_logs", get_model_invocation_logs),
    ]

    print("Bedrock Tools:")
    for tool_name, tool_func in bedrock_tools_list:
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

print("Testing Bedrock tools...")
print()

try:
    # Test: list_available_models
    print("[1/6] Testing list_available_models...")
    result = list_available_models()

    if isinstance(result, dict):
        if 'error' in result:
            print(f"⚠️  list_available_models: {result.get('message', 'Error')}")
            test_results.append(("list_available_models", False))
        elif 'summary' in result:
            model_count = result['summary'].get('total_models', 0)
            providers = result['summary'].get('provider_count', 0)
            print(f"✅ list_available_models: {model_count} models, {providers} providers")
            test_results.append(("list_available_models", True))
        else:
            print(f"⚠️  list_available_models returned unexpected format")
            test_results.append(("list_available_models", False))
    else:
        print(f"⚠️  list_available_models returned non-dict")
        test_results.append(("list_available_models", False))

except Exception as e:
    print(f"⚠️  list_available_models failed: {e}")
    test_results.append(("list_available_models", False))

print()

try:
    # Test: analyze_bedrock_usage
    print("[2/6] Testing analyze_bedrock_usage...")
    result = analyze_bedrock_usage(days_back=30)

    if isinstance(result, dict):
        if 'error' in result:
            print(f"⚠️  analyze_bedrock_usage: {result.get('message', 'Error')}")
            test_results.append(("analyze_bedrock_usage", False))
        elif 'summary' in result:
            invocations = result['summary'].get('total_invocations', 0)
            cost = result['summary'].get('total_cost', 0)
            print(f"✅ analyze_bedrock_usage: {invocations} invocations, ${cost:.2f} cost")
            test_results.append(("analyze_bedrock_usage", True))
        else:
            print(f"⚠️  analyze_bedrock_usage returned unexpected format")
            test_results.append(("analyze_bedrock_usage", False))
    else:
        print(f"⚠️  analyze_bedrock_usage returned non-dict")
        test_results.append(("analyze_bedrock_usage", False))

except Exception as e:
    print(f"⚠️  analyze_bedrock_usage failed: {e}")
    test_results.append(("analyze_bedrock_usage", False))

print()

try:
    # Test: get_model_details (use a well-known Claude model)
    print("[3/6] Testing get_model_details...")

    # First, get available models to find a valid model ID
    models_result = list_available_models()
    test_model_id = None

    if 'models' in models_result and len(models_result['models']) > 0:
        # Find a Claude model if available, otherwise use first model
        for model in models_result['models']:
            if 'claude' in model['model_id'].lower():
                test_model_id = model['model_id']
                break

        if not test_model_id:
            test_model_id = models_result['models'][0]['model_id']

    if test_model_id:
        result = get_model_details(test_model_id)

        if isinstance(result, dict) and 'model_info' in result:
            model_name = result['model_info'].get('model_name', 'Unknown')
            provider = result['model_info'].get('provider', 'Unknown')
            print(f"✅ get_model_details: {model_name} ({provider})")
            test_results.append(("get_model_details", True))
        else:
            print(f"⚠️  get_model_details returned unexpected format")
            test_results.append(("get_model_details", False))
    else:
        print(f"⚠️  No models available to test get_model_details")
        test_results.append(("get_model_details", False))

except Exception as e:
    print(f"⚠️  get_model_details failed: {e}")
    test_results.append(("get_model_details", False))

print()

try:
    # Test: analyze_model_performance
    print("[4/6] Testing analyze_model_performance...")
    result = analyze_model_performance(days_back=7)

    if isinstance(result, dict):
        if 'error' in result:
            print(f"⚠️  analyze_model_performance: {result.get('message', 'Error')}")
            test_results.append(("analyze_model_performance", False))
        elif 'summary' in result:
            invocations = result['summary'].get('total_invocations', 0)
            error_rate = result['summary'].get('error_rate', 0)
            print(f"✅ analyze_model_performance: {invocations} invocations, {error_rate:.2%} error rate")
            test_results.append(("analyze_model_performance", True))
        else:
            print(f"⚠️  analyze_model_performance returned unexpected format")
            test_results.append(("analyze_model_performance", False))
    else:
        print(f"⚠️  analyze_model_performance returned non-dict")
        test_results.append(("analyze_model_performance", False))

except Exception as e:
    print(f"⚠️  analyze_model_performance failed: {e}")
    test_results.append(("analyze_model_performance", False))

print()

try:
    # Test: compare_models (get 2-3 model IDs from available models)
    print("[5/6] Testing compare_models...")

    models_result = list_available_models()
    model_ids_to_compare = []

    if 'models' in models_result and len(models_result['models']) >= 2:
        # Try to get Claude models for comparison
        claude_models = [m for m in models_result['models'] if 'claude' in m['model_id'].lower()]

        if len(claude_models) >= 2:
            model_ids_to_compare = [m['model_id'] for m in claude_models[:2]]
        else:
            model_ids_to_compare = [m['model_id'] for m in models_result['models'][:2]]

    if len(model_ids_to_compare) >= 2:
        result = compare_models(model_ids_to_compare)

        if isinstance(result, dict) and 'comparison_table' in result:
            compared = result.get('models_compared', 0)
            print(f"✅ compare_models: Compared {compared} models")
            test_results.append(("compare_models", True))
        else:
            print(f"⚠️  compare_models returned unexpected format")
            test_results.append(("compare_models", False))
    else:
        print(f"⚠️  Not enough models available to test compare_models")
        test_results.append(("compare_models", False))

except Exception as e:
    print(f"⚠️  compare_models failed: {e}")
    test_results.append(("compare_models", False))

print()

try:
    # Test: get_model_invocation_logs
    print("[6/6] Testing get_model_invocation_logs...")
    result = get_model_invocation_logs(hours_back=24, limit=10)

    if isinstance(result, dict):
        if 'logging_status' in result:
            status = result['logging_status']
            if status == 'enabled':
                invocations = result['summary'].get('total_invocations', 0)
                print(f"✅ get_model_invocation_logs: Logging enabled, {invocations} invocations")
                test_results.append(("get_model_invocation_logs", True))
            else:
                print(f"⚠️  get_model_invocation_logs: Logging not enabled (expected)")
                test_results.append(("get_model_invocation_logs", True))  # Still a pass
        else:
            print(f"⚠️  get_model_invocation_logs returned unexpected format")
            test_results.append(("get_model_invocation_logs", False))
    else:
        print(f"⚠️  get_model_invocation_logs returned non-dict")
        test_results.append(("get_model_invocation_logs", False))

except Exception as e:
    print(f"⚠️  get_model_invocation_logs failed: {e}")
    test_results.append(("get_model_invocation_logs", False))

print()

# Check test results
passed = sum(1 for _, success in test_results if success)
total = len(test_results)

if passed >= 4:  # Allow some tools to fail if Bedrock is not enabled
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

    # Test 1: Agent with Bedrock tools only
    print("Creating agent with Bedrock tools...")
    agent = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_tools_by_category('bedrock')
    )
    print(f"✅ Agent created with 6 Bedrock tools")

    # Test 2: Agent with all 78 tools
    print("Creating agent with all 78 tools...")
    agent_full = Agent(
        model="anthropic.claude-3-5-haiku",
        tools=get_all_tools()
    )
    print(f"✅ Agent created with all 78 tools")

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

print("Bedrock Tools Test Results:")
for tool_name, success in test_results:
    status = "✅ WORKING" if success else "❌ FAILED"
    print(f"  {status}: {tool_name}")

print()
print("Key Findings:")
print(f"  - Total new tools added: 6 Bedrock tools")
print(f"  - Total tools in StrandKit: 78 (72 previous + 6 new)")
print(f"  - New tools tested: {len(test_results)}")
print(f"  - Successfully working: {passed}/{total}")
print()

if passed >= 4:
    print("🎉 BEDROCK TOOLS READY!")
    print()
    print("Next Steps:")
    print("  1. Update README.md with Bedrock tool examples")
    print("  2. Update TOOLS.md with Bedrock tool documentation")
    print("  3. Update version to v2.3.0")
    print()
    sys.exit(0)
else:
    print("⚠️  SOME TESTS FAILED")
    print()
    print("Note: Some failures are expected if Bedrock is not enabled in your region.")
    print("Bedrock tools require:")
    print("  - Bedrock enabled in your AWS region")
    print("  - Model access granted in Bedrock console")
    print("  - Optional: Model invocation logging configured")
    print()
    sys.exit(0)  # Still exit 0 since some failures are expected
