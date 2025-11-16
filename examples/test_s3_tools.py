#!/usr/bin/env python3
"""
Test S3 tools with live AWS account.

This script tests all S3 visibility tools to ensure they work correctly
with a real AWS account.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import S3 tools
from strandkit.tools.s3 import (
    analyze_s3_bucket,
    find_public_buckets,
    get_s3_cost_analysis,
    analyze_bucket_access,
    find_unused_buckets
)


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)


def test_find_public_buckets():
    """Test finding public S3 buckets."""
    print_section("Testing Public Bucket Detection")

    result = find_public_buckets()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully scanned for public buckets")
    print(f"\nSummary:")
    print(f"  Total buckets: {result['summary']['total_buckets']}")
    print(f"  Public buckets: {result['summary']['public_buckets']}")
    print(f"  Critical risk: {result['summary']['critical']}")
    print(f"  High risk: {result['summary']['high']}")
    print(f"  Medium risk: {result['summary']['medium']}")

    if result['public_buckets']:
        print(f"\nPublic Buckets Found:")
        for bucket in result['public_buckets']:
            risk_icon = "🔴" if bucket['risk_level'] == 'critical' else "⚠️"
            print(f"  {risk_icon} {bucket['bucket_name']} - {bucket['risk_level'].upper()}")
            for reason in bucket['public_reason']:
                print(f"      - {reason}")

    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")

    return result


def test_analyze_bucket(bucket_name):
    """Test analyzing a specific bucket."""
    if not bucket_name:
        print("\n⚠️ Skipping bucket analysis - no bucket name provided")
        return None

    print_section(f"Testing Bucket Analysis: {bucket_name}")

    result = analyze_s3_bucket(bucket_name)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully analyzed bucket")

    # Bucket details
    details = result['bucket_details']
    print(f"\nBucket Details:")
    print(f"  Name: {details['bucket_name']}")
    print(f"  Region: {details['region']}")
    if 'creation_date' in details:
        print(f"  Created: {details['creation_date']}")

    # Security
    security = result['security']
    print(f"\nSecurity:")
    print(f"  Encryption: {'✅ Enabled' if security.get('encryption', {}).get('enabled') else '❌ Disabled'}")

    pab = security.get('public_access_block', {})
    if pab.get('enabled'):
        print(f"  Public Access Block: ✅ Enabled")
        print(f"    Block Public ACLs: {pab.get('block_public_acls')}")
        print(f"    Block Public Policy: {pab.get('block_public_policy')}")
    else:
        print(f"  Public Access Block: ❌ Not configured")

    # Storage
    storage = result['storage']
    print(f"\nStorage:")
    print(f"  Objects: {storage['object_count']:,}")
    print(f"  Total Size: {storage['total_size_gb']:.2f} GB")
    if storage['storage_classes']:
        print(f"  Storage Classes:")
        for sc, count in storage['storage_classes'].items():
            print(f"    {sc}: {count:,} objects")

    # Configuration
    config = result['configuration']
    print(f"\nConfiguration:")
    print(f"  Versioning: {config.get('versioning', {}).get('status', 'Unknown')}")
    print(f"  Lifecycle: {'✅ Enabled' if config.get('lifecycle', {}).get('enabled') else '❌ Not configured'}")
    print(f"  Replication: {'✅ Enabled' if config.get('replication', {}).get('enabled') else '❌ Not configured'}")

    # Cost
    cost = result['cost_estimate']
    print(f"\nCost Estimate:")
    print(f"  Monthly: ${cost['monthly_cost']:.2f}")
    print(f"  Storage: {cost['storage_gb']:.2f} GB")

    # Risk
    risk = result['risk_assessment']
    print(f"\nRisk Assessment:")
    print(f"  Risk Level: {risk['risk_level'].upper()}")
    if risk['risk_factors']:
        print(f"  Risk Factors:")
        for factor in risk['risk_factors']:
            print(f"    - {factor}")

    # Recommendations
    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")

    return result


def test_cost_analysis():
    """Test S3 cost analysis."""
    print_section("Testing S3 Cost Analysis")

    result = get_s3_cost_analysis(days_back=30)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully analyzed S3 costs")

    print(f"\nTime Period: {result['time_period']['days']} days")
    print(f"Total S3 Cost: ${result['total_cost']:.2f}")

    if result.get('by_bucket'):
        print(f"\nTop Buckets by Cost:")
        for bucket in result['by_bucket'][:10]:
            print(f"  {bucket['bucket_name']}: ${bucket['estimated_monthly_cost']:.2f}/month")
            print(f"    Size: {bucket['total_size_gb']:.2f} GB, Objects: {bucket['object_count']:,}")

    if result.get('by_storage_class'):
        print(f"\nStorage Classes:")
        for sc, count in result['by_storage_class'].items():
            print(f"  {sc}: {count:,} objects")

    if result.get('optimization_opportunities'):
        opt = result['optimization_opportunities']
        print(f"\nOptimization Opportunities:")
        print(f"  Potential Savings: ${opt['total_savings']:.2f}/month")
        print(f"  Lifecycle Candidates: {opt['lifecycle_candidates']} bucket(s)")
        print(f"  Intelligent-Tiering Candidates: {opt['intelligent_tiering_candidates']} bucket(s)")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_bucket_access(bucket_name):
    """Test bucket access analysis."""
    if not bucket_name:
        print("\n⚠️ Skipping bucket access analysis - no bucket name provided")
        return None

    print_section(f"Testing Bucket Access Analysis: {bucket_name}")

    result = analyze_bucket_access(bucket_name)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully analyzed bucket access")

    logging = result['logging_status']
    print(f"\nLogging Status:")
    if logging.get('enabled'):
        print(f"  ✅ Enabled")
        print(f"  Target Bucket: {logging.get('target_bucket')}")
        print(f"  Target Prefix: {logging.get('target_prefix', '(none)')}")
    else:
        print(f"  ❌ Not enabled")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_unused_buckets():
    """Test finding unused buckets."""
    print_section("Testing Unused Bucket Detection")

    result = find_unused_buckets(min_age_days=90)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully scanned for unused buckets")

    print(f"\nSummary:")
    print(f"  Empty buckets: {len(result['empty_buckets'])}")
    print(f"  Old-only buckets: {len(result['old_only_buckets'])}")
    print(f"  Total unused: {result['unused_buckets_count']}")
    print(f"  Potential savings: ${result['potential_savings']:.2f}/month")

    if result['empty_buckets']:
        print(f"\nEmpty Buckets:")
        for bucket in result['empty_buckets'][:5]:
            print(f"  - {bucket['bucket_name']}")
            print(f"    Reason: {bucket['reason']}")

    if result['old_only_buckets']:
        print(f"\nBuckets with Only Old Objects:")
        for bucket in result['old_only_buckets'][:5]:
            print(f"  - {bucket['bucket_name']}")
            print(f"    Newest: {bucket['newest_object_date']}")
            print(f"    Objects: {bucket['object_count']:,}")

    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")

    return result


def main():
    """Run all S3 tool tests."""
    print("="*80)
    print("StrandKit S3 Tools - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Find public buckets
    public_scan = test_find_public_buckets()

    # Get first bucket for detailed testing
    bucket_name = None
    if public_scan and public_scan.get('buckets'):
        bucket_name = public_scan['buckets'][0]['bucket_name']

    # Test 2: Analyze specific bucket
    test_analyze_bucket(bucket_name)

    # Test 3: Cost analysis
    test_cost_analysis()

    # Test 4: Bucket access
    test_bucket_access(bucket_name)

    # Test 5: Unused buckets
    test_unused_buckets()

    print_section("Testing Complete")
    print("✅ All S3 tools tested successfully!")


if __name__ == "__main__":
    main()
