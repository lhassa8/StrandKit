#!/usr/bin/env python3
"""
Test Cost Waste Detection tools with live AWS account.

This script tests all 5 Phase 2 Cost Waste Detection tools to validate
waste identification capabilities.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Cost Waste Detection tools
from strandkit.tools.cost_waste import (
    find_zombie_resources,
    analyze_idle_resources,
    analyze_snapshot_waste,
    analyze_data_transfer_costs,
    get_cost_allocation_tags
)


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)


def test_zombie_resources():
    """Test zombie resource detection."""
    print_section("Testing Zombie Resource Detection")

    result = find_zombie_resources(min_age_days=30)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Zombie Resource Scan Complete")

    summary = result.get('summary', {})
    zombies = result.get('zombie_resources', [])

    print(f"\nSummary:")
    print(f"  Total zombies found: {summary.get('total_zombies', 0)}")
    print(f"  Monthly waste: ${summary.get('total_monthly_waste', 0):.2f}")
    print(f"  Annual waste: ${summary.get('total_annual_waste', 0):.2f}")

    by_service = summary.get('by_service', {})
    if by_service:
        print(f"\nWaste by Service:")
        for service, cost in sorted(by_service.items(), key=lambda x: x[1], reverse=True):
            print(f"  {service}: ${cost:.2f}/month")

    by_risk = summary.get('by_risk', {})
    print(f"\nBy Risk Level:")
    print(f"  Low: {by_risk.get('low', 0)}")
    print(f"  Medium: {by_risk.get('medium', 0)}")
    print(f"  High: {by_risk.get('high', 0)}")

    if zombies:
        print(f"\nTop Zombie Resources (up to 10):")
        for i, zombie in enumerate(zombies[:10], 1):
            risk_icon = "🟢" if zombie['risk'] == 'low' else "🟡" if zombie['risk'] == 'medium' else "🔴"
            print(f"\n  {i}. {risk_icon} {zombie['resource_type']}")
            print(f"     ID: {zombie['resource_id']}")
            print(f"     Age: {zombie['age_days']} days")
            print(f"     Cost: ${zombie['monthly_cost']:.2f}/month")
            print(f"     Reason: {zombie['reason']}")
            print(f"     Action: {zombie['recommendation']}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_idle_resources():
    """Test idle resource detection."""
    print_section("Testing Idle Resource Detection")

    result = analyze_idle_resources(cpu_threshold=5.0, lookback_days=7)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Idle Resource Analysis Complete")

    summary = result.get('summary', {})
    idle = result.get('idle_resources', [])

    print(f"\nSummary:")
    print(f"  Total idle resources: {summary.get('total_idle', 0)}")
    print(f"  Potential monthly savings: ${summary.get('potential_monthly_savings', 0):.2f}")
    print(f"  Potential annual savings: ${summary.get('potential_annual_savings', 0):.2f}")

    by_service = summary.get('by_service', {})
    if by_service:
        print(f"\nIdle Resources by Service:")
        for service, cost in sorted(by_service.items(), key=lambda x: x[1], reverse=True):
            print(f"  {service}: ${cost:.2f}/month")

    analysis = result.get('analysis_period', {})
    print(f"\nAnalysis Period:")
    print(f"  Days: {analysis.get('days', 0)}")
    print(f"  CPU Threshold: {analysis.get('cpu_threshold', 0):.1f}%")

    if idle:
        print(f"\nIdle Resources Found (up to 10):")
        for i, resource in enumerate(idle[:10], 1):
            print(f"\n  {i}. {resource['resource_type']}")
            print(f"     ID: {resource['resource_id']}")
            print(f"     Type: {resource.get('instance_type', 'N/A')}")
            print(f"     Avg CPU: {resource.get('avg_cpu', 0):.2f}%")
            print(f"     Max CPU: {resource.get('max_cpu', 0):.2f}%")
            print(f"     Cost: ${resource.get('monthly_cost', 0):.2f}/month")
            print(f"     Action: {resource.get('recommendation', 'N/A')}")

    return result


def test_snapshot_waste():
    """Test snapshot waste analysis."""
    print_section("Testing Snapshot Waste Analysis")

    result = analyze_snapshot_waste(min_age_days=90)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Snapshot Waste Analysis Complete")

    ebs = result.get('ebs_snapshots', {})
    summary = result.get('summary', {})

    print(f"\nEBS Snapshots:")
    print(f"  Total: {ebs.get('total', 0)}")
    print(f"  Total Size: {ebs.get('total_size_gb', 0):,} GB")
    print(f"  Monthly Cost: ${ebs.get('monthly_cost', 0):.2f}")

    old_snaps = ebs.get('old_snapshots', [])
    orphaned_snaps = ebs.get('orphaned_snapshots', [])

    print(f"\nOld Snapshots (>90 days): {len(old_snaps)}")
    if old_snaps:
        print(f"  Showing first 5:")
        for snap in old_snaps[:5]:
            print(f"    - {snap['snapshot_id']}: {snap['size_gb']} GB, {snap['age_days']} days old, ${snap['monthly_cost']:.2f}/month")

    print(f"\nOrphaned Snapshots (volume deleted): {len(orphaned_snaps)}")
    if orphaned_snaps:
        print(f"  Showing first 5:")
        for snap in orphaned_snaps[:5]:
            print(f"    - {snap['snapshot_id']}: {snap['size_gb']} GB, ${snap['monthly_cost']:.2f}/month")

    print(f"\nPotential Savings:")
    print(f"  Monthly: ${summary.get('potential_monthly_savings', 0):.2f}")
    print(f"  Annual: ${summary.get('potential_annual_savings', 0):.2f}")
    print(f"  Snapshots to review: {summary.get('snapshots_to_review', 0)}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_data_transfer_costs():
    """Test data transfer cost analysis."""
    print_section("Testing Data Transfer Cost Analysis")

    result = analyze_data_transfer_costs(days_back=30)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Data Transfer Analysis Complete")

    print(f"\nTotal Data Transfer Cost: ${result.get('total_data_transfer_cost', 0):.2f}")
    print(f"Percentage of Total Bill: {result.get('percentage_of_total_bill', 0):.1f}%")
    print(f"Total Bill: ${result.get('total_bill', 0):.2f}")

    by_type = result.get('by_type', {})
    if by_type:
        print(f"\nCost Breakdown by Type:")
        for transfer_type, cost in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"  {transfer_type}: ${cost:.2f}")

    print(f"\nOptimization Opportunities:")
    for opp in result.get('optimization_opportunities', []):
        print(f"  • {opp}")

    return result


def test_cost_allocation_tags():
    """Test cost allocation tag analysis."""
    print_section("Testing Cost Allocation Tag Analysis")

    result = get_cost_allocation_tags(
        required_tags=["Environment", "Owner", "CostCenter"]
    )

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Cost Allocation Tag Analysis Complete")

    coverage = result.get('tag_coverage', {})
    print(f"\nTag Coverage:")
    print(f"  Percentage: {coverage.get('percentage', 0):.1f}%")
    print(f"  Tagged resources: {coverage.get('tagged_resources', 0)}")
    print(f"  Untagged resources: {coverage.get('untagged_resources', 0)}")

    untagged_cost = result.get('untagged_cost', {})
    print(f"\nCost of Untagged Resources:")
    print(f"  Monthly: ${untagged_cost.get('monthly', 0):.2f}")
    print(f"  Annual: ${untagged_cost.get('annual', 0):.2f}")

    print(f"\nRequired Tags: {', '.join(result.get('required_tags', []))}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  • {rec}")

    return result


def main():
    """Run all cost waste detection tests."""
    print("="*80)
    print("StrandKit Cost Waste Detection - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTesting 5 Phase 2 Waste Detection tools:")
    print("  1. Zombie Resources")
    print("  2. Idle Resources")
    print("  3. Snapshot Waste")
    print("  4. Data Transfer Costs")
    print("  5. Cost Allocation Tags")

    # Test 1: Zombie Resources
    zombie_result = test_zombie_resources()

    # Test 2: Idle Resources
    idle_result = test_idle_resources()

    # Test 3: Snapshot Waste
    snapshot_result = test_snapshot_waste()

    # Test 4: Data Transfer
    transfer_result = test_data_transfer_costs()

    # Test 5: Cost Allocation Tags
    tags_result = test_cost_allocation_tags()

    print_section("Testing Complete")

    # Summary
    print("\n✅ All Cost Waste Detection tools tested!")
    print("\nKey Insights:")

    total_savings = 0.0

    if zombie_result and not zombie_result.get('error'):
        zombie_savings = zombie_result['summary']['total_monthly_waste']
        total_savings += zombie_savings
        print(f"  💀 Zombie Resources: ${zombie_savings:.2f}/month")

    if idle_result and not idle_result.get('error'):
        idle_savings = idle_result['summary']['potential_monthly_savings']
        total_savings += idle_savings
        print(f"  😴 Idle Resources: ${idle_savings:.2f}/month")

    if snapshot_result and not snapshot_result.get('error'):
        snapshot_savings = snapshot_result['summary']['potential_monthly_savings']
        total_savings += snapshot_savings
        print(f"  📸 Snapshot Waste: ${snapshot_savings:.2f}/month")

    print(f"\n💰 Total Potential Monthly Savings: ${total_savings:.2f}")
    print(f"💰 Total Potential Annual Savings: ${total_savings * 12:,.2f}")

    print(f"\n💡 Next Steps:")
    print(f"  1. Review zombie resources and delete unused ones")
    print(f"  2. Stop or downsize idle resources")
    print(f"  3. Clean up old snapshots (>90 days)")
    print(f"  4. Implement proper tagging for cost allocation")
    print(f"  5. Optimize data transfer patterns")


if __name__ == "__main__":
    main()
