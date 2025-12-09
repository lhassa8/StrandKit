"""
EC2 and Compute Visibility Tools

This module provides tools for analyzing EC2 instances, security groups,
and compute resources for health, security, and cost optimization.

PRICING NOTES:
- EC2 pricing varies significantly by instance family, size, and platform (Linux/Windows)
- Windows instances typically cost 1.5-2x more than Linux due to licensing
- Graviton (arm64) instances are typically 20% cheaper than x86 equivalents
- Spot instances can be 60-90% cheaper but may be interrupted
- Reserved Instances and Savings Plans can reduce costs by 30-72%
- All estimates are for us-east-1 on-demand pricing; other regions may vary 10-30%
- Use AWS Pricing Calculator for accurate quotes
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


# =============================================================================
# EC2 PRICING DATA (us-east-1, on-demand, as of 2024)
# =============================================================================
# Source: https://instances.vantage.sh/ and AWS pricing pages
# Format: {instance_type: {'linux': hourly_cost, 'windows': hourly_cost}}

EC2_INSTANCE_PRICING = {
    # T2 Burstable (Previous Gen)
    't2.nano': {'linux': 0.0058, 'windows': 0.0082},
    't2.micro': {'linux': 0.0116, 'windows': 0.0162},
    't2.small': {'linux': 0.023, 'windows': 0.032},
    't2.medium': {'linux': 0.0464, 'windows': 0.064},
    't2.large': {'linux': 0.0928, 'windows': 0.128},
    't2.xlarge': {'linux': 0.1856, 'windows': 0.256},
    't2.2xlarge': {'linux': 0.3712, 'windows': 0.512},

    # T3 Burstable (Current Gen)
    't3.nano': {'linux': 0.0052, 'windows': 0.0076},
    't3.micro': {'linux': 0.0104, 'windows': 0.0152},
    't3.small': {'linux': 0.0208, 'windows': 0.0304},
    't3.medium': {'linux': 0.0416, 'windows': 0.0608},
    't3.large': {'linux': 0.0832, 'windows': 0.1216},
    't3.xlarge': {'linux': 0.1664, 'windows': 0.2432},
    't3.2xlarge': {'linux': 0.3328, 'windows': 0.4864},

    # T3a AMD Burstable
    't3a.nano': {'linux': 0.0047, 'windows': 0.0071},
    't3a.micro': {'linux': 0.0094, 'windows': 0.0142},
    't3a.small': {'linux': 0.0188, 'windows': 0.0284},
    't3a.medium': {'linux': 0.0376, 'windows': 0.0568},
    't3a.large': {'linux': 0.0752, 'windows': 0.1136},
    't3a.xlarge': {'linux': 0.1504, 'windows': 0.2272},
    't3a.2xlarge': {'linux': 0.3008, 'windows': 0.4544},

    # T4g Graviton Burstable (20% cheaper than T3)
    't4g.nano': {'linux': 0.0042, 'windows': None},  # No Windows on Graviton
    't4g.micro': {'linux': 0.0084, 'windows': None},
    't4g.small': {'linux': 0.0168, 'windows': None},
    't4g.medium': {'linux': 0.0336, 'windows': None},
    't4g.large': {'linux': 0.0672, 'windows': None},
    't4g.xlarge': {'linux': 0.1344, 'windows': None},
    't4g.2xlarge': {'linux': 0.2688, 'windows': None},

    # M5 General Purpose
    'm5.large': {'linux': 0.096, 'windows': 0.188},
    'm5.xlarge': {'linux': 0.192, 'windows': 0.376},
    'm5.2xlarge': {'linux': 0.384, 'windows': 0.752},
    'm5.4xlarge': {'linux': 0.768, 'windows': 1.504},
    'm5.8xlarge': {'linux': 1.536, 'windows': 3.008},
    'm5.12xlarge': {'linux': 2.304, 'windows': 4.512},
    'm5.16xlarge': {'linux': 3.072, 'windows': 6.016},
    'm5.24xlarge': {'linux': 4.608, 'windows': 9.024},

    # M5a AMD General Purpose
    'm5a.large': {'linux': 0.086, 'windows': 0.178},
    'm5a.xlarge': {'linux': 0.172, 'windows': 0.356},
    'm5a.2xlarge': {'linux': 0.344, 'windows': 0.712},
    'm5a.4xlarge': {'linux': 0.688, 'windows': 1.424},
    'm5a.8xlarge': {'linux': 1.376, 'windows': 2.848},
    'm5a.12xlarge': {'linux': 2.064, 'windows': 4.272},

    # M6i General Purpose (Current Gen Intel)
    'm6i.large': {'linux': 0.096, 'windows': 0.188},
    'm6i.xlarge': {'linux': 0.192, 'windows': 0.376},
    'm6i.2xlarge': {'linux': 0.384, 'windows': 0.752},
    'm6i.4xlarge': {'linux': 0.768, 'windows': 1.504},
    'm6i.8xlarge': {'linux': 1.536, 'windows': 3.008},
    'm6i.12xlarge': {'linux': 2.304, 'windows': 4.512},
    'm6i.16xlarge': {'linux': 3.072, 'windows': 6.016},
    'm6i.24xlarge': {'linux': 4.608, 'windows': 9.024},

    # M6g Graviton General Purpose
    'm6g.medium': {'linux': 0.0385, 'windows': None},
    'm6g.large': {'linux': 0.077, 'windows': None},
    'm6g.xlarge': {'linux': 0.154, 'windows': None},
    'm6g.2xlarge': {'linux': 0.308, 'windows': None},
    'm6g.4xlarge': {'linux': 0.616, 'windows': None},
    'm6g.8xlarge': {'linux': 1.232, 'windows': None},
    'm6g.12xlarge': {'linux': 1.848, 'windows': None},
    'm6g.16xlarge': {'linux': 2.464, 'windows': None},

    # M7g Graviton3 General Purpose (Latest)
    'm7g.medium': {'linux': 0.0408, 'windows': None},
    'm7g.large': {'linux': 0.0816, 'windows': None},
    'm7g.xlarge': {'linux': 0.1632, 'windows': None},
    'm7g.2xlarge': {'linux': 0.3264, 'windows': None},
    'm7g.4xlarge': {'linux': 0.6528, 'windows': None},
    'm7g.8xlarge': {'linux': 1.3056, 'windows': None},
    'm7g.12xlarge': {'linux': 1.9584, 'windows': None},
    'm7g.16xlarge': {'linux': 2.6112, 'windows': None},

    # C5 Compute Optimized
    'c5.large': {'linux': 0.085, 'windows': 0.177},
    'c5.xlarge': {'linux': 0.17, 'windows': 0.354},
    'c5.2xlarge': {'linux': 0.34, 'windows': 0.708},
    'c5.4xlarge': {'linux': 0.68, 'windows': 1.416},
    'c5.9xlarge': {'linux': 1.53, 'windows': 3.186},
    'c5.12xlarge': {'linux': 2.04, 'windows': 4.248},
    'c5.18xlarge': {'linux': 3.06, 'windows': 6.372},
    'c5.24xlarge': {'linux': 4.08, 'windows': 8.496},

    # C6i Compute Optimized (Current Gen Intel)
    'c6i.large': {'linux': 0.085, 'windows': 0.177},
    'c6i.xlarge': {'linux': 0.17, 'windows': 0.354},
    'c6i.2xlarge': {'linux': 0.34, 'windows': 0.708},
    'c6i.4xlarge': {'linux': 0.68, 'windows': 1.416},
    'c6i.8xlarge': {'linux': 1.36, 'windows': 2.832},
    'c6i.12xlarge': {'linux': 2.04, 'windows': 4.248},
    'c6i.16xlarge': {'linux': 2.72, 'windows': 5.664},
    'c6i.24xlarge': {'linux': 4.08, 'windows': 8.496},

    # C6g Graviton Compute Optimized
    'c6g.medium': {'linux': 0.034, 'windows': None},
    'c6g.large': {'linux': 0.068, 'windows': None},
    'c6g.xlarge': {'linux': 0.136, 'windows': None},
    'c6g.2xlarge': {'linux': 0.272, 'windows': None},
    'c6g.4xlarge': {'linux': 0.544, 'windows': None},
    'c6g.8xlarge': {'linux': 1.088, 'windows': None},
    'c6g.12xlarge': {'linux': 1.632, 'windows': None},
    'c6g.16xlarge': {'linux': 2.176, 'windows': None},

    # C7g Graviton3 Compute Optimized (Latest)
    'c7g.medium': {'linux': 0.0361, 'windows': None},
    'c7g.large': {'linux': 0.0723, 'windows': None},
    'c7g.xlarge': {'linux': 0.1445, 'windows': None},
    'c7g.2xlarge': {'linux': 0.289, 'windows': None},
    'c7g.4xlarge': {'linux': 0.578, 'windows': None},
    'c7g.8xlarge': {'linux': 1.156, 'windows': None},
    'c7g.12xlarge': {'linux': 1.734, 'windows': None},
    'c7g.16xlarge': {'linux': 2.312, 'windows': None},

    # R5 Memory Optimized
    'r5.large': {'linux': 0.126, 'windows': 0.218},
    'r5.xlarge': {'linux': 0.252, 'windows': 0.436},
    'r5.2xlarge': {'linux': 0.504, 'windows': 0.872},
    'r5.4xlarge': {'linux': 1.008, 'windows': 1.744},
    'r5.8xlarge': {'linux': 2.016, 'windows': 3.488},
    'r5.12xlarge': {'linux': 3.024, 'windows': 5.232},
    'r5.16xlarge': {'linux': 4.032, 'windows': 6.976},
    'r5.24xlarge': {'linux': 6.048, 'windows': 10.464},

    # R6i Memory Optimized (Current Gen Intel)
    'r6i.large': {'linux': 0.126, 'windows': 0.218},
    'r6i.xlarge': {'linux': 0.252, 'windows': 0.436},
    'r6i.2xlarge': {'linux': 0.504, 'windows': 0.872},
    'r6i.4xlarge': {'linux': 1.008, 'windows': 1.744},
    'r6i.8xlarge': {'linux': 2.016, 'windows': 3.488},
    'r6i.12xlarge': {'linux': 3.024, 'windows': 5.232},
    'r6i.16xlarge': {'linux': 4.032, 'windows': 6.976},
    'r6i.24xlarge': {'linux': 6.048, 'windows': 10.464},

    # R6g Graviton Memory Optimized
    'r6g.medium': {'linux': 0.0504, 'windows': None},
    'r6g.large': {'linux': 0.1008, 'windows': None},
    'r6g.xlarge': {'linux': 0.2016, 'windows': None},
    'r6g.2xlarge': {'linux': 0.4032, 'windows': None},
    'r6g.4xlarge': {'linux': 0.8064, 'windows': None},
    'r6g.8xlarge': {'linux': 1.6128, 'windows': None},
    'r6g.12xlarge': {'linux': 2.4192, 'windows': None},
    'r6g.16xlarge': {'linux': 3.2256, 'windows': None},

    # I3 Storage Optimized
    'i3.large': {'linux': 0.156, 'windows': 0.248},
    'i3.xlarge': {'linux': 0.312, 'windows': 0.496},
    'i3.2xlarge': {'linux': 0.624, 'windows': 0.992},
    'i3.4xlarge': {'linux': 1.248, 'windows': 1.984},
    'i3.8xlarge': {'linux': 2.496, 'windows': 3.968},
    'i3.16xlarge': {'linux': 4.992, 'windows': 7.936},

    # D2 Dense Storage
    'd2.xlarge': {'linux': 0.69, 'windows': 0.828},
    'd2.2xlarge': {'linux': 1.38, 'windows': 1.656},
    'd2.4xlarge': {'linux': 2.76, 'windows': 3.312},
    'd2.8xlarge': {'linux': 5.52, 'windows': 6.624},

    # X1 Memory Optimized (Very Large)
    'x1.16xlarge': {'linux': 6.669, 'windows': 9.341},
    'x1.32xlarge': {'linux': 13.338, 'windows': 18.682},

    # X2idn Memory Optimized (Current Gen)
    'x2idn.16xlarge': {'linux': 6.669, 'windows': 9.341},
    'x2idn.24xlarge': {'linux': 10.008, 'windows': 14.016},
    'x2idn.32xlarge': {'linux': 13.338, 'windows': 18.682},

    # P3 GPU Instances
    'p3.2xlarge': {'linux': 3.06, 'windows': 3.06},  # Windows same price
    'p3.8xlarge': {'linux': 12.24, 'windows': 12.24},
    'p3.16xlarge': {'linux': 24.48, 'windows': 24.48},

    # P4d GPU Instances (Latest)
    'p4d.24xlarge': {'linux': 32.77, 'windows': 32.77},

    # G4dn GPU Instances (Inference)
    'g4dn.xlarge': {'linux': 0.526, 'windows': 0.71},
    'g4dn.2xlarge': {'linux': 0.752, 'windows': 1.028},
    'g4dn.4xlarge': {'linux': 1.204, 'windows': 1.664},
    'g4dn.8xlarge': {'linux': 2.176, 'windows': 3.096},
    'g4dn.12xlarge': {'linux': 3.912, 'windows': 5.292},
    'g4dn.16xlarge': {'linux': 4.352, 'windows': 6.192},

    # G5 GPU Instances (Latest Inference)
    'g5.xlarge': {'linux': 1.006, 'windows': 1.282},
    'g5.2xlarge': {'linux': 1.212, 'windows': 1.58},
    'g5.4xlarge': {'linux': 1.624, 'windows': 2.176},
    'g5.8xlarge': {'linux': 2.448, 'windows': 3.368},
    'g5.12xlarge': {'linux': 5.672, 'windows': 6.96},
    'g5.16xlarge': {'linux': 4.096, 'windows': 5.936},
    'g5.24xlarge': {'linux': 8.144, 'windows': 10.704},
    'g5.48xlarge': {'linux': 16.288, 'windows': 21.408},

    # Inf1 Inference Instances
    'inf1.xlarge': {'linux': 0.228, 'windows': None},
    'inf1.2xlarge': {'linux': 0.362, 'windows': None},
    'inf1.6xlarge': {'linux': 1.18, 'windows': None},
    'inf1.24xlarge': {'linux': 4.721, 'windows': None},
}

# EBS Volume Pricing (per GB-month, us-east-1)
EBS_VOLUME_PRICING = {
    'gp3': 0.08,
    'gp2': 0.10,
    'io1': 0.125,  # Plus IOPS cost
    'io2': 0.125,  # Plus IOPS cost
    'st1': 0.045,
    'sc1': 0.015,
    'standard': 0.05,
}

# EBS IOPS Pricing (per IOPS-month)
EBS_IOPS_PRICING = {
    'io1': 0.10,
    'io2': 0.10,
    'gp3': 0.005,  # Only above 3000 IOPS baseline
}


def _get_ec2_hourly_cost(instance_type: str, platform: str = 'linux') -> float:
    """
    Get hourly cost for an EC2 instance type.

    Args:
        instance_type: EC2 instance type (e.g., 'm5.large')
        platform: 'linux' or 'windows'

    Returns:
        Hourly cost in USD, or estimate if type not found
    """
    platform_key = 'windows' if platform and 'windows' in platform.lower() else 'linux'

    if instance_type in EC2_INSTANCE_PRICING:
        pricing = EC2_INSTANCE_PRICING[instance_type]
        cost = pricing.get(platform_key)
        if cost is not None:
            return cost
        # Graviton instances don't support Windows, fall back to Linux
        return pricing.get('linux', 0.10)

    # Estimate for unknown instance types based on family and size
    # Parse instance type (e.g., 'm5.large' -> family='m5', size='large')
    parts = instance_type.split('.')
    if len(parts) == 2:
        family, size = parts

        # Size multipliers (approximate)
        size_multipliers = {
            'nano': 0.25, 'micro': 0.5, 'small': 1, 'medium': 2,
            'large': 4, 'xlarge': 8, '2xlarge': 16, '4xlarge': 32,
            '8xlarge': 64, '9xlarge': 72, '12xlarge': 96, '16xlarge': 128,
            '18xlarge': 144, '24xlarge': 192, '32xlarge': 256, '48xlarge': 384,
        }

        # Base costs per family (for 'large' equivalent)
        family_base_costs = {
            't': 0.02, 'm': 0.024, 'c': 0.021, 'r': 0.032,
            'i': 0.039, 'd': 0.17, 'x': 0.42, 'p': 0.77, 'g': 0.13,
        }

        family_prefix = family[0] if family else 'm'
        base_cost = family_base_costs.get(family_prefix, 0.024)
        multiplier = size_multipliers.get(size, 4) / 4  # Normalize to 'large'

        hourly = base_cost * multiplier
        if platform_key == 'windows':
            hourly *= 1.8  # Windows typically ~80% more

        return hourly

    # Default fallback
    return 0.10 if platform_key == 'linux' else 0.18


def _estimate_ebs_cost(volumes: list) -> dict:
    """
    Estimate monthly EBS cost for a list of volumes.

    Args:
        volumes: List of volume dicts with 'size_gb', 'volume_type', 'iops'

    Returns:
        Dict with storage_cost, iops_cost, total_cost
    """
    storage_cost = 0.0
    iops_cost = 0.0

    for vol in volumes:
        size = vol.get('size_gb', 0)
        vol_type = vol.get('volume_type', 'gp2')
        iops = vol.get('iops', 0)

        # Storage cost
        rate = EBS_VOLUME_PRICING.get(vol_type, 0.10)
        storage_cost += size * rate

        # IOPS cost (io1, io2, and gp3 above baseline)
        if vol_type in ('io1', 'io2') and iops > 0:
            iops_cost += iops * EBS_IOPS_PRICING.get(vol_type, 0.10)
        elif vol_type == 'gp3' and iops > 3000:
            iops_cost += (iops - 3000) * EBS_IOPS_PRICING['gp3']

    return {
        'storage_cost': round(storage_cost, 2),
        'iops_cost': round(iops_cost, 2),
        'total_cost': round(storage_cost + iops_cost, 2),
    }


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
    """
    Estimate monthly cost for an instance using comprehensive pricing data.

    Args:
        instance_details: Dict with instance_type, state, platform keys
        volumes: List of volume dicts with size_gb, volume_type, iops keys

    Returns:
        Dict with monthly_cost, instance_cost, storage_cost, hourly_rate, and notes
    """
    instance_type = instance_details.get('instance_type', '')
    state = instance_details.get('state', '')
    platform = instance_details.get('platform', 'linux')

    # Get hourly cost using comprehensive pricing table
    hourly_cost = _get_ec2_hourly_cost(instance_type, platform)

    monthly_instance_cost = hourly_cost * 730  # 730 hours/month average

    # Only charge for running instances
    if state != 'running':
        monthly_instance_cost = 0.0

    # Volume costs using actual volume types and IOPS
    ebs_costs = _estimate_ebs_cost(volumes)

    platform_note = 'Windows' if platform and 'windows' in platform.lower() else 'Linux'
    is_known_type = instance_type in EC2_INSTANCE_PRICING

    return {
        "monthly_cost": round(monthly_instance_cost + ebs_costs['total_cost'], 2),
        "instance_cost": round(monthly_instance_cost, 2),
        "storage_cost": ebs_costs['storage_cost'],
        "iops_cost": ebs_costs['iops_cost'],
        "hourly_rate": round(hourly_cost, 4),
        "platform": platform_note,
        "pricing_accuracy": "known" if is_known_type else "estimated",
        "note": f"On-demand {platform_note} pricing (us-east-1). "
                f"{'Exact pricing from database.' if is_known_type else 'Estimated from similar types.'} "
                "Reserved/Savings Plans can reduce costs 30-72%."
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
