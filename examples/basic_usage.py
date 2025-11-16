"""
Basic usage examples for StrandKit.

This file demonstrates how to use StrandKit's AWS tools independently,
without the agent framework.
"""

from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
from strandkit.tools.cloudformation import explain_changeset
from strandkit.core.aws_client import AWSClient


def example_lambda_logs():
    """Example: Retrieve Lambda logs"""
    print("=" * 60)
    print("Example 1: Get Lambda Logs")
    print("=" * 60)

    # Option 1: Use default AWS credentials
    logs = get_lambda_logs(
        function_name="my-api-function",
        start_minutes=60,
        filter_pattern="ERROR"
    )

    print(f"Function: {logs['function_name']}")
    print(f"Total events: {logs['total_events']}")
    print(f"Errors found: {logs['error_count']}")

    if logs['has_errors']:
        print("\nError messages:")
        for event in logs['events'][:5]:  # Show first 5
            if 'ERROR' in event['message']:
                print(f"  [{event['timestamp']}] {event['message'][:100]}")

    print()


def example_cloudwatch_metrics():
    """Example: Query CloudWatch metrics"""
    print("=" * 60)
    print("Example 2: Get CloudWatch Metrics")
    print("=" * 60)

    # Query Lambda error metrics
    metrics = get_metric(
        namespace="AWS/Lambda",
        metric_name="Errors",
        dimensions={"FunctionName": "my-api-function"},
        statistic="Sum",
        period=300,  # 5 minutes
        start_minutes=120  # Last 2 hours
    )

    print(f"Metric: {metrics['namespace']}/{metrics['metric_name']}")
    print(f"Dimensions: {metrics['dimensions']}")
    print(f"Summary: {metrics['summary']}")
    print(f"Datapoints: {len(metrics['datapoints'])}")

    if metrics['datapoints']:
        print("\nRecent values:")
        for point in metrics['datapoints'][-5:]:  # Show last 5
            print(f"  [{point['timestamp']}] {point['value']} {point['unit']}")

    print()


def example_cloudformation_changeset():
    """Example: Explain CloudFormation changeset"""
    print("=" * 60)
    print("Example 3: Explain CloudFormation Changeset")
    print("=" * 60)

    result = explain_changeset(
        changeset_name="my-changeset",
        stack_name="my-stack"
    )

    print(f"Changeset: {result['changeset_name']}")
    print(f"Stack: {result['stack_name']}")
    print(f"Status: {result['status']}")
    print(f"Summary: {result['summary']}")

    if result.get('error'):
        print(f"\nError: {result['error']}")
    else:
        print(f"\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  {rec}")

        print(f"\nHigh-risk changes:")
        for change in result['changes']:
            if change['risk_level'] == 'high':
                print(f"  - {change['details']}")

    print()


def example_with_custom_aws_client():
    """Example: Use custom AWS profile and region"""
    print("=" * 60)
    print("Example 4: Custom AWS Profile and Region")
    print("=" * 60)

    # Create AWS client with specific profile and region
    client = AWSClient(profile="dev", region="us-west-2")

    # Use the client with tools
    logs = get_lambda_logs(
        function_name="my-function",
        start_minutes=30,
        aws_client=client
    )

    print(f"Using profile: {client.profile}")
    print(f"Using region: {client.region}")
    print(f"Found {logs['total_events']} log events")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("StrandKit Basic Usage Examples")
    print("=" * 60 + "\n")

    print("NOTE: These examples will make real AWS API calls.")
    print("Uncomment the example functions you want to run.\n")

    # Uncomment to run examples (requires valid AWS credentials)

    # example_lambda_logs()
    # example_cloudwatch_metrics()
    # example_cloudformation_changeset()
    # example_with_custom_aws_client()

    print("\nTo run these examples:")
    print("1. Ensure you have valid AWS credentials configured")
    print("2. Replace function/stack names with your actual resources")
    print("3. Uncomment the example functions above")
    print("4. Run: python examples/basic_usage.py")
