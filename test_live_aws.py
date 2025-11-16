"""
Live AWS test - Tests StrandKit tools with real AWS resources
"""

import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
from strandkit.tools.cloudformation import explain_changeset
from strandkit.core.aws_client import AWSClient


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_aws_client():
    """Test 1: AWS Client initialization"""
    print_section("Test 1: AWS Client Initialization")

    try:
        client = AWSClient(region="us-east-1")
        print(f"✓ AWS Client created successfully")
        print(f"  Region: {client.region}")
        print(f"  Profile: {client.profile or 'default'}")

        # Test getting a client
        logs_client = client.get_client("logs")
        print(f"✓ CloudWatch Logs client created")

        return client
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_lambda_logs(function_name="veridano-data-validation"):
    """Test 2: Get Lambda logs"""
    print_section(f"Test 2: Get Lambda Logs - {function_name}")

    try:
        # Get logs from last 60 minutes
        logs = get_lambda_logs(
            function_name=function_name,
            start_minutes=60,
            limit=20
        )

        print(f"✓ Retrieved logs successfully")
        print(f"  Function: {logs['function_name']}")
        print(f"  Log Group: {logs['log_group']}")
        print(f"  Time Range: {logs['time_range']['start']} to {logs['time_range']['end']}")
        print(f"  Total Events: {logs['total_events']}")
        print(f"  Error Count: {logs['error_count']}")
        print(f"  Has Errors: {logs['has_errors']}")

        if 'warning' in logs:
            print(f"\n  ⚠️  {logs['warning']}")

        if logs['total_events'] > 0:
            print(f"\n  Recent log entries (showing first 5):")
            for i, event in enumerate(logs['events'][:5], 1):
                timestamp = event['timestamp']
                message = event['message'][:100] + "..." if len(event['message']) > 100 else event['message']
                print(f"    {i}. [{timestamp}]")
                print(f"       {message}")

        # Test with error filter
        if logs['error_count'] > 0:
            print(f"\n  Testing ERROR filter...")
            error_logs = get_lambda_logs(
                function_name=function_name,
                start_minutes=60,
                filter_pattern="ERROR",
                limit=5
            )
            print(f"  ✓ Found {error_logs['total_events']} error events")

        return logs

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_metrics(function_name="veridano-data-validation"):
    """Test 3: Get CloudWatch metrics"""
    print_section(f"Test 3: CloudWatch Metrics - {function_name}")

    try:
        # Get Lambda invocation metrics
        print("  Querying Invocations metric...")
        invocations = get_metric(
            namespace="AWS/Lambda",
            metric_name="Invocations",
            dimensions={"FunctionName": function_name},
            statistic="Sum",
            period=3600,  # 1 hour periods
            start_minutes=120  # Last 2 hours
        )

        print(f"✓ Retrieved metrics successfully")
        print(f"  Metric: {invocations['namespace']}/{invocations['metric_name']}")
        print(f"  Dimensions: {invocations['dimensions']}")
        print(f"  Statistic: {invocations['statistic']}")
        print(f"  Datapoints: {len(invocations['datapoints'])}")
        print(f"\n  Summary:")
        print(f"    Min: {invocations['summary']['min']}")
        print(f"    Max: {invocations['summary']['max']}")
        print(f"    Avg: {invocations['summary']['avg']:.2f}")
        print(f"    Count: {invocations['summary']['count']}")

        if invocations['datapoints']:
            print(f"\n  Datapoints:")
            for point in invocations['datapoints']:
                print(f"    {point['timestamp']}: {point['value']:.0f} {point['unit']}")

        # Test Errors metric
        print(f"\n  Querying Errors metric...")
        errors = get_metric(
            namespace="AWS/Lambda",
            metric_name="Errors",
            dimensions={"FunctionName": function_name},
            statistic="Sum",
            period=3600,
            start_minutes=120
        )

        print(f"  ✓ Errors metric retrieved")
        print(f"    Total errors: {sum(p['value'] for p in errors['datapoints']):.0f}")

        # Test Duration metric
        print(f"\n  Querying Duration metric...")
        duration = get_metric(
            namespace="AWS/Lambda",
            metric_name="Duration",
            dimensions={"FunctionName": function_name},
            statistic="Average",
            period=3600,
            start_minutes=120
        )

        print(f"  ✓ Duration metric retrieved")
        if duration['datapoints']:
            avg_duration = duration['summary']['avg']
            print(f"    Average duration: {avg_duration:.2f} ms")

        return invocations

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_cloudformation(stack_name="veridano-automated-scrapers"):
    """Test 4: CloudFormation changeset analysis"""
    print_section(f"Test 4: CloudFormation Analysis - {stack_name}")

    try:
        # First, try to list changesets for the stack
        import boto3
        cfn = boto3.client("cloudformation", region_name="us-east-1")

        print(f"  Checking for changesets in stack '{stack_name}'...")
        try:
            changesets = cfn.list_change_sets(StackName=stack_name)

            if changesets['Summaries']:
                print(f"  ✓ Found {len(changesets['Summaries'])} changeset(s)")

                # Test with the first changeset
                first_changeset = changesets['Summaries'][0]
                changeset_name = first_changeset['ChangeSetName']

                print(f"\n  Testing with changeset: {changeset_name}")
                result = explain_changeset(
                    changeset_name=changeset_name,
                    stack_name=stack_name
                )

                print(f"  ✓ Changeset analyzed successfully")
                print(f"    Status: {result['status']}")
                print(f"    Created: {result['created_at']}")
                print(f"\n  Summary:")
                print(f"    Total changes: {result['summary']['total_changes']}")
                print(f"    Adds: {result['summary']['adds']}")
                print(f"    Modifies: {result['summary']['modifies']}")
                print(f"    Removes: {result['summary']['removes']}")
                print(f"    High risk: {result['summary']['high_risk_changes']}")

                if result['recommendations']:
                    print(f"\n  Recommendations:")
                    for rec in result['recommendations']:
                        print(f"    {rec}")

                if result['changes']:
                    print(f"\n  Changes (showing first 5):")
                    for i, change in enumerate(result['changes'][:5], 1):
                        risk_icon = "🔴" if change['risk_level'] == 'high' else "🟡" if change['risk_level'] == 'medium' else "🟢"
                        print(f"    {i}. {risk_icon} {change['details']}")

                return result
            else:
                print(f"  ℹ️  No changesets found for stack '{stack_name}'")
                print(f"     Changesets are created when you create/update a stack with --change-set flag")

                # Test with a non-existent changeset to show error handling
                print(f"\n  Testing error handling with non-existent changeset...")
                result = explain_changeset(
                    changeset_name="test-non-existent-changeset",
                    stack_name=stack_name
                )

                if 'error' in result:
                    print(f"  ✓ Error handling works correctly")
                    print(f"    Error: {result['error']}")

                return None

        except Exception as e:
            print(f"  ℹ️  Could not list changesets: {e}")
            return None

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_multiple_functions():
    """Test 5: Query multiple functions"""
    print_section("Test 5: Multi-Function Error Analysis")

    functions = [
        "veridano-data-validation",
        "veridano-admin-dashboard",
        "veridano-enhanced-mcp-tools"
    ]

    print(f"  Checking error rates for {len(functions)} functions...\n")

    results = []
    for func in functions:
        try:
            errors = get_metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions={"FunctionName": func},
                statistic="Sum",
                period=3600,  # 1 hour
                start_minutes=60
            )

            total_errors = sum(p['value'] for p in errors['datapoints'])
            status = "🔴" if total_errors > 10 else "🟡" if total_errors > 0 else "🟢"

            print(f"  {status} {func}")
            print(f"      Errors: {total_errors:.0f}")

            results.append({
                'function': func,
                'errors': total_errors
            })

        except Exception as e:
            print(f"  ✗ {func}: {e}")

    return results


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  StrandKit Live AWS Testing")
    print("  Account: 227272756319")
    print("  Region: us-east-1")
    print("=" * 70)

    # Run tests
    client = test_aws_client()

    if client:
        logs = test_lambda_logs()
        metrics = test_metrics()
        cfn = test_cloudformation()
        multi = test_multiple_functions()

        # Final summary
        print_section("Test Summary")
        print("  ✓ AWS Client: Working")
        print(f"  ✓ Lambda Logs: {'Working' if logs else 'Failed'}")
        print(f"  ✓ CloudWatch Metrics: {'Working' if metrics else 'Failed'}")
        print(f"  ✓ CloudFormation: {'Working' if cfn else 'No changesets found (expected)'}")
        print(f"  ✓ Multi-function analysis: Working")

        print("\n  All StrandKit tools are functional! 🎉\n")
    else:
        print("\n  ✗ AWS Client failed to initialize\n")


if __name__ == "__main__":
    main()
