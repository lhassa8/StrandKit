"""
Test new StrandKit tools (IAM and Cost Explorer)

This script tests the newly added IAM analyzer and Cost Explorer tools
with real AWS resources.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strandkit.tools.iam import analyze_role, find_overpermissive_roles
from strandkit.tools.cost import (
    get_cost_and_usage,
    get_cost_by_service,
    detect_cost_anomalies,
    get_cost_forecast
)


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_iam_tools():
    """Test IAM analyzer tools"""
    print_section("IAM Analysis Tools")

    # Test 1: Find overpermissive roles
    print("1. Scanning for overpermissive roles...\n")
    try:
        result = find_overpermissive_roles()

        if "error" in result:
            print(f"  ⚠️  {result['error']}")
        else:
            print(f"  Total roles in account: {result['total_roles']}")
            print(f"  Scanned: {result['scanned_roles']}")
            print(f"  Overpermissive roles found: {len(result['overpermissive_roles'])}\n")

            print(f"  Risk Summary:")
            print(f"    🔴 Critical: {result['summary']['critical']}")
            print(f"    🟠 High: {result['summary']['high']}")
            print(f"    🟡 Medium: {result['summary']['medium']}")
            print(f"    🟢 Low: {result['summary']['low']}")

            if result['overpermissive_roles']:
                print(f"\n  Top risky roles:")
                for role in result['overpermissive_roles'][:5]:
                    icon = "🔴" if role['risk_level'] == 'critical' else "🟠" if role['risk_level'] == 'high' else "🟡"
                    print(f"    {icon} {role['role_name']} ({role['risk_level']})")
                    if role['risk_factors']:
                        for factor in role['risk_factors'][:2]:
                            print(f"       - {factor}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 2: Analyze a specific role
    print("\n2. Analyzing a specific role...\n")
    try:
        # Try to analyze a common Lambda execution role
        import boto3
        iam = boto3.client('iam')

        # Get first role
        roles = iam.list_roles(MaxItems=1)
        if roles['Roles']:
            role_name = roles['Roles'][0]['RoleName']

            print(f"  Analyzing role: {role_name}\n")
            analysis = analyze_role(role_name)

            if "error" in analysis:
                print(f"  ⚠️  {analysis['error']}")
            else:
                print(f"  Role ARN: {analysis['role_arn']}")
                print(f"  Created: {analysis['created_date']}")
                print(f"  Attached Policies: {analysis['permissions_summary']['total_policies']}")
                print(f"\n  Risk Assessment:")
                print(f"    Level: {analysis['risk_assessment']['risk_level'].upper()}")

                if analysis['risk_assessment']['risk_factors']:
                    print(f"    Risk Factors:")
                    for factor in analysis['risk_assessment']['risk_factors']:
                        print(f"      - {factor}")

                print(f"\n  Recommendations:")
                for rec in analysis['recommendations']:
                    print(f"    {rec}")

    except Exception as e:
        print(f"  ✗ Error: {e}")


def test_cost_tools():
    """Test Cost Explorer tools"""
    print_section("Cost Explorer Tools")

    # Test 1: Get cost and usage
    print("1. Getting cost and usage (last 30 days)...\n")
    try:
        costs = get_cost_and_usage(days_back=30)

        if "error" in costs:
            print(f"  ⚠️  {costs['error']}")
        else:
            print(f"  Time Period: {costs['time_period']['start']} to {costs['time_period']['end']}")
            print(f"  Total Cost: ${costs['total_cost']:.2f} {costs['currency']}")
            print(f"\n  Summary:")
            print(f"    Average Daily: ${costs['summary']['average_daily']:.2f}")
            print(f"    Min Daily: ${costs['summary']['min_daily']:.2f}")
            print(f"    Max Daily: ${costs['summary']['max_daily']:.2f}")

            if costs['results_by_time']:
                print(f"\n  Recent daily costs (last 5 days):")
                for item in costs['results_by_time'][-5:]:
                    print(f"    {item['date']}: ${item['amount']:.2f}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 2: Cost by service
    print("\n2. Getting cost breakdown by service...\n")
    try:
        service_costs = get_cost_by_service(days_back=30, top_n=10)

        if "error" in service_costs:
            print(f"  ⚠️  {service_costs['error']}")
        else:
            print(f"  Total Cost: ${service_costs['total_cost']:.2f} {service_costs['currency']}")
            print(f"\n  Top 10 services by cost:")

            for svc in service_costs['services']:
                bar_length = int(svc['percentage'] / 2)  # Scale to fit
                bar = "█" * bar_length
                print(f"    {svc['service'][:30]:<30} ${svc['cost']:>8.2f} ({svc['percentage']:>5.1f}%) {bar}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 3: Detect cost anomalies
    print("\n3. Detecting cost anomalies...\n")
    try:
        anomalies = detect_cost_anomalies(days_back=30, threshold_percentage=20)

        if "error" in anomalies:
            print(f"  ⚠️  {anomalies['error']}")
        else:
            print(f"  Baseline average daily cost: ${anomalies['baseline']['average_daily_cost']:.2f}")
            print(f"  Total anomalies detected: {anomalies['total_anomalies']}")

            if anomalies['anomalies']:
                print(f"\n  Anomalous days:")
                for anomaly in anomalies['anomalies']:
                    severity_icon = "🔴" if anomaly['severity'] == 'high' else "🟡" if anomaly['severity'] == 'medium' else "🟢"
                    print(f"    {severity_icon} {anomaly['date']}: ${anomaly['cost']:.2f} (+{anomaly['deviation_percentage']:.1f}%)")

            print(f"\n  Recommendations:")
            for rec in anomalies['recommendations']:
                print(f"    {rec}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 4: Cost forecast
    print("\n4. Getting cost forecast (next 30 days)...\n")
    try:
        forecast = get_cost_forecast(days_forward=30)

        if "error" in forecast:
            print(f"  ⚠️  {forecast['error']}")
        else:
            print(f"  Forecast Period: {forecast['time_period']['start']} to {forecast['time_period']['end']}")
            print(f"  Predicted Cost: ${forecast['forecast']['predicted_cost']:.2f} {forecast['forecast']['currency']}")
            print(f"  Range: ${forecast['forecast']['prediction_interval_lower']:.2f} - ${forecast['forecast']['prediction_interval_upper']:.2f}")

            if forecast['daily_forecast']:
                print(f"\n  Next 5 days forecast:")
                for day in forecast['daily_forecast'][:5]:
                    print(f"    {day['date']}: ${day['amount']:.2f}")

    except Exception as e:
        print(f"  ✗ Error: {e}")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  StrandKit New Tools Test")
    print("  Account: 227272756319")
    print("  Region: us-east-1")
    print("=" * 70)

    test_iam_tools()
    test_cost_tools()

    print("\n" + "=" * 70)
    print("  Testing Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
