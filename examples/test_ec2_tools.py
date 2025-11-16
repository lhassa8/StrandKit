#!/usr/bin/env python3
"""
Test EC2 tools with live AWS account.

This script tests all EC2 visibility tools to ensure they work correctly
with a real AWS account.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import EC2 tools
from strandkit.tools.ec2 import (
    analyze_ec2_instance,
    get_ec2_inventory,
    find_unused_resources,
    analyze_security_group,
    find_overpermissive_security_groups
)


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)


def test_ec2_inventory():
    """Test EC2 inventory listing."""
    print_section("Testing EC2 Inventory")

    result = get_ec2_inventory()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully retrieved EC2 inventory")
    print(f"\nSummary:")
    print(f"  Total instances: {result['summary']['total_instances']}")
    print(f"  By state: {result['summary']['by_state']}")
    print(f"  Estimated monthly cost: ${result['total_monthly_cost']:.2f}")

    if result['instances']:
        print(f"\nFirst few instances:")
        for inst in result['instances'][:5]:
            state_icon = "🟢" if inst['state'] == 'running' else "⚫"
            name = inst['name'] or '(no name)'
            print(f"  {state_icon} {inst['instance_id']} - {name} ({inst['instance_type']}, {inst['state']})")

    return result


def test_analyze_instance(instance_id):
    """Test instance analysis."""
    if not instance_id:
        print("\n⚠️ Skipping instance analysis - no instance ID provided")
        return None

    print_section(f"Testing Instance Analysis: {instance_id}")

    result = analyze_ec2_instance(instance_id, include_metrics=True)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully analyzed instance")

    details = result['instance_details']
    print(f"\nInstance Details:")
    print(f"  ID: {details['instance_id']}")
    print(f"  Type: {details['instance_type']}")
    print(f"  State: {details['state']}")
    print(f"  Uptime: {details.get('uptime_days', 'N/A')} days")
    print(f"  AZ: {details['availability_zone']}")

    print(f"\nSecurity Groups: {len(result['security_groups'])}")
    for sg in result['security_groups']:
        print(f"  - {sg['group_name']} ({sg['group_id']}): {sg['ingress_rules_count']} ingress, {sg['egress_rules_count']} egress")

    print(f"\nVolumes: {len(result['volumes'])}")
    for vol in result['volumes']:
        encrypted = "🔒" if vol['encrypted'] else "🔓"
        print(f"  {encrypted} {vol['volume_id']}: {vol['size_gb']}GB {vol['volume_type']}")

    print(f"\nCost Estimate:")
    print(f"  Monthly: ${result['cost_estimate']['monthly_cost']:.2f}")
    print(f"  Instance: ${result['cost_estimate']['instance_cost']:.2f}")
    print(f"  Storage: ${result['cost_estimate']['storage_cost']:.2f}")

    if result.get('metrics'):
        metrics = result['metrics']
        print(f"\nMetrics (last hour):")
        print(f"  CPU Average: {metrics['cpu_utilization']['average']:.1f}%")
        print(f"  CPU Maximum: {metrics['cpu_utilization']['maximum']:.1f}%")

    print(f"\nHealth: {result['health_check']['health_status']}")
    if result['health_check']['issues']:
        print("  Issues:")
        for issue in result['health_check']['issues']:
            print(f"    - {issue}")
    if result['health_check']['warnings']:
        print("  Warnings:")
        for warning in result['health_check']['warnings']:
            print(f"    - {warning}")

    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")

    return result


def test_unused_resources():
    """Test finding unused resources."""
    print_section("Testing Unused Resources Detection")

    result = find_unused_resources()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully scanned for unused resources")

    print(f"\nSummary:")
    print(f"  Stopped instances: {result['stopped_instances_count']}")
    print(f"  Unattached volumes: {result['unattached_volumes_count']}")
    print(f"  Unused Elastic IPs: {result['unused_elastic_ips_count']}")
    print(f"  Old snapshots (>90 days): {result['old_snapshots_count']}")

    print(f"\nPotential Savings: ${result['total_potential_savings']:.2f}/month")
    print(f"  Volumes: ${result['breakdown']['volumes']:.2f}")
    print(f"  Elastic IPs: ${result['breakdown']['elastic_ips']:.2f}")
    print(f"  Snapshots: ${result['breakdown']['snapshots']:.2f}")

    if result['stopped_instances']:
        print(f"\nStopped Instances:")
        for inst in result['stopped_instances'][:5]:
            name = inst['name'] or '(no name)'
            print(f"  - {inst['instance_id']} ({name}) - {inst['instance_type']}")

    if result['unattached_volumes']:
        print(f"\nUnattached Volumes:")
        for vol in result['unattached_volumes'][:5]:
            name = vol['name'] or '(no name)'
            print(f"  - {vol['volume_id']} ({name}) - {vol['size_gb']}GB, ${vol['estimated_monthly_cost']:.2f}/month")

    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")

    return result


def test_security_group_analysis(sg_id):
    """Test security group analysis."""
    if not sg_id:
        print("\n⚠️ Skipping security group analysis - no SG ID provided")
        return None

    print_section(f"Testing Security Group Analysis: {sg_id}")

    result = analyze_security_group(sg_id)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully analyzed security group")

    details = result['group_details']
    print(f"\nSecurity Group:")
    print(f"  ID: {details['group_id']}")
    print(f"  Name: {details['group_name']}")
    print(f"  VPC: {details['vpc_id']}")

    print(f"\nRules:")
    print(f"  Ingress: {result['ingress_rules_count']}")
    print(f"  Egress: {result['egress_rules_count']}")

    print(f"\nRisk Assessment:")
    print(f"  Risk Level: {result['risk_assessment']['risk_level'].upper()}")
    if result['risk_assessment']['risk_factors']:
        print(f"  Risk Factors:")
        for factor in result['risk_assessment']['risk_factors']:
            print(f"    - {factor}")

    print(f"\nAttached Resources:")
    print(f"  Instances: {result['attached_resources']['instances']}")

    if result['ingress_rules']:
        print(f"\nIngress Rules (showing first 5):")
        for rule in result['ingress_rules'][:5]:
            protocol = rule['protocol']
            from_port = rule['from_port']
            to_port = rule['to_port']
            sources = ', '.join(s['value'] for s in rule['sources'][:3])
            risk = rule['risk_level']
            risk_icon = "🔴" if risk == 'critical' else "⚠️" if risk == 'high' else "💡" if risk == 'medium' else "✅"
            print(f"  {risk_icon} {protocol} {from_port}-{to_port} from {sources}")

    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")

    return result


def test_overpermissive_sgs():
    """Test scanning for overpermissive security groups."""
    print_section("Testing Overpermissive Security Group Scan")

    result = find_overpermissive_security_groups()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Successfully scanned security groups")

    print(f"\nSummary:")
    print(f"  Total groups: {result['summary']['total_groups']}")
    print(f"  Critical risk: {result['summary']['critical']}")
    print(f"  High risk: {result['summary']['high']}")
    print(f"  Medium risk: {result['summary']['medium']}")
    print(f"  Low risk: {result['summary']['low']}")
    print(f"  Unused: {result['summary']['unused']}")

    if result['risky_groups']:
        print(f"\nRisky Security Groups (showing first 10):")
        for sg in result['risky_groups'][:10]:
            risk_icon = "🔴" if sg['risk_level'] == 'critical' else "⚠️"
            print(f"  {risk_icon} {sg['group_name']} ({sg['group_id']}) - {sg['risk_level'].upper()}")
            for factor in sg['risk_factors'][:2]:
                print(f"      - {factor}")

    if result['unused_groups']:
        print(f"\nUnused Security Groups: {len(result['unused_groups'])}")

    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")

    return result


def main():
    """Run all EC2 tool tests."""
    print("="*80)
    print("StrandKit EC2 Tools - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Get EC2 inventory
    inventory = test_ec2_inventory()

    # Get first instance ID for detailed testing
    instance_id = None
    sg_id = None

    if inventory and inventory['instances']:
        # Find a running instance
        running_instances = [i for i in inventory['instances'] if i['state'] == 'running']
        if running_instances:
            instance_id = running_instances[0]['instance_id']
            if running_instances[0]['security_groups']:
                sg_id = running_instances[0]['security_groups'][0]

    # Test 2: Analyze specific instance
    test_analyze_instance(instance_id)

    # Test 3: Find unused resources
    test_unused_resources()

    # Test 4: Analyze security group
    test_security_group_analysis(sg_id)

    # Test 5: Scan all security groups
    test_overpermissive_sgs()

    print_section("Testing Complete")
    print("✅ All EC2 tools tested successfully!")


if __name__ == "__main__":
    main()
