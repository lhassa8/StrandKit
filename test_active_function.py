"""
Test with a function that might have recent activity
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strandkit.tools.cloudwatch import get_lambda_logs, get_metric

# Try multiple functions to find one with recent activity
functions_to_test = [
    "veridano-admin-dashboard",
    "veridano-enhanced-mcp-tools",
    "veridano-public-mcp-server",
    "veridano-webhook-manager",
    "veridano-scraper-cisa-rss",
]

print("Searching for functions with recent activity...\n")

for func in functions_to_test:
    print(f"Checking {func}...")

    # Check for recent invocations (last 24 hours)
    metrics = get_metric(
        namespace="AWS/Lambda",
        metric_name="Invocations",
        dimensions={"FunctionName": func},
        statistic="Sum",
        period=3600,  # 1 hour periods
        start_minutes=1440  # 24 hours
    )

    total_invocations = sum(p['value'] for p in metrics['datapoints'])

    if total_invocations > 0:
        print(f"  ✓ Found {total_invocations:.0f} invocations in last 24 hours!")

        # Get logs for this function
        logs = get_lambda_logs(
            function_name=func,
            start_minutes=1440,  # 24 hours
            limit=10
        )

        if logs['total_events'] > 0:
            print(f"  ✓ Found {logs['total_events']} log events")
            print(f"    Errors: {logs['error_count']}")

            print(f"\n  Recent logs:")
            for i, event in enumerate(logs['events'][:5], 1):
                msg = event['message'][:80] + "..." if len(event['message']) > 80 else event['message']
                print(f"    {i}. [{event['timestamp']}]")
                print(f"       {msg}")

            # Check error metrics
            errors = get_metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions={"FunctionName": func},
                statistic="Sum",
                period=3600,
                start_minutes=1440
            )

            total_errors = sum(p['value'] for p in errors['datapoints'])
            print(f"\n  Error rate: {total_errors:.0f} errors out of {total_invocations:.0f} invocations")

            if total_invocations > 0:
                error_rate = (total_errors / total_invocations) * 100
                print(f"  Error percentage: {error_rate:.2f}%")

            break
    else:
        print(f"  No recent invocations")

    print()
