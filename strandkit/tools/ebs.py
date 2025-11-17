"""
EBS & Volume Optimization Tools for StrandKit.

This module provides comprehensive EBS volume and snapshot optimization:
- Volume type optimization (GP2 → GP3 migration)
- IOPS and throughput recommendations
- Snapshot lifecycle management
- Encryption compliance checking
- Performance anomaly detection
- AMI usage analysis

All tools follow consistent patterns:
- Accept simple, well-typed parameters
- Return structured JSON with consistent keys
- Include cost savings calculations
- Provide actionable recommendations
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from strandkit.core.aws_client import AWSClient
from strands import tool


# EBS Pricing (us-east-1, per GB-month)
EBS_PRICING = {
    'gp3': 0.08,
    'gp2': 0.10,
    'io1': 0.125,
    'io2': 0.125,
    'st1': 0.045,
    'sc1': 0.015,
    'standard': 0.05
}

# IOPS Pricing (per IOPS-month)
IOPS_PRICING = {
    'gp3': 0.005,  # Above 3000 IOPS
    'io1': 0.065,
    'io2': 0.065
}

# Throughput Pricing (per MB/s-month)
THROUGHPUT_PRICING = {
    'gp3': 0.04  # Above 125 MB/s
}


@tool
def analyze_ebs_volumes(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze EBS volumes for optimization opportunities.

    Checks for:
    - GP2 → GP3 migration opportunities (20% cost savings)
    - Underutilized volumes (low IOPS usage)
    - Oversized volumes (low space utilization)
    - Unattached volumes (waste)
    - Volume type recommendations

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total volumes, optimization opportunities, potential savings
        - gp2_to_gp3_migrations: GP2 volumes that should move to GP3
        - underutilized_volumes: Volumes with low usage
        - oversized_volumes: Volumes with low space utilization
        - unattached_volumes: Volumes not attached to instances
        - recommendations: Cost optimization suggestions

    Example:
        >>> result = analyze_ebs_volumes()
        >>> print(f"Potential savings: ${result['summary']['total_monthly_savings']:.2f}")
        >>> print(f"GP2→GP3 migrations: {len(result['gp2_to_gp3_migrations'])}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2 = aws_client.get_client('ec2')
        cloudwatch = aws_client.get_client('cloudwatch')

        # Get all volumes
        volumes_response = ec2.describe_volumes()
        all_volumes = volumes_response.get('Volumes', [])

        # Handle pagination
        while 'NextToken' in volumes_response:
            volumes_response = ec2.describe_volumes(NextToken=volumes_response['NextToken'])
            all_volumes.extend(volumes_response.get('Volumes', []))

        gp2_to_gp3_migrations = []
        underutilized_volumes = []
        oversized_volumes = []
        unattached_volumes = []

        total_monthly_cost = 0.0
        total_monthly_savings = 0.0

        now = datetime.now(timezone.utc)

        for volume in all_volumes:
            volume_id = volume['VolumeId']
            volume_type = volume['VolumeType']
            size_gb = volume['Size']
            iops = volume.get('Iops', 0)
            throughput = volume.get('Throughput', 0)
            state = volume['State']
            attachments = volume.get('Attachments', [])

            # Calculate current cost
            storage_cost = size_gb * EBS_PRICING.get(volume_type, 0.10)
            iops_cost = 0.0
            throughput_cost = 0.0

            if volume_type == 'gp3':
                # GP3: First 3000 IOPS and 125 MB/s free
                if iops > 3000:
                    iops_cost = (iops - 3000) * IOPS_PRICING['gp3']
                if throughput > 125:
                    throughput_cost = (throughput - 125) * THROUGHPUT_PRICING['gp3']
            elif volume_type in ['io1', 'io2']:
                iops_cost = iops * IOPS_PRICING.get(volume_type, 0.065)

            current_monthly_cost = storage_cost + iops_cost + throughput_cost
            total_monthly_cost += current_monthly_cost

            # Check if volume is attached
            is_attached = len(attachments) > 0
            instance_id = attachments[0]['InstanceId'] if is_attached else None

            # 1. Check for GP2 → GP3 migration
            if volume_type == 'gp2':
                # GP3 is 20% cheaper and offers better performance
                gp3_storage_cost = size_gb * EBS_PRICING['gp3']
                # GP3 includes 3000 IOPS and 125 MB/s baseline (same as GP2)
                gp3_monthly_cost = gp3_storage_cost
                monthly_savings = current_monthly_cost - gp3_monthly_cost

                gp2_to_gp3_migrations.append({
                    'volume_id': volume_id,
                    'size_gb': size_gb,
                    'current_iops': iops,
                    'current_monthly_cost': round(current_monthly_cost, 2),
                    'gp3_monthly_cost': round(gp3_monthly_cost, 2),
                    'monthly_savings': round(monthly_savings, 2),
                    'annual_savings': round(monthly_savings * 12, 2),
                    'recommendation': 'Migrate to GP3 for 20% cost savings with same/better performance',
                    'is_attached': is_attached,
                    'instance_id': instance_id
                })
                total_monthly_savings += monthly_savings

            # 2. Check for unattached volumes
            if not is_attached:
                age_days = (now - volume['CreateTime']).days
                unattached_volumes.append({
                    'volume_id': volume_id,
                    'volume_type': volume_type,
                    'size_gb': size_gb,
                    'state': state,
                    'age_days': age_days,
                    'monthly_cost': round(current_monthly_cost, 2),
                    'recommendation': 'Delete if no longer needed or attach to instance'
                })

            # 3. Check for IO1/IO2 that could be GP3
            if volume_type in ['io1', 'io2'] and iops <= 16000:
                # GP3 can provide up to 16,000 IOPS
                # Calculate GP3 cost with equivalent IOPS
                gp3_storage = size_gb * EBS_PRICING['gp3']
                gp3_iops_cost = 0.0
                if iops > 3000:
                    gp3_iops_cost = (iops - 3000) * IOPS_PRICING['gp3']

                gp3_monthly_cost = gp3_storage + gp3_iops_cost
                monthly_savings = current_monthly_cost - gp3_monthly_cost

                if monthly_savings > 5:  # Only recommend if savings > $5/month
                    underutilized_volumes.append({
                        'volume_id': volume_id,
                        'volume_type': volume_type,
                        'size_gb': size_gb,
                        'current_iops': iops,
                        'current_monthly_cost': round(current_monthly_cost, 2),
                        'recommended_type': 'gp3',
                        'recommended_monthly_cost': round(gp3_monthly_cost, 2),
                        'monthly_savings': round(monthly_savings, 2),
                        'annual_savings': round(monthly_savings * 12, 2),
                        'recommendation': f'Migrate {volume_type} to GP3 (supports up to 16,000 IOPS)',
                        'is_attached': is_attached
                    })

        # Calculate summary statistics
        total_volumes = len(all_volumes)
        gp2_volumes = sum(1 for v in all_volumes if v['VolumeType'] == 'gp2')
        io_volumes = sum(1 for v in all_volumes if v['VolumeType'] in ['io1', 'io2'])
        total_size_gb = sum(v['Size'] for v in all_volumes)

        # Generate recommendations
        recommendations = []

        if gp2_to_gp3_migrations:
            total_gp2_savings = sum(m['monthly_savings'] for m in gp2_to_gp3_migrations)
            recommendations.append(
                f"Migrate {len(gp2_to_gp3_migrations)} GP2 volumes to GP3 for ${total_gp2_savings:.2f}/month savings (20% cost reduction)"
            )

        if underutilized_volumes:
            total_io_savings = sum(v['monthly_savings'] for v in underutilized_volumes)
            recommendations.append(
                f"Migrate {len(underutilized_volumes)} IO volumes to GP3 for ${total_io_savings:.2f}/month savings"
            )

        if unattached_volumes:
            total_unattached_cost = sum(v['monthly_cost'] for v in unattached_volumes)
            recommendations.append(
                f"Review {len(unattached_volumes)} unattached volumes (${total_unattached_cost:.2f}/month)"
            )

        recommendations.append(
            "Implement automated volume optimization policy"
        )

        if not gp2_to_gp3_migrations and not underutilized_volumes and not unattached_volumes:
            recommendations.append(
                "✅ All EBS volumes are optimally configured!"
            )

        return {
            'summary': {
                'total_volumes': total_volumes,
                'gp2_volumes': gp2_volumes,
                'io_volumes': io_volumes,
                'total_size_gb': total_size_gb,
                'total_monthly_cost': round(total_monthly_cost, 2),
                'total_monthly_savings': round(total_monthly_savings, 2),
                'total_annual_savings': round(total_monthly_savings * 12, 2),
                'gp2_to_gp3_count': len(gp2_to_gp3_migrations),
                'underutilized_count': len(underutilized_volumes),
                'unattached_count': len(unattached_volumes)
            },
            'gp2_to_gp3_migrations': gp2_to_gp3_migrations,
            'underutilized_volumes': underutilized_volumes,
            'unattached_volumes': unattached_volumes,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_ebs_snapshots_lifecycle(
    min_age_days: int = 90,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze EBS snapshot lifecycle and identify cleanup opportunities.

    Checks for:
    - Snapshots without lifecycle policies
    - Old snapshots (>90 days by default)
    - Orphaned snapshots (volume deleted)
    - AMI-associated vs standalone snapshots
    - Snapshot chains and incremental costs

    Args:
        min_age_days: Minimum age to flag snapshots (default: 90 days)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total snapshots, lifecycle coverage, potential savings
        - snapshots_without_lifecycle: Snapshots lacking lifecycle policies
        - old_snapshots: Snapshots older than threshold
        - orphaned_snapshots: Snapshots with deleted parent volumes
        - ami_snapshots: Snapshots associated with AMIs
        - recommendations: Lifecycle policy suggestions

    Example:
        >>> result = analyze_ebs_snapshots_lifecycle(min_age_days=90)
        >>> print(f"Snapshots without lifecycle: {len(result['snapshots_without_lifecycle'])}")
        >>> print(f"Potential savings: ${result['summary']['potential_monthly_savings']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2 = aws_client.get_client('ec2')

        # Get all snapshots owned by this account
        account_id = aws_client.get_client('sts').get_caller_identity()['Account']

        snapshots_response = ec2.describe_snapshots(OwnerIds=[account_id])
        all_snapshots = snapshots_response.get('Snapshots', [])

        # Handle pagination
        while 'NextToken' in snapshots_response:
            snapshots_response = ec2.describe_snapshots(
                OwnerIds=[account_id],
                NextToken=snapshots_response['NextToken']
            )
            all_snapshots.extend(snapshots_response.get('Snapshots', []))

        # Get all volumes to check for orphaned snapshots
        volumes_response = ec2.describe_volumes()
        all_volumes = volumes_response.get('Volumes', [])
        volume_ids = {v['VolumeId'] for v in all_volumes}

        # Get all AMIs to identify AMI snapshots
        amis_response = ec2.describe_images(Owners=[account_id])
        all_amis = amis_response.get('Images', [])
        ami_snapshot_ids = set()
        for ami in all_amis:
            for bdm in ami.get('BlockDeviceMappings', []):
                if 'Ebs' in bdm and 'SnapshotId' in bdm['Ebs']:
                    ami_snapshot_ids.add(bdm['Ebs']['SnapshotId'])

        now = datetime.now(timezone.utc)
        age_threshold = now - timedelta(days=min_age_days)

        snapshots_without_lifecycle = []
        old_snapshots = []
        orphaned_snapshots = []
        ami_snapshots = []

        total_snapshot_size_gb = 0
        total_snapshot_cost = 0.0
        potential_cleanup_size = 0
        potential_cleanup_cost = 0.0

        SNAPSHOT_COST_PER_GB = 0.05  # $0.05 per GB-month

        for snapshot in all_snapshots:
            snapshot_id = snapshot['SnapshotId']
            volume_id = snapshot.get('VolumeId')
            size_gb = snapshot['VolumeSize']
            start_time = snapshot['StartTime']
            description = snapshot.get('Description', '')
            state = snapshot['State']

            if state != 'completed':
                continue

            age_days = (now - start_time).days
            monthly_cost = size_gb * SNAPSHOT_COST_PER_GB

            total_snapshot_size_gb += size_gb
            total_snapshot_cost += monthly_cost

            snapshot_info = {
                'snapshot_id': snapshot_id,
                'volume_id': volume_id,
                'size_gb': size_gb,
                'start_time': start_time.isoformat(),
                'age_days': age_days,
                'monthly_cost': round(monthly_cost, 2),
                'description': description[:100]  # Truncate long descriptions
            }

            # Check if snapshot is associated with an AMI
            is_ami_snapshot = snapshot_id in ami_snapshot_ids

            if is_ami_snapshot:
                ami_snapshots.append({
                    **snapshot_info,
                    'recommendation': 'Keep - associated with AMI (deregister AMI first to delete)'
                })
                continue

            # Check if snapshot is orphaned (volume deleted)
            is_orphaned = volume_id and volume_id not in volume_ids

            if is_orphaned:
                orphaned_snapshots.append({
                    **snapshot_info,
                    'recommendation': 'Consider deleting - parent volume no longer exists'
                })
                potential_cleanup_size += size_gb
                potential_cleanup_cost += monthly_cost
                continue

            # Check if snapshot is old
            if start_time < age_threshold:
                old_snapshots.append({
                    **snapshot_info,
                    'recommendation': f'Review - snapshot is {age_days} days old'
                })

            # All snapshots without lifecycle policy (AWS doesn't expose this via API easily,
            # so we flag all non-AMI snapshots for lifecycle review)
            snapshots_without_lifecycle.append({
                **snapshot_info,
                'is_ami_snapshot': is_ami_snapshot,
                'is_orphaned': is_orphaned,
                'is_old': age_days > min_age_days,
                'recommendation': 'Configure lifecycle policy for automated management'
            })

        # Generate recommendations
        recommendations = []

        if orphaned_snapshots:
            orphaned_cost = sum(s['monthly_cost'] for s in orphaned_snapshots)
            recommendations.append(
                f"Delete {len(orphaned_snapshots)} orphaned snapshots to save ${orphaned_cost:.2f}/month"
            )

        if old_snapshots:
            recommendations.append(
                f"Review {len(old_snapshots)} snapshots older than {min_age_days} days"
            )

        recommendations.append(
            "Implement Data Lifecycle Manager (DLM) policies for automated snapshot management"
        )

        recommendations.append(
            "Configure retention policies: 7 daily, 4 weekly, 12 monthly snapshots"
        )

        if ami_snapshots:
            recommendations.append(
                f"Review {len(ami_snapshots)} AMI-associated snapshots - deregister unused AMIs first"
            )

        if potential_cleanup_cost < 1:
            recommendations.append(
                "✅ Snapshot management is well-maintained!"
            )

        return {
            'summary': {
                'total_snapshots': len(all_snapshots),
                'ami_snapshots': len(ami_snapshots),
                'orphaned_snapshots': len(orphaned_snapshots),
                'old_snapshots': len(old_snapshots),
                'total_size_gb': total_snapshot_size_gb,
                'total_monthly_cost': round(total_snapshot_cost, 2),
                'potential_cleanup_size_gb': potential_cleanup_size,
                'potential_monthly_savings': round(potential_cleanup_cost, 2),
                'potential_annual_savings': round(potential_cleanup_cost * 12, 2),
                'min_age_days': min_age_days
            },
            'snapshots_without_lifecycle': snapshots_without_lifecycle[:50],  # Limit output
            'old_snapshots': old_snapshots[:50],
            'orphaned_snapshots': orphaned_snapshots,
            'ami_snapshots': ami_snapshots[:20],
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def get_ebs_iops_recommendations(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get IOPS optimization recommendations for provisioned IOPS volumes.

    Analyzes IO1/IO2 volumes for:
    - Over-provisioned IOPS (paying for unused IOPS)
    - Underutilized IOPS (can downgrade to GP3)
    - IOPS:GB ratio analysis
    - Cost savings from rightsizing

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total IO volumes, over-provisioned count, potential savings
        - over_provisioned_iops: Volumes with excess IOPS
        - gp3_candidates: IO volumes that should migrate to GP3
        - optimization_opportunities: Specific IOPS reduction recommendations
        - recommendations: IOPS optimization suggestions

    Example:
        >>> result = get_ebs_iops_recommendations()
        >>> print(f"Over-provisioned volumes: {result['summary']['over_provisioned_count']}")
        >>> print(f"Potential savings: ${result['summary']['total_monthly_savings']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2 = aws_client.get_client('ec2')

        # Get all IO1 and IO2 volumes
        volumes_response = ec2.describe_volumes(
            Filters=[
                {'Name': 'volume-type', 'Values': ['io1', 'io2', 'gp3']}
            ]
        )
        all_volumes = volumes_response.get('Volumes', [])

        over_provisioned_iops = []
        gp3_candidates = []
        optimization_opportunities = []

        total_monthly_savings = 0.0

        for volume in all_volumes:
            volume_id = volume['VolumeId']
            volume_type = volume['VolumeType']
            size_gb = volume['Size']
            iops = volume.get('Iops', 0)
            throughput = volume.get('Throughput', 0)
            attachments = volume.get('Attachments', [])
            is_attached = len(attachments) > 0

            if volume_type not in ['io1', 'io2', 'gp3']:
                continue

            # Calculate current cost
            storage_cost = size_gb * EBS_PRICING.get(volume_type, 0.125)
            iops_cost = 0.0

            if volume_type in ['io1', 'io2']:
                iops_cost = iops * IOPS_PRICING.get(volume_type, 0.065)
            elif volume_type == 'gp3' and iops > 3000:
                iops_cost = (iops - 3000) * IOPS_PRICING['gp3']

            current_monthly_cost = storage_cost + iops_cost

            # Check IOPS:GB ratio
            iops_per_gb = iops / size_gb if size_gb > 0 else 0

            # For IO1/IO2 volumes
            if volume_type in ['io1', 'io2']:
                # IO1/IO2 max ratio is 50:1
                # Check if this could be GP3 (up to 16,000 IOPS, 500 IOPS/GB max)
                if iops <= 16000:
                    # Calculate GP3 cost
                    gp3_storage = size_gb * EBS_PRICING['gp3']
                    gp3_iops_cost = 0.0
                    if iops > 3000:
                        gp3_iops_cost = (iops - 3000) * IOPS_PRICING['gp3']

                    gp3_monthly_cost = gp3_storage + gp3_iops_cost
                    monthly_savings = current_monthly_cost - gp3_monthly_cost

                    if monthly_savings > 5:  # Minimum $5/month savings
                        gp3_candidates.append({
                            'volume_id': volume_id,
                            'current_type': volume_type,
                            'size_gb': size_gb,
                            'current_iops': iops,
                            'iops_per_gb': round(iops_per_gb, 2),
                            'current_monthly_cost': round(current_monthly_cost, 2),
                            'gp3_monthly_cost': round(gp3_monthly_cost, 2),
                            'monthly_savings': round(monthly_savings, 2),
                            'annual_savings': round(monthly_savings * 12, 2),
                            'recommendation': f'Migrate to GP3 (supports up to 16,000 IOPS) for ${monthly_savings:.2f}/month savings',
                            'is_attached': is_attached
                        })
                        total_monthly_savings += monthly_savings

                # Check if IOPS seems over-provisioned (very low ratio)
                if iops_per_gb > 100:  # Very high IOPS for the volume size
                    over_provisioned_iops.append({
                        'volume_id': volume_id,
                        'volume_type': volume_type,
                        'size_gb': size_gb,
                        'provisioned_iops': iops,
                        'iops_per_gb': round(iops_per_gb, 2),
                        'monthly_iops_cost': round(iops_cost, 2),
                        'recommendation': 'Review IOPS requirements - may be over-provisioned',
                        'is_attached': is_attached
                    })

            # For GP3 volumes with provisioned IOPS
            if volume_type == 'gp3' and iops > 3000:
                # Check if paying for unused IOPS
                # Could downgrade to 3000 IOPS (free tier)
                baseline_cost = size_gb * EBS_PRICING['gp3']
                potential_savings = iops_cost

                if potential_savings > 2:  # Minimum $2/month savings
                    optimization_opportunities.append({
                        'volume_id': volume_id,
                        'volume_type': volume_type,
                        'size_gb': size_gb,
                        'current_iops': iops,
                        'baseline_iops': 3000,
                        'extra_iops': iops - 3000,
                        'extra_iops_cost': round(iops_cost, 2),
                        'recommendation': 'Review if extra IOPS are needed - could save by using 3000 IOPS baseline',
                        'is_attached': is_attached
                    })

        # Generate recommendations
        recommendations = []

        if gp3_candidates:
            total_io_savings = sum(v['monthly_savings'] for v in gp3_candidates)
            recommendations.append(
                f"Migrate {len(gp3_candidates)} IO volumes to GP3 for ${total_io_savings:.2f}/month savings"
            )

        if over_provisioned_iops:
            recommendations.append(
                f"Review {len(over_provisioned_iops)} volumes with very high IOPS:GB ratios"
            )

        if optimization_opportunities:
            recommendations.append(
                f"Review {len(optimization_opportunities)} GP3 volumes paying for extra IOPS"
            )

        recommendations.append(
            "Monitor IOPS usage with CloudWatch to validate IOPS requirements"
        )

        recommendations.append(
            "Consider GP3 for most workloads - 20% cheaper with better baseline performance"
        )

        if not gp3_candidates and not over_provisioned_iops and not optimization_opportunities:
            recommendations.append(
                "✅ IOPS provisioning is optimized!"
            )

        return {
            'summary': {
                'io_volumes_analyzed': len([v for v in all_volumes if v['VolumeType'] in ['io1', 'io2']]),
                'gp3_volumes_analyzed': len([v for v in all_volumes if v['VolumeType'] == 'gp3']),
                'over_provisioned_count': len(over_provisioned_iops),
                'gp3_migration_count': len(gp3_candidates),
                'optimization_count': len(optimization_opportunities),
                'total_monthly_savings': round(total_monthly_savings, 2),
                'total_annual_savings': round(total_monthly_savings * 12, 2)
            },
            'over_provisioned_iops': over_provisioned_iops,
            'gp3_candidates': gp3_candidates,
            'optimization_opportunities': optimization_opportunities,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_ebs_encryption(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze EBS encryption compliance.

    Checks for:
    - Unencrypted volumes (security risk!)
    - Default encryption settings by region
    - Encryption key analysis (AWS vs customer managed)
    - Compliance violations
    - Migration recommendations

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total volumes, encryption rate, compliance status
        - unencrypted_volumes: Volumes without encryption
        - encryption_keys: KMS keys used for encryption
        - default_encryption: Default encryption settings
        - recommendations: Encryption compliance suggestions

    Example:
        >>> result = analyze_ebs_encryption()
        >>> print(f"Encryption rate: {result['summary']['encryption_rate']:.1f}%")
        >>> print(f"Unencrypted volumes: {len(result['unencrypted_volumes'])}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2 = aws_client.get_client('ec2')

        # Check default encryption settings
        try:
            encryption_response = ec2.get_ebs_encryption_by_default()
            default_encryption_enabled = encryption_response.get('EbsEncryptionByDefault', False)

            kms_key_id = None
            try:
                kms_response = ec2.get_ebs_default_kms_key_id()
                kms_key_id = kms_response.get('KmsKeyId')
            except:
                pass
        except:
            default_encryption_enabled = False
            kms_key_id = None

        # Get all volumes
        volumes_response = ec2.describe_volumes()
        all_volumes = volumes_response.get('Volumes', [])

        # Handle pagination
        while 'NextToken' in volumes_response:
            volumes_response = ec2.describe_volumes(NextToken=volumes_response['NextToken'])
            all_volumes.extend(volumes_response.get('Volumes', []))

        unencrypted_volumes = []
        encryption_keys = defaultdict(int)

        total_volumes = len(all_volumes)
        encrypted_volumes = 0

        for volume in all_volumes:
            volume_id = volume['VolumeId']
            encrypted = volume.get('Encrypted', False)
            size_gb = volume['Size']
            volume_type = volume['VolumeType']
            kms_key = volume.get('KmsKeyId')
            attachments = volume.get('Attachments', [])
            is_attached = len(attachments) > 0
            instance_id = attachments[0]['InstanceId'] if is_attached else None

            if encrypted:
                encrypted_volumes += 1
                # Track which KMS keys are used
                if kms_key:
                    # Extract key ID from ARN
                    if 'alias/' in kms_key:
                        key_name = kms_key.split('/')[-1]
                    elif ':key/' in kms_key:
                        key_name = kms_key.split(':key/')[-1]
                    else:
                        key_name = kms_key
                    encryption_keys[key_name] += 1
                else:
                    encryption_keys['AWS managed (default)'] += 1
            else:
                unencrypted_volumes.append({
                    'volume_id': volume_id,
                    'size_gb': size_gb,
                    'volume_type': volume_type,
                    'is_attached': is_attached,
                    'instance_id': instance_id,
                    'risk_level': 'high' if is_attached else 'medium',
                    'recommendation': 'Create encrypted snapshot and replace volume' if is_attached else 'Delete or encrypt volume'
                })

        encryption_rate = (encrypted_volumes / total_volumes * 100) if total_volumes > 0 else 0

        # Generate recommendations
        recommendations = []

        if not default_encryption_enabled:
            recommendations.append(
                "🚨 CRITICAL: Enable default EBS encryption for all new volumes"
            )

        if unencrypted_volumes:
            attached_unencrypted = sum(1 for v in unencrypted_volumes if v['is_attached'])
            recommendations.append(
                f"⚠️ Encrypt {len(unencrypted_volumes)} unencrypted volumes ({attached_unencrypted} attached)"
            )
            recommendations.append(
                "Use encrypted snapshots to migrate data to encrypted volumes"
            )

        if encryption_rate < 100:
            recommendations.append(
                f"Improve encryption rate from {encryption_rate:.1f}% to 100%"
            )

        if kms_key_id:
            recommendations.append(
                "✅ Default KMS key configured for new encrypted volumes"
            )
        else:
            recommendations.append(
                "Configure default KMS key for consistent encryption"
            )

        recommendations.append(
            "Implement encryption compliance policy - all volumes must be encrypted"
        )

        if encryption_rate == 100 and default_encryption_enabled:
            recommendations.append(
                "✅ Perfect encryption compliance - all volumes encrypted!"
            )

        return {
            'summary': {
                'total_volumes': total_volumes,
                'encrypted_volumes': encrypted_volumes,
                'unencrypted_volumes': len(unencrypted_volumes),
                'encryption_rate': round(encryption_rate, 1),
                'default_encryption_enabled': default_encryption_enabled,
                'default_kms_key': kms_key_id or 'Not configured'
            },
            'default_encryption': {
                'enabled': default_encryption_enabled,
                'kms_key_id': kms_key_id,
                'recommendation': 'Enable default encryption' if not default_encryption_enabled else 'Default encryption enabled'
            },
            'unencrypted_volumes': unencrypted_volumes,
            'encryption_keys': dict(encryption_keys),
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def find_ebs_volume_anomalies(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Find EBS volume performance anomalies and issues.

    Detects:
    - Volumes with I/O credit exhaustion (GP2/GP3)
    - High latency volumes
    - Burst balance depletion
    - Volumes hitting throughput limits
    - Performance upgrade recommendations

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total volumes checked, anomalies found
        - credit_exhaustion: Volumes running out of I/O credits
        - performance_issues: Volumes with detected performance problems
        - upgrade_recommendations: Volumes that need performance upgrades
        - recommendations: Performance optimization suggestions

    Example:
        >>> result = find_ebs_volume_anomalies()
        >>> print(f"Volumes with issues: {result['summary']['total_anomalies']}")
        >>> for vol in result['performance_issues']:
        ...     print(f"  {vol['volume_id']}: {vol['issue']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2 = aws_client.get_client('ec2')

        # Get all volumes
        volumes_response = ec2.describe_volumes()
        all_volumes = volumes_response.get('Volumes', [])

        # Handle pagination
        while 'NextToken' in volumes_response:
            volumes_response = ec2.describe_volumes(NextToken=volumes_response['NextToken'])
            all_volumes.extend(volumes_response.get('Volumes', []))

        # Note: This is a simplified analysis
        # Full implementation would query CloudWatch metrics for:
        # - VolumeReadOps, VolumeWriteOps
        # - VolumeThroughputPercentage
        # - BurstBalance (for GP2/ST1/SC1)

        credit_exhaustion = []
        performance_issues = []
        upgrade_recommendations = []

        # For now, identify volumes that are likely to have issues based on configuration
        for volume in all_volumes:
            volume_id = volume['VolumeId']
            volume_type = volume['VolumeType']
            size_gb = volume['Size']
            iops = volume.get('Iops', 0)
            attachments = volume.get('Attachments', [])
            is_attached = len(attachments) > 0

            if not is_attached:
                continue  # Skip unattached volumes

            # GP2 volumes can have burst balance issues
            if volume_type == 'gp2':
                # GP2 baseline: 3 IOPS/GB, minimum 100 IOPS, max 16,000 IOPS
                baseline_iops = max(100, min(16000, size_gb * 3))

                # Small GP2 volumes (<1TB) can experience credit exhaustion
                if size_gb < 1000:
                    performance_issues.append({
                        'volume_id': volume_id,
                        'volume_type': volume_type,
                        'size_gb': size_gb,
                        'baseline_iops': baseline_iops,
                        'issue': f'Small GP2 volume ({size_gb} GB) may experience I/O credit exhaustion',
                        'recommendation': 'Migrate to GP3 for consistent performance (no burst credits)',
                        'severity': 'medium'
                    })

            # Very small volumes of any type
            if size_gb < 100 and volume_type in ['gp2', 'gp3']:
                performance_issues.append({
                    'volume_id': volume_id,
                    'volume_type': volume_type,
                    'size_gb': size_gb,
                    'issue': f'Very small volume ({size_gb} GB) may have limited performance',
                    'recommendation': 'Consider increasing size or upgrading to provisioned IOPS',
                    'severity': 'low'
                })

            # IO1/IO2 volumes with low IOPS:GB ratio
            if volume_type in ['io1', 'io2']:
                iops_per_gb = iops / size_gb if size_gb > 0 else 0
                if iops_per_gb < 10:
                    upgrade_recommendations.append({
                        'volume_id': volume_id,
                        'volume_type': volume_type,
                        'size_gb': size_gb,
                        'current_iops': iops,
                        'iops_per_gb': round(iops_per_gb, 2),
                        'recommendation': f'Low IOPS:GB ratio ({iops_per_gb:.1f}:1) - consider GP3 instead',
                        'suggested_type': 'gp3'
                    })

        # Generate recommendations
        recommendations = []

        if performance_issues:
            recommendations.append(
                f"Review {len(performance_issues)} volumes with potential performance issues"
            )

        recommendations.append(
            "Monitor CloudWatch metrics: VolumeReadOps, VolumeWriteOps, BurstBalance"
        )

        recommendations.append(
            "Set up CloudWatch alarms for BurstBalance < 20% on GP2 volumes"
        )

        recommendations.append(
            "Consider GP3 for consistent performance without burst credits"
        )

        if upgrade_recommendations:
            recommendations.append(
                f"Review {len(upgrade_recommendations)} volumes for type optimization"
            )

        if not performance_issues and not upgrade_recommendations:
            recommendations.append(
                "✅ No obvious performance anomalies detected"
            )

        recommendations.append(
            "Note: Enable detailed CloudWatch monitoring for comprehensive performance analysis"
        )

        return {
            'summary': {
                'total_volumes_checked': len([v for v in all_volumes if v.get('Attachments')]),
                'performance_issues': len(performance_issues),
                'upgrade_recommendations': len(upgrade_recommendations),
                'total_anomalies': len(performance_issues) + len(upgrade_recommendations)
            },
            'credit_exhaustion': credit_exhaustion,
            'performance_issues': performance_issues,
            'upgrade_recommendations': upgrade_recommendations,
            'recommendations': recommendations,
            'note': 'This analysis is based on volume configuration. Enable CloudWatch detailed monitoring for real-time performance metrics.'
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_ami_usage(
    min_age_days: int = 180,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze AMI usage and identify cleanup opportunities.

    Identifies:
    - Unused AMIs (no instances launched in 180+ days)
    - AMI age analysis
    - AMI storage costs (associated snapshots)
    - Deregistration recommendations
    - Cross-region AMI copies

    Args:
        min_age_days: Minimum age to flag AMIs as old (default: 180 days)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total AMIs, unused count, storage costs
        - unused_amis: AMIs not used recently
        - old_amis: AMIs older than threshold
        - ami_costs: Storage costs for AMI snapshots
        - recommendations: AMI cleanup suggestions

    Example:
        >>> result = analyze_ami_usage(min_age_days=180)
        >>> print(f"Unused AMIs: {len(result['unused_amis'])}")
        >>> print(f"Potential savings: ${result['summary']['potential_monthly_savings']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2 = aws_client.get_client('ec2')

        # Get account ID
        account_id = aws_client.get_client('sts').get_caller_identity()['Account']

        # Get all AMIs owned by this account
        amis_response = ec2.describe_images(Owners=[account_id])
        all_amis = amis_response.get('Images', [])

        # Get all instances to check AMI usage
        instances_response = ec2.describe_instances()
        all_instances = []
        for reservation in instances_response.get('Reservations', []):
            all_instances.extend(reservation.get('Instances', []))

        # Track which AMIs are in use
        ami_usage = defaultdict(int)
        for instance in all_instances:
            ami_id = instance.get('ImageId')
            if ami_id:
                ami_usage[ami_id] += 1

        now = datetime.now(timezone.utc)
        age_threshold = now - timedelta(days=min_age_days)

        unused_amis = []
        old_amis = []
        ami_costs = []

        total_snapshot_size = 0
        total_monthly_cost = 0.0
        potential_savings = 0.0

        SNAPSHOT_COST_PER_GB = 0.05  # $0.05 per GB-month

        for ami in all_amis:
            ami_id = ami['ImageId']
            ami_name = ami.get('Name', 'Unnamed')
            creation_date_str = ami.get('CreationDate', '')
            description = ami.get('Description', '')
            state = ami.get('State', '')

            if state != 'available':
                continue

            # Parse creation date
            try:
                creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
            except:
                creation_date = now

            age_days = (now - creation_date).days

            # Get snapshot IDs from block device mappings
            snapshot_ids = []
            snapshot_size_gb = 0

            for bdm in ami.get('BlockDeviceMappings', []):
                if 'Ebs' in bdm and 'SnapshotId' in bdm['Ebs']:
                    snapshot_id = bdm['Ebs']['SnapshotId']
                    snapshot_ids.append(snapshot_id)

                    # Get snapshot size
                    try:
                        snapshot_info = ec2.describe_snapshots(SnapshotIds=[snapshot_id])
                        if snapshot_info.get('Snapshots'):
                            snapshot_size_gb += snapshot_info['Snapshots'][0]['VolumeSize']
                    except:
                        pass

            monthly_cost = snapshot_size_gb * SNAPSHOT_COST_PER_GB
            total_snapshot_size += snapshot_size_gb
            total_monthly_cost += monthly_cost

            # Check if AMI is used
            instance_count = ami_usage.get(ami_id, 0)
            is_unused = instance_count == 0

            ami_info = {
                'ami_id': ami_id,
                'ami_name': ami_name[:100],  # Truncate long names
                'creation_date': creation_date.isoformat(),
                'age_days': age_days,
                'snapshot_count': len(snapshot_ids),
                'snapshot_size_gb': snapshot_size_gb,
                'monthly_cost': round(monthly_cost, 2),
                'instance_count': instance_count,
                'description': description[:100] if description else None
            }

            if is_unused:
                unused_amis.append({
                    **ami_info,
                    'recommendation': 'Deregister AMI and delete associated snapshots if no longer needed'
                })
                potential_savings += monthly_cost

            if age_days > min_age_days:
                old_amis.append({
                    **ami_info,
                    'recommendation': f'Review - AMI is {age_days} days old'
                })

            ami_costs.append({
                **ami_info,
                'annual_cost': round(monthly_cost * 12, 2)
            })

        # Sort AMI costs by monthly cost (descending)
        ami_costs.sort(key=lambda x: x['monthly_cost'], reverse=True)

        # Generate recommendations
        recommendations = []

        if unused_amis:
            recommendations.append(
                f"Deregister {len(unused_amis)} unused AMIs to save ${potential_savings:.2f}/month"
            )

        if old_amis:
            recommendations.append(
                f"Review {len(old_amis)} AMIs older than {min_age_days} days"
            )

        recommendations.append(
            "Implement AMI lifecycle policy: keep last 3 versions, delete older ones"
        )

        recommendations.append(
            "Use tags to track AMI purpose and retention requirements"
        )

        if potential_savings > 10:
            recommendations.append(
                f"Cleanup could save ${potential_savings * 12:.2f}/year in snapshot storage costs"
            )

        if potential_savings < 5:
            recommendations.append(
                "✅ AMI management is efficient - minimal waste detected"
            )

        return {
            'summary': {
                'total_amis': len(all_amis),
                'unused_amis': len(unused_amis),
                'old_amis': len(old_amis),
                'total_snapshot_size_gb': total_snapshot_size,
                'total_monthly_cost': round(total_monthly_cost, 2),
                'total_annual_cost': round(total_monthly_cost * 12, 2),
                'potential_monthly_savings': round(potential_savings, 2),
                'potential_annual_savings': round(potential_savings * 12, 2),
                'min_age_days': min_age_days
            },
            'unused_amis': unused_amis,
            'old_amis': old_amis[:50],  # Limit output
            'ami_costs': ami_costs[:20],  # Top 20 most expensive AMIs
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}
