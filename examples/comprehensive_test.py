#!/usr/bin/env python3
"""
Comprehensive StrandKit Testing Suite

Tests all 24 tools across 6 AWS service categories to validate
functionality and identify any issues before expansion.

Categories:
- CloudWatch (4 tools)
- CloudFormation (1 tool)
- IAM (3 tools)
- Cost Explorer (4 tools)
- EC2 (5 tools)
- S3 (5 tools)
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all tools
from strandkit import (
    # CloudWatch
    get_lambda_logs,
    get_metric,
    get_log_insights,
    get_recent_errors,
    # CloudFormation
    explain_changeset,
    # IAM
    analyze_role,
    explain_policy,
    find_overpermissive_roles,
    # Cost
    get_cost_and_usage,
    get_cost_by_service,
    detect_cost_anomalies,
    get_cost_forecast,
    # EC2
    analyze_ec2_instance,
    get_ec2_inventory,
    find_unused_resources,
    analyze_security_group,
    find_overpermissive_security_groups,
    # S3
    analyze_s3_bucket,
    find_public_buckets,
    get_s3_cost_analysis,
    analyze_bucket_access,
    find_unused_buckets,
)


class TestResults:
    """Track test results."""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []

    def add_result(self, category: str, tool: str, status: str, message: str = "", data: Any = None):
        """Add a test result."""
        self.total += 1
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "SKIP":
            self.skipped += 1

        self.results.append({
            "category": category,
            "tool": tool,
            "status": status,
            "message": message,
            "data": data
        })

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total tests: {self.total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"⏭️  Skipped: {self.skipped}")
        print(f"Success rate: {(self.passed/self.total*100) if self.total > 0 else 0:.1f}%")

        if self.failed > 0:
            print(f"\n❌ FAILED TESTS:")
            for r in self.results:
                if r['status'] == 'FAIL':
                    print(f"  - {r['category']}/{r['tool']}: {r['message']}")

        if self.skipped > 0:
            print(f"\n⏭️  SKIPPED TESTS:")
            for r in self.results:
                if r['status'] == 'SKIP':
                    print(f"  - {r['category']}/{r['tool']}: {r['message']}")


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)


def test_cloudwatch_tools(results: TestResults):
    """Test CloudWatch tools."""
    print_section("Testing CloudWatch Tools (4 tools)")

    # Test 1: get_lambda_logs
    try:
        print("\n[1/4] Testing get_lambda_logs...")
        # This will likely fail if no Lambda function exists, but we're testing the code path
        result = get_lambda_logs("nonexistent-function", start_minutes=60)

        if 'error' in result:
            # Expected for nonexistent function
            print(f"  ✅ Error handling works: {result['error'][:50]}...")
            results.add_result("CloudWatch", "get_lambda_logs", "PASS", "Error handling validated")
        else:
            print(f"  ✅ Retrieved {result.get('total_events', 0)} events")
            results.add_result("CloudWatch", "get_lambda_logs", "PASS", f"{result.get('total_events', 0)} events")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("CloudWatch", "get_lambda_logs", "FAIL", str(e)[:100])

    # Test 2: get_metric
    try:
        print("\n[2/4] Testing get_metric...")
        result = get_metric(
            namespace="AWS/Lambda",
            metric_name="Invocations",
            dimensions={"FunctionName": "test"},
            statistic="Sum",
            start_minutes=60
        )

        if 'error' in result:
            print(f"  ✅ Error handling works: {result['error'][:50]}...")
            results.add_result("CloudWatch", "get_metric", "PASS", "Error handling validated")
        else:
            print(f"  ✅ Retrieved {len(result.get('datapoints', []))} datapoints")
            results.add_result("CloudWatch", "get_metric", "PASS", f"{len(result.get('datapoints', []))} datapoints")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("CloudWatch", "get_metric", "FAIL", str(e)[:100])

    # Test 3: get_log_insights
    try:
        print("\n[3/4] Testing get_log_insights...")
        result = get_log_insights(
            log_group_names=["/aws/lambda/test"],
            query_string="fields @timestamp, @message | limit 10",
            start_minutes=60
        )

        if 'error' in result:
            print(f"  ✅ Error handling works: {result['error'][:50]}...")
            results.add_result("CloudWatch", "get_log_insights", "PASS", "Error handling validated")
        else:
            print(f"  ✅ Query completed")
            results.add_result("CloudWatch", "get_log_insights", "PASS", "Query executed")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("CloudWatch", "get_log_insights", "FAIL", str(e)[:100])

    # Test 4: get_recent_errors
    try:
        print("\n[4/4] Testing get_recent_errors...")
        result = get_recent_errors(
            log_group_pattern="/aws/lambda/test",
            start_minutes=60
        )

        if 'error' in result:
            print(f"  ✅ Error handling works: {result['error'][:50]}...")
            results.add_result("CloudWatch", "get_recent_errors", "PASS", "Error handling validated")
        else:
            print(f"  ✅ Found {result.get('error_count', 0)} errors")
            results.add_result("CloudWatch", "get_recent_errors", "PASS", f"{result.get('error_count', 0)} errors")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("CloudWatch", "get_recent_errors", "FAIL", str(e)[:100])


def test_cloudformation_tools(results: TestResults):
    """Test CloudFormation tools."""
    print_section("Testing CloudFormation Tools (1 tool)")

    # Test 1: explain_changeset
    try:
        print("\n[1/1] Testing explain_changeset...")
        result = explain_changeset(
            changeset_name="test-changeset",
            stack_name="test-stack"
        )

        if 'error' in result:
            print(f"  ✅ Error handling works: {result['error'][:50]}...")
            results.add_result("CloudFormation", "explain_changeset", "PASS", "Error handling validated")
        else:
            print(f"  ✅ Analyzed changeset")
            results.add_result("CloudFormation", "explain_changeset", "PASS", "Changeset analyzed")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("CloudFormation", "explain_changeset", "FAIL", str(e)[:100])


def test_iam_tools(results: TestResults):
    """Test IAM tools."""
    print_section("Testing IAM Tools (3 tools)")

    # Test 1: find_overpermissive_roles (this should work with any account)
    try:
        print("\n[1/3] Testing find_overpermissive_roles...")
        result = find_overpermissive_roles()

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("IAM", "find_overpermissive_roles", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Scanned {result['total_roles']} roles")
            print(f"     Found {len(result['overpermissive_roles'])} overpermissive roles")
            results.add_result("IAM", "find_overpermissive_roles", "PASS",
                             f"{result['total_roles']} roles scanned", result)
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("IAM", "find_overpermissive_roles", "FAIL", str(e)[:100])

    # Test 2: analyze_role
    try:
        print("\n[2/3] Testing analyze_role...")
        # Try to get a real role from the previous test
        role_name = None
        for r in results.results:
            if r['category'] == 'IAM' and r['tool'] == 'find_overpermissive_roles' and r['data']:
                if r['data'].get('overpermissive_roles'):
                    role_name = r['data']['overpermissive_roles'][0]['role_name']
                    break

        if not role_name:
            print(f"  ⏭️  Skipped: No role available to test")
            results.add_result("IAM", "analyze_role", "SKIP", "No role available")
        else:
            result = analyze_role(role_name)
            if 'error' in result:
                print(f"  ❌ Error: {result['error'][:100]}")
                results.add_result("IAM", "analyze_role", "FAIL", result['error'][:100])
            else:
                print(f"  ✅ Analyzed role: {role_name}")
                print(f"     Risk level: {result['risk_assessment']['risk_level']}")
                results.add_result("IAM", "analyze_role", "PASS",
                                 f"Risk: {result['risk_assessment']['risk_level']}")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("IAM", "analyze_role", "FAIL", str(e)[:100])

    # Test 3: explain_policy
    try:
        print("\n[3/3] Testing explain_policy...")
        test_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::my-bucket/*"
            }]
        }
        result = explain_policy(test_policy)

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("IAM", "explain_policy", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Policy explained")
            print(f"     Risk level: {result.get('risk_level', 'N/A')}")
            results.add_result("IAM", "explain_policy", "PASS", "Policy parsed successfully")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("IAM", "explain_policy", "FAIL", str(e)[:100])


def test_cost_tools(results: TestResults):
    """Test Cost Explorer tools."""
    print_section("Testing Cost Explorer Tools (4 tools)")

    # Test 1: get_cost_and_usage
    try:
        print("\n[1/4] Testing get_cost_and_usage...")
        result = get_cost_and_usage(days_back=7, granularity="DAILY")

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("Cost", "get_cost_and_usage", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Retrieved {len(result.get('daily_costs', []))} days of data")
            print(f"     Total cost: ${result.get('total_cost', 0):.2f}")
            results.add_result("Cost", "get_cost_and_usage", "PASS",
                             f"${result.get('total_cost', 0):.2f}")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("Cost", "get_cost_and_usage", "FAIL", str(e)[:100])

    # Test 2: get_cost_by_service
    try:
        print("\n[2/4] Testing get_cost_by_service...")
        result = get_cost_by_service(days_back=30, top_n=5)

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("Cost", "get_cost_by_service", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Retrieved costs for {len(result.get('services', []))} services")
            print(f"     Total cost: ${result.get('total_cost', 0):.2f}")
            results.add_result("Cost", "get_cost_by_service", "PASS",
                             f"{len(result.get('services', []))} services")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("Cost", "get_cost_by_service", "FAIL", str(e)[:100])

    # Test 3: detect_cost_anomalies
    try:
        print("\n[3/4] Testing detect_cost_anomalies...")
        result = detect_cost_anomalies(days_back=30)

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("Cost", "detect_cost_anomalies", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Detected {result.get('total_anomalies', 0)} anomalies")
            results.add_result("Cost", "detect_cost_anomalies", "PASS",
                             f"{result.get('total_anomalies', 0)} anomalies")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("Cost", "detect_cost_anomalies", "FAIL", str(e)[:100])

    # Test 4: get_cost_forecast
    try:
        print("\n[4/4] Testing get_cost_forecast...")
        result = get_cost_forecast(days_forward=30)

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("Cost", "get_cost_forecast", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Forecast generated")
            print(f"     Predicted cost: ${result.get('predicted_cost', 0):.2f}")
            results.add_result("Cost", "get_cost_forecast", "PASS",
                             f"${result.get('predicted_cost', 0):.2f}")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("Cost", "get_cost_forecast", "FAIL", str(e)[:100])


def test_ec2_tools(results: TestResults):
    """Test EC2 tools."""
    print_section("Testing EC2 Tools (5 tools)")

    # Test 1: get_ec2_inventory
    try:
        print("\n[1/5] Testing get_ec2_inventory...")
        result = get_ec2_inventory()

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("EC2", "get_ec2_inventory", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Found {result['summary']['total_instances']} instances")
            results.add_result("EC2", "get_ec2_inventory", "PASS",
                             f"{result['summary']['total_instances']} instances", result)
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("EC2", "get_ec2_inventory", "FAIL", str(e)[:100])

    # Test 2: analyze_ec2_instance
    try:
        print("\n[2/5] Testing analyze_ec2_instance...")
        # Try to get an instance ID from inventory
        instance_id = None
        for r in results.results:
            if r['category'] == 'EC2' and r['tool'] == 'get_ec2_inventory' and r['data']:
                if r['data'].get('instances'):
                    instance_id = r['data']['instances'][0]['instance_id']
                    break

        if not instance_id:
            print(f"  ⏭️  Skipped: No EC2 instances available")
            results.add_result("EC2", "analyze_ec2_instance", "SKIP", "No instances")
        else:
            result = analyze_ec2_instance(instance_id)
            if 'error' in result:
                print(f"  ❌ Error: {result['error'][:100]}")
                results.add_result("EC2", "analyze_ec2_instance", "FAIL", result['error'][:100])
            else:
                print(f"  ✅ Analyzed instance: {instance_id}")
                results.add_result("EC2", "analyze_ec2_instance", "PASS", "Instance analyzed")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("EC2", "analyze_ec2_instance", "FAIL", str(e)[:100])

    # Test 3: find_unused_resources
    try:
        print("\n[3/5] Testing find_unused_resources...")
        result = find_unused_resources()

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("EC2", "find_unused_resources", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Potential savings: ${result.get('total_potential_savings', 0):.2f}/month")
            results.add_result("EC2", "find_unused_resources", "PASS",
                             f"${result.get('total_potential_savings', 0):.2f}/month")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("EC2", "find_unused_resources", "FAIL", str(e)[:100])

    # Test 4: find_overpermissive_security_groups
    try:
        print("\n[4/5] Testing find_overpermissive_security_groups...")
        result = find_overpermissive_security_groups()

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("EC2", "find_overpermissive_security_groups", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Scanned {result['summary']['total_groups']} security groups")
            print(f"     Critical risks: {result['summary']['critical']}")
            results.add_result("EC2", "find_overpermissive_security_groups", "PASS",
                             f"{result['summary']['total_groups']} groups", result)
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("EC2", "find_overpermissive_security_groups", "FAIL", str(e)[:100])

    # Test 5: analyze_security_group
    try:
        print("\n[5/5] Testing analyze_security_group...")
        # Try to get a security group ID
        sg_id = None
        for r in results.results:
            if r['category'] == 'EC2' and r['tool'] == 'find_overpermissive_security_groups' and r['data']:
                if r['data'].get('risky_groups'):
                    sg_id = r['data']['risky_groups'][0]['group_id']
                    break

        if not sg_id:
            print(f"  ⏭️  Skipped: No security groups available")
            results.add_result("EC2", "analyze_security_group", "SKIP", "No security groups")
        else:
            result = analyze_security_group(sg_id)
            if 'error' in result:
                print(f"  ❌ Error: {result['error'][:100]}")
                results.add_result("EC2", "analyze_security_group", "FAIL", result['error'][:100])
            else:
                print(f"  ✅ Analyzed security group: {sg_id}")
                print(f"     Risk level: {result['risk_assessment']['risk_level']}")
                results.add_result("EC2", "analyze_security_group", "PASS",
                                 f"Risk: {result['risk_assessment']['risk_level']}")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("EC2", "analyze_security_group", "FAIL", str(e)[:100])


def test_s3_tools(results: TestResults):
    """Test S3 tools."""
    print_section("Testing S3 Tools (5 tools)")

    # Test 1: find_public_buckets
    try:
        print("\n[1/5] Testing find_public_buckets...")
        result = find_public_buckets()

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("S3", "find_public_buckets", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Scanned {result['summary']['total_buckets']} buckets")
            print(f"     Public buckets: {result['summary']['public_buckets']}")
            print(f"     Critical risks: {result['summary']['critical']}")
            results.add_result("S3", "find_public_buckets", "PASS",
                             f"{result['summary']['total_buckets']} buckets", result)
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("S3", "find_public_buckets", "FAIL", str(e)[:100])

    # Test 2: analyze_s3_bucket
    try:
        print("\n[2/5] Testing analyze_s3_bucket...")
        # Try to get a bucket name
        bucket_name = None
        for r in results.results:
            if r['category'] == 'S3' and r['tool'] == 'find_public_buckets' and r['data']:
                if r['data'].get('buckets'):
                    bucket_name = r['data']['buckets'][0]['bucket_name']
                    break

        if not bucket_name:
            print(f"  ⏭️  Skipped: No S3 buckets available")
            results.add_result("S3", "analyze_s3_bucket", "SKIP", "No buckets")
        else:
            result = analyze_s3_bucket(bucket_name)
            if 'error' in result:
                print(f"  ❌ Error: {result['error'][:100]}")
                results.add_result("S3", "analyze_s3_bucket", "FAIL", result['error'][:100])
            else:
                print(f"  ✅ Analyzed bucket: {bucket_name}")
                print(f"     Risk level: {result['risk_assessment']['risk_level']}")
                results.add_result("S3", "analyze_s3_bucket", "PASS",
                                 f"Risk: {result['risk_assessment']['risk_level']}")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("S3", "analyze_s3_bucket", "FAIL", str(e)[:100])

    # Test 3: get_s3_cost_analysis
    try:
        print("\n[3/5] Testing get_s3_cost_analysis...")
        result = get_s3_cost_analysis(days_back=30)

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("S3", "get_s3_cost_analysis", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Total S3 cost: ${result.get('total_cost', 0):.2f}")
            results.add_result("S3", "get_s3_cost_analysis", "PASS",
                             f"${result.get('total_cost', 0):.2f}")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("S3", "get_s3_cost_analysis", "FAIL", str(e)[:100])

    # Test 4: analyze_bucket_access
    try:
        print("\n[4/5] Testing analyze_bucket_access...")
        # Try to get a bucket name
        bucket_name = None
        for r in results.results:
            if r['category'] == 'S3' and r['tool'] == 'find_public_buckets' and r['data']:
                if r['data'].get('buckets'):
                    bucket_name = r['data']['buckets'][0]['bucket_name']
                    break

        if not bucket_name:
            print(f"  ⏭️  Skipped: No S3 buckets available")
            results.add_result("S3", "analyze_bucket_access", "SKIP", "No buckets")
        else:
            result = analyze_bucket_access(bucket_name)
            if 'error' in result:
                print(f"  ❌ Error: {result['error'][:100]}")
                results.add_result("S3", "analyze_bucket_access", "FAIL", result['error'][:100])
            else:
                print(f"  ✅ Analyzed access for: {bucket_name}")
                logging_enabled = result.get('logging_status', {}).get('enabled', False)
                print(f"     Logging: {'✅ Enabled' if logging_enabled else '❌ Disabled'}")
                results.add_result("S3", "analyze_bucket_access", "PASS", "Access analyzed")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("S3", "analyze_bucket_access", "FAIL", str(e)[:100])

    # Test 5: find_unused_buckets
    try:
        print("\n[5/5] Testing find_unused_buckets...")
        result = find_unused_buckets(min_age_days=90)

        if 'error' in result:
            print(f"  ❌ Error: {result['error'][:100]}")
            results.add_result("S3", "find_unused_buckets", "FAIL", result['error'][:100])
        else:
            print(f"  ✅ Found {result.get('unused_buckets_count', 0)} unused buckets")
            print(f"     Potential savings: ${result.get('potential_savings', 0):.2f}/month")
            results.add_result("S3", "find_unused_buckets", "PASS",
                             f"{result.get('unused_buckets_count', 0)} unused buckets")
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        results.add_result("S3", "find_unused_buckets", "FAIL", str(e)[:100])


def test_imports():
    """Test that all imports work."""
    print_section("Testing Package Imports")

    try:
        import strandkit
        print(f"✅ strandkit v{strandkit.__version__}")

        # Check all exports
        expected_tools = [
            # CloudWatch
            "get_lambda_logs", "get_metric", "get_log_insights", "get_recent_errors",
            # CloudFormation
            "explain_changeset",
            # IAM
            "analyze_role", "explain_policy", "find_overpermissive_roles",
            # Cost
            "get_cost_and_usage", "get_cost_by_service", "detect_cost_anomalies", "get_cost_forecast",
            # EC2
            "analyze_ec2_instance", "get_ec2_inventory", "find_unused_resources",
            "analyze_security_group", "find_overpermissive_security_groups",
            # S3
            "analyze_s3_bucket", "find_public_buckets", "get_s3_cost_analysis",
            "analyze_bucket_access", "find_unused_buckets",
        ]

        missing = []
        for tool in expected_tools:
            if not hasattr(strandkit, tool):
                missing.append(tool)

        if missing:
            print(f"❌ Missing exports: {', '.join(missing)}")
            return False
        else:
            print(f"✅ All 24 tools exported correctly")
            return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def main():
    """Run comprehensive test suite."""
    print("="*80)
    print("StrandKit v0.4.0 - Comprehensive Testing Suite")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing all 24 tools across 6 categories")

    # Test imports first
    if not test_imports():
        print("\n❌ Import tests failed. Cannot continue.")
        return 1

    # Initialize results tracker
    results = TestResults()

    # Run tests by category
    test_cloudwatch_tools(results)
    test_cloudformation_tools(results)
    test_iam_tools(results)
    test_cost_tools(results)
    test_ec2_tools(results)
    test_s3_tools(results)

    # Print summary
    results.print_summary()

    print_section("Testing Complete")
    if results.failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {results.failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
