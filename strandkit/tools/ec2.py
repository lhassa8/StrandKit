"""
EC2 and Compute Visibility Tools

This module provides tools for analyzing EC2 instances, security groups,
and compute resources for health, security, and cost optimization.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import sys

# Handle boto3 import
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Warning: boto3 not installed. Install with: pip install boto3", file=sys.stderr)
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

from strandkit.core.aws_client import AWSClient
from strands import tool


@tool
def analyze_ec2_instance(
    instance_id: str,
    include_metrics: bool = True,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of an EC2 instance.

    Analyzes instance configuration, security, attached resources,
    performance metrics, and provides optimization recommendations.

    Args:
        instance_id: EC2 instance ID (e.g., "i-1234567890abcdef0")
        include_metrics: Whether to fetch CloudWatch metrics (default: True)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - instance_details: Core instance information
        - security_groups: Attached security groups with rule counts
        - volumes: EBS volumes (size, type, IOPS, encryption)
        - network: Network interfaces and IPs
        - tags: Instance tags
        - metrics: CloudWatch metrics (if include_metrics=True)
        - cost_estimate: Estimated monthly cost
        - health_check: Instance health assessment
        - recommendations: Optimization suggestions

    Example:
        >>> analysis = analyze_ec2_instance("i-1234567890abcdef0")
        >>> print(f"Instance type: {analysis['instance_details']['instance_type']}")
        >>> print(f"Monthly cost: ${analysis['cost_estimate']['monthly_cost']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2_client = aws_client.get_client("ec2")

        # Get instance details
        response = ec2_client.describe_instances(InstanceIds=[instance_id])

        if not response['Reservations']:
            return {
                "error": f"Instance {instance_id} not found",
                "instance_id": instance_id
            }

        instance = response['Reservations'][0]['Instances'][0]

        # Extract instance details
        instance_details = {
            "instance_id": instance_id,
            "instance_type": instance.get('InstanceType'),
            "state": instance.get('State', {}).get('Name'),
            "launch_time": instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else None,
            "availability_zone": instance.get('Placement', {}).get('AvailabilityZone'),
            "platform": instance.get('Platform', 'linux'),
            "architecture": instance.get('Architecture'),
            "vpc_id": instance.get('VpcId'),
            "subnet_id": instance.get('SubnetId'),
            "private_ip": instance.get('PrivateIpAddress'),
            "public_ip": instance.get('PublicIpAddress'),
            "monitoring_state": instance.get('Monitoring', {}).get('State', 'disabled')
        }

        # Calculate uptime
        if instance.get('LaunchTime'):
            uptime_delta = datetime.now(instance['LaunchTime'].tzinfo) - instance['LaunchTime']
            instance_details['uptime_days'] = uptime_delta.days

        # Security groups
        security_groups = []
        for sg in instance.get('SecurityGroups', []):
            sg_details = ec2_client.describe_security_groups(GroupIds=[sg['GroupId']])
            sg_info = sg_details['SecurityGroups'][0]
            security_groups.append({
                "group_id": sg['GroupId'],
                "group_name": sg['GroupName'],
                "ingress_rules_count": len(sg_info.get('IpPermissions', [])),
                "egress_rules_count": len(sg_info.get('IpPermissionsEgress', []))
            })

        # EBS volumes
        volumes = []
        for bdm in instance.get('BlockDeviceMappings', []):
            if 'Ebs' in bdm:
                volume_id = bdm['Ebs']['VolumeId']
                vol_response = ec2_client.describe_volumes(VolumeIds=[volume_id])
                vol = vol_response['Volumes'][0]
                volumes.append({
                    "volume_id": volume_id,
                    "device_name": bdm.get('DeviceName'),
                    "size_gb": vol.get('Size'),
                    "volume_type": vol.get('VolumeType'),
                    "iops": vol.get('Iops'),
                    "encrypted": vol.get('Encrypted', False),
                    "state": vol.get('State'),
                    "delete_on_termination": bdm['Ebs'].get('DeleteOnTermination', False)
                })

        # Network interfaces
        network_interfaces = []
        for ni in instance.get('NetworkInterfaces', []):
            network_interfaces.append({
                "interface_id": ni.get('NetworkInterfaceId'),
                "private_ip": ni.get('PrivateIpAddress'),
                "public_ip": ni.get('Association', {}).get('PublicIp'),
                "subnet_id": ni.get('SubnetId'),
                "security_groups": [sg['GroupId'] for sg in ni.get('Groups', [])]
            })

        # Tags
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}

        # CloudWatch metrics (if requested)
        metrics = None
        if include_metrics and instance_details['state'] == 'running':
            metrics = _get_instance_metrics(instance_id, aws_client)

        # Cost estimation
        cost_estimate = _estimate_instance_cost(instance_details, volumes)

        # Health check
        health_check = _assess_instance_health(instance_details, volumes, security_groups, tags)

        # Recommendations
        recommendations = _generate_instance_recommendations(
            instance_details, volumes, security_groups, tags, metrics
        )

        return {
            "instance_id": instance_id,
            "instance_details": instance_details,
            "security_groups": security_groups,
            "volumes": volumes,
            "network": network_interfaces,
            "tags": tags,
            "metrics": metrics,
            "cost_estimate": cost_estimate,
            "health_check": health_check,
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "instance_id": instance_id
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "instance_id": instance_id
        }


@tool
def get_ec2_inventory(
    filters: Optional[Dict[str, List[str]]] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get comprehensive inventory of all EC2 instances.

    Lists all EC2 instances with key metrics and summary statistics.

    Args:
        filters: Optional EC2 filters (e.g., {"instance-state-name": ["running"]})
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - instances: List of instance summaries
        - summary: Statistics (total, by state, by type)
        - total_monthly_cost: Estimated total monthly cost

    Example:
        >>> inventory = get_ec2_inventory(filters={"instance-state-name": ["running"]})
        >>> print(f"Running instances: {inventory['summary']['by_state']['running']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2_client = aws_client.get_client("ec2")

        # Build filters
        ec2_filters = []
        if filters:
            for key, values in filters.items():
                ec2_filters.append({"Name": key, "Values": values})

        # Get all instances
        if ec2_filters:
            response = ec2_client.describe_instances(Filters=ec2_filters)
        else:
            response = ec2_client.describe_instances()

        instances = []
        total_cost = 0.0

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance.get('InstanceType')
                state = instance.get('State', {}).get('Name')

                # Get name from tags
                name = None
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break

                # Calculate uptime
                uptime_days = None
                if instance.get('LaunchTime'):
                    uptime_delta = datetime.now(instance['LaunchTime'].tzinfo) - instance['LaunchTime']
                    uptime_days = uptime_delta.days

                # Estimate cost
                cost_info = _estimate_instance_cost(
                    {"instance_type": instance_type, "state": state, "platform": instance.get('Platform', 'linux')},
                    []
                )

                instance_summary = {
                    "instance_id": instance_id,
                    "name": name,
                    "instance_type": instance_type,
                    "state": state,
                    "launch_time": instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else None,
                    "uptime_days": uptime_days,
                    "availability_zone": instance.get('Placement', {}).get('AvailabilityZone'),
                    "private_ip": instance.get('PrivateIpAddress'),
                    "public_ip": instance.get('PublicIpAddress'),
                    "vpc_id": instance.get('VpcId'),
                    "security_groups": [sg['GroupId'] for sg in instance.get('SecurityGroups', [])],
                    "estimated_monthly_cost": cost_info['monthly_cost']
                }

                instances.append(instance_summary)

                if state == 'running':
                    total_cost += cost_info['monthly_cost']

        # Calculate summary statistics
        summary = {
            "total_instances": len(instances),
            "by_state": {},
            "by_type": {},
            "by_az": {}
        }

        for inst in instances:
            # By state
            state = inst['state']
            summary['by_state'][state] = summary['by_state'].get(state, 0) + 1

            # By type
            inst_type = inst['instance_type']
            summary['by_type'][inst_type] = summary['by_type'].get(inst_type, 0) + 1

            # By AZ
            az = inst['availability_zone']
            if az:
                summary['by_az'][az] = summary['by_az'].get(az, 0) + 1

        return {
            "instances": instances,
            "summary": summary,
            "total_monthly_cost": total_cost
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "instances": []
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "instances": []
        }


@tool
def find_unused_resources(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Find unused or underutilized EC2 resources to reduce costs.

    Identifies stopped instances, unattached volumes, unused Elastic IPs,
    and old snapshots.

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - stopped_instances: Instances in stopped state
        - unattached_volumes: EBS volumes not attached to instances
        - unused_elastic_ips: Elastic IPs not associated
        - old_snapshots: Snapshots older than 90 days
        - total_potential_savings: Estimated monthly savings
        - recommendations: Action items

    Example:
        >>> unused = find_unused_resources()
        >>> print(f"Potential savings: ${unused['total_potential_savings']:.2f}/month")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2_client = aws_client.get_client("ec2")

        # Stopped instances
        stopped_response = ec2_client.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
        )

        stopped_instances = []
        stopped_cost = 0.0

        for reservation in stopped_response['Reservations']:
            for instance in reservation['Instances']:
                name = None
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break

                # Calculate how long stopped
                state_transition_reason = instance.get('StateTransitionReason', '')
                stopped_date = None
                if instance.get('LaunchTime'):
                    # Approximate - would need CloudTrail for exact time
                    stopped_date = datetime.now(instance['LaunchTime'].tzinfo)

                stopped_instances.append({
                    "instance_id": instance['InstanceId'],
                    "name": name,
                    "instance_type": instance.get('InstanceType'),
                    "stopped_reason": state_transition_reason,
                    "availability_zone": instance.get('Placement', {}).get('AvailabilityZone')
                })

        # Unattached volumes
        volumes_response = ec2_client.describe_volumes(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )

        unattached_volumes = []
        volume_cost = 0.0

        for volume in volumes_response['Volumes']:
            name = None
            for tag in volume.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break

            size = volume.get('Size', 0)
            volume_type = volume.get('VolumeType', 'gp2')

            # Estimate cost (rough - varies by region and type)
            monthly_cost = size * 0.10  # ~$0.10/GB for gp2
            if volume_type == 'io1' or volume_type == 'io2':
                monthly_cost = size * 0.125

            volume_cost += monthly_cost

            unattached_volumes.append({
                "volume_id": volume['VolumeId'],
                "name": name,
                "size_gb": size,
                "volume_type": volume_type,
                "create_time": volume.get('CreateTime').isoformat() if volume.get('CreateTime') else None,
                "availability_zone": volume.get('AvailabilityZone'),
                "estimated_monthly_cost": monthly_cost
            })

        # Unused Elastic IPs
        eips_response = ec2_client.describe_addresses()

        unused_elastic_ips = []
        eip_cost = 0.0

        for eip in eips_response['Addresses']:
            if 'InstanceId' not in eip and 'NetworkInterfaceId' not in eip:
                # Unassociated EIP costs ~$3.65/month
                eip_cost += 3.65
                unused_elastic_ips.append({
                    "allocation_id": eip.get('AllocationId'),
                    "public_ip": eip.get('PublicIp'),
                    "domain": eip.get('Domain'),
                    "estimated_monthly_cost": 3.65
                })

        # Old snapshots (older than 90 days)
        cutoff_date = datetime.now() - timedelta(days=90)
        snapshots_response = ec2_client.describe_snapshots(OwnerIds=['self'])

        old_snapshots = []
        snapshot_cost = 0.0

        for snapshot in snapshots_response['Snapshots']:
            snapshot_time = snapshot.get('StartTime')
            if snapshot_time and snapshot_time.replace(tzinfo=None) < cutoff_date:
                size = snapshot.get('VolumeSize', 0)
                monthly_cost = size * 0.05  # $0.05/GB for snapshots
                snapshot_cost += monthly_cost

                description = snapshot.get('Description', '')

                old_snapshots.append({
                    "snapshot_id": snapshot['SnapshotId'],
                    "description": description,
                    "size_gb": size,
                    "start_time": snapshot_time.isoformat(),
                    "age_days": (datetime.now() - snapshot_time.replace(tzinfo=None)).days,
                    "estimated_monthly_cost": monthly_cost
                })

        # Total savings
        total_savings = volume_cost + eip_cost + snapshot_cost

        # Recommendations
        recommendations = []
        if stopped_instances:
            recommendations.append(f"⚠️ {len(stopped_instances)} stopped instance(s) found - consider terminating if no longer needed")
        if unattached_volumes:
            recommendations.append(f"💰 {len(unattached_volumes)} unattached volume(s) found - potential savings: ${volume_cost:.2f}/month")
        if unused_elastic_ips:
            recommendations.append(f"💰 {len(unused_elastic_ips)} unused Elastic IP(s) - potential savings: ${eip_cost:.2f}/month")
        if old_snapshots:
            recommendations.append(f"💰 {len(old_snapshots)} snapshot(s) older than 90 days - potential savings: ${snapshot_cost:.2f}/month")

        if not recommendations:
            recommendations.append("✅ No obvious unused resources found - good housekeeping!")

        return {
            "stopped_instances": stopped_instances,
            "stopped_instances_count": len(stopped_instances),
            "unattached_volumes": unattached_volumes,
            "unattached_volumes_count": len(unattached_volumes),
            "unused_elastic_ips": unused_elastic_ips,
            "unused_elastic_ips_count": len(unused_elastic_ips),
            "old_snapshots": old_snapshots[:20],  # Limit to 20 oldest
            "old_snapshots_count": len(old_snapshots),
            "total_potential_savings": total_savings,
            "breakdown": {
                "volumes": volume_cost,
                "elastic_ips": eip_cost,
                "snapshots": snapshot_cost
            },
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "stopped_instances": [],
            "unattached_volumes": [],
            "unused_elastic_ips": [],
            "old_snapshots": []
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "stopped_instances": [],
            "unattached_volumes": [],
            "unused_elastic_ips": [],
            "old_snapshots": []
        }


@tool
def analyze_security_group(
    group_id: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze security group rules and assess security risks.

    Provides detailed analysis of ingress/egress rules with risk assessment
    for overly permissive configurations.

    Args:
        group_id: Security group ID (e.g., "sg-1234567890abcdef0")
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - group_details: Basic SG information
        - ingress_rules: All inbound rules with risk assessment
        - egress_rules: All outbound rules
        - risk_assessment: Overall security risk level
        - attached_resources: Count of instances using this SG
        - recommendations: Security improvements

    Example:
        >>> sg = analyze_security_group("sg-1234567890abcdef0")
        >>> print(f"Risk level: {sg['risk_assessment']['risk_level']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2_client = aws_client.get_client("ec2")

        # Get security group details
        response = ec2_client.describe_security_groups(GroupIds=[group_id])

        if not response['SecurityGroups']:
            return {
                "error": f"Security group {group_id} not found",
                "group_id": group_id
            }

        sg = response['SecurityGroups'][0]

        # Basic details
        group_details = {
            "group_id": group_id,
            "group_name": sg.get('GroupName'),
            "description": sg.get('Description'),
            "vpc_id": sg.get('VpcId')
        }

        # Analyze ingress rules
        ingress_rules = []
        risk_factors = []

        for rule in sg.get('IpPermissions', []):
            rule_analysis = _analyze_sg_rule(rule, 'ingress')
            ingress_rules.append(rule_analysis)

            if rule_analysis['risk_level'] in ['critical', 'high']:
                risk_factors.append(rule_analysis['risk_reason'])

        # Analyze egress rules
        egress_rules = []
        for rule in sg.get('IpPermissionsEgress', []):
            rule_analysis = _analyze_sg_rule(rule, 'egress')
            egress_rules.append(rule_analysis)

        # Find attached resources
        instances_response = ec2_client.describe_instances(
            Filters=[{"Name": "instance.group-id", "Values": [group_id]}]
        )

        attached_instance_count = sum(
            len(res['Instances']) for res in instances_response['Reservations']
        )

        # Risk assessment
        risk_level = 'low'
        if any('0.0.0.0/0' in str(r) for r in ingress_rules):
            # Check for critical public access
            critical_ports = [22, 3389, 1433, 3306, 5432, 27017]  # SSH, RDP, databases
            for rule in ingress_rules:
                if rule.get('from_port') in critical_ports and '0.0.0.0/0' in str(rule):
                    risk_level = 'critical'
                    break
            if risk_level != 'critical':
                risk_level = 'high'
        elif len(risk_factors) > 2:
            risk_level = 'medium'

        # Recommendations
        recommendations = _generate_sg_recommendations(ingress_rules, egress_rules, risk_factors)

        return {
            "group_id": group_id,
            "group_details": group_details,
            "ingress_rules": ingress_rules,
            "ingress_rules_count": len(ingress_rules),
            "egress_rules": egress_rules,
            "egress_rules_count": len(egress_rules),
            "risk_assessment": {
                "risk_level": risk_level,
                "risk_factors": risk_factors
            },
            "attached_resources": {
                "instances": attached_instance_count
            },
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "group_id": group_id
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "group_id": group_id
        }


@tool
def find_overpermissive_security_groups(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Scan all security groups for overly permissive rules.

    Identifies security groups with public access (0.0.0.0/0) to sensitive ports,
    unused security groups, and other security risks.

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - security_groups: List of all SGs with risk assessment
        - risky_groups: SGs with high or critical risk
        - unused_groups: SGs not attached to any resources
        - summary: Statistics by risk level
        - recommendations: Action items

    Example:
        >>> scan = find_overpermissive_security_groups()
        >>> print(f"Found {len(scan['risky_groups'])} risky security groups")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2_client = aws_client.get_client("ec2")

        # Get all security groups
        response = ec2_client.describe_security_groups()

        security_groups = []
        risky_groups = []
        unused_groups = []

        # Get all instances to check SG usage
        instances_response = ec2_client.describe_instances()
        used_sg_ids = set()
        for reservation in instances_response['Reservations']:
            for instance in reservation['Instances']:
                for sg in instance.get('SecurityGroups', []):
                    used_sg_ids.add(sg['GroupId'])

        for sg in response['SecurityGroups']:
            group_id = sg['GroupId']
            group_name = sg.get('GroupName')

            # Skip default SGs
            if group_name == 'default':
                continue

            # Analyze rules for risks
            risk_factors = []
            risk_level = 'low'
            critical_ports = [22, 3389, 1433, 3306, 5432, 27017, 6379, 9200, 5601]

            for rule in sg.get('IpPermissions', []):
                # Check for 0.0.0.0/0
                has_public_access = False
                for ip_range in rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == '0.0.0.0/0':
                        has_public_access = True
                        break

                if has_public_access:
                    from_port = rule.get('FromPort', 0)
                    to_port = rule.get('ToPort', 65535)

                    # Check if allows all ports
                    if rule.get('IpProtocol') == '-1':
                        risk_level = 'critical'
                        risk_factors.append("Allows ALL traffic from 0.0.0.0/0")
                    # Check for critical ports
                    elif from_port in critical_ports or to_port in critical_ports:
                        risk_level = 'critical'
                        port_name = _get_port_name(from_port)
                        risk_factors.append(f"Allows {port_name} ({from_port}) from 0.0.0.0/0")
                    # Check for port ranges
                    elif to_port - from_port > 100:
                        if risk_level not in ['critical', 'high']:
                            risk_level = 'high'
                        risk_factors.append(f"Allows large port range ({from_port}-{to_port}) from 0.0.0.0/0")
                    else:
                        if risk_level == 'low':
                            risk_level = 'medium'
                        risk_factors.append(f"Allows port {from_port} from 0.0.0.0/0")

            # Check if unused
            is_unused = group_id not in used_sg_ids

            sg_summary = {
                "group_id": group_id,
                "group_name": group_name,
                "description": sg.get('Description'),
                "vpc_id": sg.get('VpcId'),
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "ingress_rules_count": len(sg.get('IpPermissions', [])),
                "is_unused": is_unused
            }

            security_groups.append(sg_summary)

            if risk_level in ['critical', 'high']:
                risky_groups.append(sg_summary)

            if is_unused:
                unused_groups.append(sg_summary)

        # Summary statistics
        summary = {
            "total_groups": len(security_groups),
            "critical": len([sg for sg in security_groups if sg['risk_level'] == 'critical']),
            "high": len([sg for sg in security_groups if sg['risk_level'] == 'high']),
            "medium": len([sg for sg in security_groups if sg['risk_level'] == 'medium']),
            "low": len([sg for sg in security_groups if sg['risk_level'] == 'low']),
            "unused": len(unused_groups)
        }

        # Recommendations
        recommendations = []
        if summary['critical'] > 0:
            recommendations.append(f"🔴 URGENT: {summary['critical']} security group(s) with CRITICAL risk - immediate action required")
        if summary['high'] > 0:
            recommendations.append(f"⚠️ {summary['high']} security group(s) with HIGH risk - review and restrict access")
        if summary['medium'] > 0:
            recommendations.append(f"⚠️ {summary['medium']} security group(s) with MEDIUM risk - consider tightening rules")
        if summary['unused'] > 0:
            recommendations.append(f"💡 {summary['unused']} unused security group(s) - consider deleting to reduce clutter")

        if not recommendations:
            recommendations.append("✅ No critical security issues found in security groups")

        return {
            "security_groups": security_groups,
            "risky_groups": risky_groups,
            "unused_groups": unused_groups,
            "summary": summary,
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "security_groups": []
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "security_groups": []
        }


# Helper functions

@tool
def _get_instance_metrics(instance_id: str, aws_client: AWSClient) -> Dict[str, Any]:
    """Fetch CloudWatch metrics for an instance."""
    try:
        cloudwatch = aws_client.get_client('cloudwatch')

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        # CPU Utilization
        cpu_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Average', 'Maximum']
        )

        cpu_datapoints = sorted(cpu_response['Datapoints'], key=lambda x: x['Timestamp'])

        return {
            "cpu_utilization": {
                "average": round(sum(p['Average'] for p in cpu_datapoints) / len(cpu_datapoints), 2) if cpu_datapoints else 0,
                "maximum": round(max((p['Maximum'] for p in cpu_datapoints), default=0), 2),
                "datapoints": len(cpu_datapoints)
            },
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    except Exception:
        return None


@tool
def _estimate_instance_cost(instance_details: Dict, volumes: List[Dict]) -> Dict[str, Any]:
    """Estimate monthly cost for an instance (rough estimates)."""
    # Very rough cost estimates - actual prices vary by region
    instance_type = instance_details.get('instance_type', '')
    state = instance_details.get('state', '')

    # Instance costs (simplified, US East pricing)
    hourly_cost = 0.0

    if instance_type.startswith('t2.'):
        cost_map = {'t2.nano': 0.0058, 't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464, 't2.large': 0.0928}
        hourly_cost = cost_map.get(instance_type, 0.05)
    elif instance_type.startswith('t3.'):
        cost_map = {'t3.nano': 0.0052, 't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416, 't3.large': 0.0832}
        hourly_cost = cost_map.get(instance_type, 0.05)
    elif instance_type.startswith('m5.'):
        cost_map = {'m5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384}
        hourly_cost = cost_map.get(instance_type, 0.10)
    else:
        hourly_cost = 0.10  # Default estimate

    monthly_instance_cost = hourly_cost * 730  # 730 hours/month average

    # Only charge for running instances
    if state != 'running':
        monthly_instance_cost = 0.0

    # Volume costs
    volume_cost = 0.0
    for vol in volumes:
        size = vol.get('size_gb', 0)
        volume_cost += size * 0.10  # $0.10/GB for gp2

    return {
        "monthly_cost": round(monthly_instance_cost + volume_cost, 2),
        "instance_cost": round(monthly_instance_cost, 2),
        "storage_cost": round(volume_cost, 2),
        "hourly_rate": hourly_cost,
        "note": "Estimates based on US East pricing, actual costs may vary"
    }


@tool
def _assess_instance_health(
    instance_details: Dict,
    volumes: List[Dict],
    security_groups: List[Dict],
    tags: Dict
) -> Dict[str, Any]:
    """Assess overall instance health."""
    issues = []
    warnings = []

    # Check if instance is stopped
    if instance_details.get('state') == 'stopped':
        warnings.append("Instance is in stopped state")

    # Check monitoring
    if instance_details.get('monitoring_state') == 'disabled':
        warnings.append("Detailed monitoring is disabled")

    # Check encryption
    unencrypted_volumes = [v for v in volumes if not v.get('encrypted')]
    if unencrypted_volumes:
        issues.append(f"{len(unencrypted_volumes)} unencrypted volume(s) found")

    # Check for Name tag
    if 'Name' not in tags:
        warnings.append("Instance has no Name tag")

    # Health status
    if issues:
        health_status = 'unhealthy'
    elif warnings:
        health_status = 'warning'
    else:
        health_status = 'healthy'

    return {
        "health_status": health_status,
        "issues": issues,
        "warnings": warnings
    }


@tool
def _generate_instance_recommendations(
    instance_details: Dict,
    volumes: List[Dict],
    security_groups: List[Dict],
    tags: Dict,
    metrics: Optional[Dict]
) -> List[str]:
    """Generate recommendations for instance optimization."""
    recommendations = []

    # Stopped instance
    if instance_details.get('state') == 'stopped':
        recommendations.append("⚠️ Instance is stopped - consider terminating if no longer needed")

    # Monitoring
    if instance_details.get('monitoring_state') == 'disabled':
        recommendations.append("💡 Enable detailed monitoring for better visibility")

    # Encryption
    unencrypted = [v for v in volumes if not v.get('encrypted')]
    if unencrypted:
        recommendations.append(f"🔒 Enable encryption on {len(unencrypted)} volume(s) for security")

    # Tagging
    if 'Name' not in tags:
        recommendations.append("🏷️ Add a Name tag for better resource management")

    # CPU utilization
    if metrics and metrics.get('cpu_utilization'):
        cpu_avg = metrics['cpu_utilization'].get('average', 0)
        if cpu_avg < 5:
            recommendations.append("💰 CPU utilization very low (<5%) - consider downsizing instance type")
        elif cpu_avg > 80:
            recommendations.append("⚡ CPU utilization high (>80%) - consider upsizing instance type")

    if not recommendations:
        recommendations.append("✅ Instance configuration looks good")

    return recommendations


@tool
def _analyze_sg_rule(rule: Dict, direction: str) -> Dict[str, Any]:
    """Analyze a single security group rule."""
    from_port = rule.get('FromPort', 0)
    to_port = rule.get('ToPort', 65535)
    protocol = rule.get('IpProtocol', 'all')

    # Get source/destination
    sources = []
    for ip_range in rule.get('IpRanges', []):
        cidr = ip_range.get('CidrIp')
        description = ip_range.get('Description', '')
        sources.append({"type": "cidr", "value": cidr, "description": description})

    for sg_ref in rule.get('UserIdGroupPairs', []):
        sg_id = sg_ref.get('GroupId')
        sources.append({"type": "security_group", "value": sg_id})

    # Risk assessment
    risk_level = 'low'
    risk_reason = None

    if any(s['value'] == '0.0.0.0/0' for s in sources if s['type'] == 'cidr'):
        critical_ports = [22, 3389, 1433, 3306, 5432, 27017]
        if from_port in critical_ports:
            risk_level = 'critical'
            risk_reason = f"Public access to {_get_port_name(from_port)} (port {from_port})"
        elif protocol == '-1':
            risk_level = 'critical'
            risk_reason = "Public access to all ports"
        else:
            risk_level = 'high'
            risk_reason = f"Public access to port {from_port}"

    return {
        "direction": direction,
        "protocol": protocol,
        "from_port": from_port,
        "to_port": to_port,
        "sources": sources,
        "risk_level": risk_level,
        "risk_reason": risk_reason
    }


@tool
def _generate_sg_recommendations(
    ingress_rules: List[Dict],
    egress_rules: List[Dict],
    risk_factors: List[str]
) -> List[str]:
    """Generate security group recommendations."""
    recommendations = []

    # Check for public access
    public_rules = [r for r in ingress_rules if any(
        s.get('value') == '0.0.0.0/0' for s in r.get('sources', [])
    )]

    if public_rules:
        recommendations.append("🔒 Restrict public access (0.0.0.0/0) to specific IP ranges where possible")

    # Check for critical risks
    critical_rules = [r for r in ingress_rules if r.get('risk_level') == 'critical']
    if critical_rules:
        recommendations.append(f"🔴 {len(critical_rules)} CRITICAL risk rule(s) found - immediate action required")

    if not recommendations:
        recommendations.append("✅ Security group configuration looks reasonable")

    return recommendations


@tool
def _get_port_name(port: int) -> str:
    """Get common name for port number."""
    port_names = {
        22: 'SSH',
        80: 'HTTP',
        443: 'HTTPS',
        3306: 'MySQL',
        5432: 'PostgreSQL',
        1433: 'MSSQL',
        3389: 'RDP',
        27017: 'MongoDB',
        6379: 'Redis',
        9200: 'Elasticsearch',
        5601: 'Kibana'
    }
    return port_names.get(port, str(port))
