#!/usr/bin/env python3
"""
Test EBS optimization tools with live AWS account.

This script tests all 6 Phase 2 EBS optimization tools.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strandkit.tools.ebs import (
    analyze_ebs_volumes,
    analyze_ebs_snapshots_lifecycle,
    get_ebs_iops_recommendations,
    analyze_ebs_encryption,
    find_ebs_volume_anomalies,
    analyze_ami_usage
)

def print_section(title):
    print(f"\n{'='*80}\n{title}\n{'='*80}")

def main():
    print("="*80)
    print("StrandKit EBS Optimization - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Test 1: Analyze EBS Volumes
    print_section("Test 1: Analyze EBS Volumes")
    result = analyze_ebs_volumes()
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ EBS Volume Analysis Complete")
        s = result['summary']
        print(f"\nSummary:")
        print(f"  Total volumes: {s['total_volumes']}")
        print(f"  GP2 volumes: {s['gp2_volumes']}")
        print(f"  IO volumes: {s['io_volumes']}")
        print(f"  Total size: {s['total_size_gb']:,} GB")
        print(f"  Monthly cost: ${s['total_monthly_cost']:.2f}")
        print(f"  Potential savings: ${s['total_monthly_savings']:.2f}/month")
        print(f"  GP2→GP3 migrations: {s['gp2_to_gp3_count']}")
        print(f"  Unattached volumes: {s['unattached_count']}")
        if result['recommendations']:
            print(f"\nTop Recommendations:")
            for rec in result['recommendations'][:3]:
                print(f"  • {rec}")

    # Test 2: Snapshot Lifecycle
    print_section("Test 2: Analyze Snapshot Lifecycle")
    result = analyze_ebs_snapshots_lifecycle(min_age_days=90)
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Snapshot Lifecycle Analysis Complete")
        s = result['summary']
        print(f"\nSummary:")
        print(f"  Total snapshots: {s['total_snapshots']}")
        print(f"  AMI snapshots: {s['ami_snapshots']}")
        print(f"  Orphaned snapshots: {s['orphaned_snapshots']}")
        print(f"  Old snapshots (>90 days): {s['old_snapshots']}")
        print(f"  Total size: {s['total_size_gb']:,} GB")
        print(f"  Monthly cost: ${s['total_monthly_cost']:.2f}")
        print(f"  Potential savings: ${s['potential_monthly_savings']:.2f}/month")

    # Test 3: IOPS Recommendations
    print_section("Test 3: Get IOPS Recommendations")
    result = get_ebs_iops_recommendations()
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ IOPS Recommendations Complete")
        s = result['summary']
        print(f"\nSummary:")
        print(f"  IO volumes analyzed: {s['io_volumes_analyzed']}")
        print(f"  GP3 volumes analyzed: {s['gp3_volumes_analyzed']}")
        print(f"  GP3 migration opportunities: {s['gp3_migration_count']}")
        print(f"  Over-provisioned: {s['over_provisioned_count']}")
        print(f"  Potential savings: ${s['total_monthly_savings']:.2f}/month")

    # Test 4: Encryption Compliance
    print_section("Test 4: Analyze EBS Encryption")
    result = analyze_ebs_encryption()
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Encryption Analysis Complete")
        s = result['summary']
        print(f"\nSummary:")
        print(f"  Total volumes: {s['total_volumes']}")
        print(f"  Encrypted: {s['encrypted_volumes']}")
        print(f"  Unencrypted: {s['unencrypted_volumes']}")
        print(f"  Encryption rate: {s['encryption_rate']:.1f}%")
        print(f"  Default encryption: {s['default_encryption_enabled']}")
        if result['unencrypted_volumes']:
            print(f"\n⚠️  Unencrypted volumes found!")

    # Test 5: Volume Anomalies
    print_section("Test 5: Find Volume Anomalies")
    result = find_ebs_volume_anomalies()
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Volume Anomaly Detection Complete")
        s = result['summary']
        print(f"\nSummary:")
        print(f"  Volumes checked: {s['total_volumes_checked']}")
        print(f"  Performance issues: {s['performance_issues']}")
        print(f"  Total anomalies: {s['total_anomalies']}")

    # Test 6: AMI Usage
    print_section("Test 6: Analyze AMI Usage")
    result = analyze_ami_usage(min_age_days=180)
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ AMI Usage Analysis Complete")
        s = result['summary']
        print(f"\nSummary:")
        print(f"  Total AMIs: {s['total_amis']}")
        print(f"  Unused AMIs: {s['unused_amis']}")
        print(f"  Old AMIs (>180 days): {s['old_amis']}")
        print(f"  Total snapshot size: {s['total_snapshot_size_gb']:,} GB")
        print(f"  Monthly cost: ${s['total_monthly_cost']:.2f}")
        print(f"  Potential savings: ${s['potential_monthly_savings']:.2f}/month")

    print_section("Testing Complete")
    print("\n✅ All 6 EBS optimization tools tested!")

if __name__ == "__main__":
    main()
