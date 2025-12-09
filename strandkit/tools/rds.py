"""
RDS/Database tools for StrandKit.

This module provides comprehensive RDS analysis tools for:
- Performance monitoring and optimization
- Cost analysis and rightsizing
- Security auditing
- Backup compliance
- Idle database detection

All functions are decorated with @tool for AWS Strands Agents integration
and can also be used standalone.

PRICING NOTES:
- RDS pricing varies significantly by engine, edition, and licensing model
- Oracle/SQL Server License Included can be 2-8x open-source pricing
- io1/io2 IOPS costs can exceed storage costs by 10x or more
- All estimates are for us-east-1; other regions may vary 10-30%
- Use AWS Pricing Calculator for accurate quotes
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from strands import tool
from strandkit.core.aws_client import AWSClient


# =============================================================================
# RDS PRICING DATA (us-east-1, as of 2024)
# =============================================================================
# Source: https://instances.vantage.sh/aws/rds/ and AWS pricing pages
# These are approximate and should be updated periodically

# Instance hourly costs by class and engine
# Format: {instance_class: {engine_key: hourly_cost}}
# Engine keys: 'mysql', 'postgres', 'mariadb', 'oracle-se2-li', 'oracle-ee-byol',
#              'sqlserver-ex', 'sqlserver-web', 'sqlserver-se', 'sqlserver-ee'
RDS_INSTANCE_PRICING = {
    # T3 Burstable instances
    'db.t3.micro': {
        'mysql': 0.017, 'postgres': 0.017, 'mariadb': 0.017,
        'oracle-se2-li': 0.026, 'oracle-ee-byol': 0.017,
        'sqlserver-ex': 0.017, 'sqlserver-web': 0.019,
        'sqlserver-se': 0.122, 'sqlserver-ee': 0.234,
    },
    'db.t3.small': {
        'mysql': 0.034, 'postgres': 0.034, 'mariadb': 0.034,
        'oracle-se2-li': 0.052, 'oracle-ee-byol': 0.034,
        'sqlserver-ex': 0.034, 'sqlserver-web': 0.038,
        'sqlserver-se': 0.244, 'sqlserver-ee': 0.468,
    },
    'db.t3.medium': {
        'mysql': 0.068, 'postgres': 0.068, 'mariadb': 0.068,
        'oracle-se2-li': 0.104, 'oracle-ee-byol': 0.068,
        'sqlserver-ex': 0.068, 'sqlserver-web': 0.076,
        'sqlserver-se': 0.296, 'sqlserver-ee': 0.544,
    },
    'db.t3.large': {
        'mysql': 0.136, 'postgres': 0.136, 'mariadb': 0.136,
        'oracle-se2-li': 0.208, 'oracle-ee-byol': 0.136,
        'sqlserver-ex': 0.136, 'sqlserver-web': 0.152,
        'sqlserver-se': 0.592, 'sqlserver-ee': 1.088,
    },
    # T4g Graviton instances (not available for Oracle/SQL Server)
    'db.t4g.micro': {
        'mysql': 0.016, 'postgres': 0.016, 'mariadb': 0.016,
    },
    'db.t4g.small': {
        'mysql': 0.032, 'postgres': 0.032, 'mariadb': 0.032,
    },
    'db.t4g.medium': {
        'mysql': 0.064, 'postgres': 0.064, 'mariadb': 0.064,
    },
    # M5 General Purpose instances
    'db.m5.large': {
        'mysql': 0.235, 'postgres': 0.235, 'mariadb': 0.234,
        'oracle-se2-li': 0.248, 'oracle-ee-byol': 0.208,
        'sqlserver-ex': 0.189, 'sqlserver-web': 0.198,
        'sqlserver-se': 0.570, 'sqlserver-ee': 1.322,
    },
    'db.m5.xlarge': {
        'mysql': 0.470, 'postgres': 0.470, 'mariadb': 0.468,
        'oracle-se2-li': 0.496, 'oracle-ee-byol': 0.416,
        'sqlserver-ex': 0.378, 'sqlserver-web': 0.396,
        'sqlserver-se': 1.140, 'sqlserver-ee': 2.644,
    },
    'db.m5.2xlarge': {
        'mysql': 0.940, 'postgres': 0.940, 'mariadb': 0.936,
        'oracle-se2-li': 0.992, 'oracle-ee-byol': 0.832,
        'sqlserver-ex': 0.756, 'sqlserver-web': 0.792,
        'sqlserver-se': 2.280, 'sqlserver-ee': 5.288,
    },
    # R5 Memory Optimized instances
    'db.r5.large': {
        'mysql': 0.290, 'postgres': 0.290, 'mariadb': 0.288,
        'oracle-se2-li': 0.306, 'oracle-ee-byol': 0.256,
        'sqlserver-ex': 0.232, 'sqlserver-web': 0.244,
        'sqlserver-se': 0.616, 'sqlserver-ee': 1.368,
    },
    'db.r5.xlarge': {
        'mysql': 0.580, 'postgres': 0.580, 'mariadb': 0.576,
        'oracle-se2-li': 0.612, 'oracle-ee-byol': 0.512,
        'sqlserver-ex': 0.464, 'sqlserver-web': 0.488,
        'sqlserver-se': 1.232, 'sqlserver-ee': 2.736,
    },
    'db.r5.2xlarge': {
        'mysql': 1.160, 'postgres': 1.160, 'mariadb': 1.152,
        'oracle-se2-li': 1.224, 'oracle-ee-byol': 1.024,
        'sqlserver-ex': 0.928, 'sqlserver-web': 0.976,
        'sqlserver-se': 2.464, 'sqlserver-ee': 5.472,
    },
}

# Storage pricing per GB-month
# Note: RDS gp2 and gp3 are the SAME price ($0.115), unlike EBS where gp3 is cheaper
RDS_STORAGE_PRICING = {
    'gp2': 0.115,
    'gp3': 0.115,  # Same as gp2 for RDS (different from EBS!)
    'io1': 0.125,  # Plus IOPS cost
    'io2': 0.125,  # Plus IOPS cost (same as io1)
    'magnetic': 0.10,  # Legacy standard storage
}

# IOPS pricing per provisioned IOPS-month (for io1/io2)
# Note: RDS gp3 IOPS pricing ($0.02) differs from EBS gp3 ($0.005)
RDS_IOPS_PRICING = {
    'io1': 0.10,
    'io2': 0.10,  # Same as io1
    'gp3': 0.02,  # Only for IOPS above baseline 3000 (RDS rate, not EBS rate)
}

# Backup storage pricing (beyond free allocation)
RDS_BACKUP_PRICING_PER_GB = 0.095


def _get_engine_key(engine: str, license_model: str = None) -> str:
    """
    Convert RDS engine name to pricing key.

    Args:
        engine: RDS engine (e.g., 'mysql', 'oracle-se2', 'sqlserver-ee')
        license_model: 'license-included' or 'bring-your-own-license'

    Returns:
        Pricing key for RDS_INSTANCE_PRICING lookup
    """
    engine_lower = engine.lower()

    # Open source engines
    if 'mysql' in engine_lower:
        return 'mysql'
    if 'postgres' in engine_lower:
        return 'postgres'
    if 'mariadb' in engine_lower:
        return 'mariadb'

    # Oracle
    if 'oracle' in engine_lower:
        if license_model and 'bring' in license_model.lower():
            return 'oracle-ee-byol'
        # License included - check edition
        if 'se2' in engine_lower or 'se1' in engine_lower:
            return 'oracle-se2-li'
        return 'oracle-ee-byol'  # Default to BYOL for EE

    # SQL Server
    if 'sqlserver' in engine_lower:
        if 'express' in engine_lower or '-ex' in engine_lower:
            return 'sqlserver-ex'
        if 'web' in engine_lower:
            return 'sqlserver-web'
        if 'enterprise' in engine_lower or '-ee' in engine_lower:
            return 'sqlserver-ee'
        if 'standard' in engine_lower or '-se' in engine_lower:
            return 'sqlserver-se'
        return 'sqlserver-se'  # Default to Standard

    # Default to MySQL pricing for unknown engines
    return 'mysql'


def _estimate_instance_cost(
    instance_class: str,
    engine: str,
    license_model: str = None,
    multi_az: bool = False
) -> Dict[str, Any]:
    """
    Estimate hourly and monthly instance cost.

    Args:
        instance_class: RDS instance class (e.g., 'db.m5.large')
        engine: Database engine
        license_model: Licensing model
        multi_az: Whether Multi-AZ is enabled

    Returns:
        Dict with hourly_cost, monthly_cost, and pricing notes
    """
    engine_key = _get_engine_key(engine, license_model)

    # Look up pricing
    if instance_class in RDS_INSTANCE_PRICING:
        class_pricing = RDS_INSTANCE_PRICING[instance_class]
        if engine_key in class_pricing:
            hourly_cost = class_pricing[engine_key]
        else:
            # Engine not available for this instance class (e.g., T4g + Oracle)
            hourly_cost = class_pricing.get('mysql', 0.10)
            engine_key = f"{engine_key} (estimated from mysql)"
    else:
        # Unknown instance class - rough estimate
        hourly_cost = 0.20
        engine_key = f"{engine_key} (unknown instance class)"

    monthly_hours = 730
    monthly_cost = hourly_cost * monthly_hours

    if multi_az:
        monthly_cost *= 2

    return {
        'hourly_cost': round(hourly_cost, 4),
        'monthly_cost': round(monthly_cost, 2),
        'engine_key': engine_key,
        'multi_az_multiplier': 2 if multi_az else 1,
    }


def _estimate_storage_cost(
    storage_type: str,
    allocated_storage_gb: int,
    provisioned_iops: int = 0,
    multi_az: bool = False
) -> Dict[str, Any]:
    """
    Estimate monthly storage cost including IOPS.

    Args:
        storage_type: Storage type (gp2, gp3, io1, io2)
        allocated_storage_gb: Allocated storage in GB
        provisioned_iops: Provisioned IOPS (for io1/io2)
        multi_az: Whether Multi-AZ is enabled

    Returns:
        Dict with storage_cost, iops_cost, total, and breakdown
    """
    storage_type_lower = storage_type.lower() if storage_type else 'gp2'

    # Base storage cost
    storage_rate = RDS_STORAGE_PRICING.get(storage_type_lower, 0.115)
    storage_cost = allocated_storage_gb * storage_rate

    # IOPS cost (io1/io2)
    iops_cost = 0.0
    if storage_type_lower in ('io1', 'io2') and provisioned_iops > 0:
        iops_rate = RDS_IOPS_PRICING.get(storage_type_lower, 0.10)
        iops_cost = provisioned_iops * iops_rate

    # gp3 additional IOPS (above baseline 3000)
    if storage_type_lower == 'gp3' and provisioned_iops > 3000:
        additional_iops = provisioned_iops - 3000
        iops_cost = additional_iops * RDS_IOPS_PRICING['gp3']

    total_cost = storage_cost + iops_cost

    # Multi-AZ doubles storage cost
    if multi_az:
        storage_cost *= 2
        total_cost = storage_cost + iops_cost  # IOPS not doubled

    return {
        'storage_cost': round(storage_cost, 2),
        'iops_cost': round(iops_cost, 2),
        'total_cost': round(total_cost, 2),
        'storage_rate_per_gb': storage_rate,
        'provisioned_iops': provisioned_iops,
        'multi_az_storage_multiplier': 2 if multi_az else 1,
    }


def _estimate_backup_cost(
    total_backup_gb: int,
    allocated_storage_gb: int
) -> Dict[str, Any]:
    """
    Estimate backup storage cost accounting for free tier.

    Free tier: Backup storage up to 100% of provisioned DB storage is free.

    Args:
        total_backup_gb: Total backup storage in GB
        allocated_storage_gb: Provisioned database storage in GB

    Returns:
        Dict with free_allocation, billable_gb, and monthly_cost
    """
    free_allocation = allocated_storage_gb  # 100% of DB size is free
    billable_gb = max(0, total_backup_gb - free_allocation)
    monthly_cost = billable_gb * RDS_BACKUP_PRICING_PER_GB

    return {
        'total_backup_gb': total_backup_gb,
        'free_allocation_gb': free_allocation,
        'billable_gb': billable_gb,
        'monthly_cost': round(monthly_cost, 2),
        'rate_per_gb': RDS_BACKUP_PRICING_PER_GB,
    }


@tool
def analyze_rds_instance(
    db_instance_identifier: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Comprehensive RDS instance analysis including performance, cost, and configuration.

    Analyzes:
    - Instance configuration (class, engine, storage)
    - Performance metrics (CPU, connections, IOPS)
    - Cost estimation (instance + storage)
    - Security settings (encryption, public access)
    - Backup configuration
    - Optimization recommendations

    Args:
        db_instance_identifier: RDS instance identifier
        aws_client: Optional AWSClient instance

    Returns:
        Dict with instance details, metrics, costs, security, and recommendations

    Example:
        >>> result = analyze_rds_instance("my-database")
        >>> print(f"Monthly cost: ${result['cost']['total_monthly_cost']:.2f}")
        >>> print(f"CPU average: {result['performance']['cpu_average']:.1f}%")
    """
    if aws_client is None:
        aws_client = AWSClient()

    rds = aws_client.get_client('rds')
    cloudwatch = aws_client.get_client('cloudwatch')

    try:
        # Get instance details
        response = rds.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        db = response['DBInstances'][0]

        # Extract configuration
        config = {
            'identifier': db['DBInstanceIdentifier'],
            'engine': db['Engine'],
            'engine_version': db['EngineVersion'],
            'instance_class': db['DBInstanceClass'],
            'status': db['DBInstanceStatus'],
            'availability_zone': db.get('AvailabilityZone', 'N/A'),
            'multi_az': db.get('MultiAZ', False),
            'storage_type': db.get('StorageType', 'Unknown'),
            'allocated_storage_gb': db.get('AllocatedStorage', 0),
            'iops': db.get('Iops', 0),
            'license_model': db.get('LicenseModel', 'Unknown'),
            'created': db.get('InstanceCreateTime', 'Unknown')
        }

        # Get CloudWatch metrics (last 7 days)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        # CPU Utilization
        cpu_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_identifier}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average', 'Maximum']
        )

        cpu_datapoints = cpu_response.get('Datapoints', [])
        cpu_avg = sum(dp['Average'] for dp in cpu_datapoints) / len(cpu_datapoints) if cpu_datapoints else 0
        cpu_max = max((dp['Maximum'] for dp in cpu_datapoints), default=0)

        # Database Connections
        conn_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='DatabaseConnections',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_identifier}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average', 'Maximum']
        )

        conn_datapoints = conn_response.get('Datapoints', [])
        conn_avg = sum(dp['Average'] for dp in conn_datapoints) / len(conn_datapoints) if conn_datapoints else 0
        conn_max = max((dp['Maximum'] for dp in conn_datapoints), default=0)

        # Read/Write IOPS
        read_iops_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='ReadIOPS',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_identifier}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average']
        )

        read_iops_datapoints = read_iops_response.get('Datapoints', [])
        read_iops_avg = sum(dp['Average'] for dp in read_iops_datapoints) / len(read_iops_datapoints) if read_iops_datapoints else 0

        performance = {
            'cpu_average': round(cpu_avg, 2),
            'cpu_maximum': round(cpu_max, 2),
            'connections_average': round(conn_avg, 2),
            'connections_maximum': int(conn_max),
            'read_iops_average': round(read_iops_avg, 2),
            'lookback_days': 7
        }

        # Cost estimation using engine-aware pricing
        instance_cost_estimate = _estimate_instance_cost(
            instance_class=config['instance_class'],
            engine=config['engine'],
            license_model=config['license_model'],
            multi_az=config['multi_az']
        )

        storage_cost_estimate = _estimate_storage_cost(
            storage_type=config['storage_type'],
            allocated_storage_gb=config['allocated_storage_gb'],
            provisioned_iops=config['iops'],
            multi_az=config['multi_az']
        )

        total_monthly = instance_cost_estimate['monthly_cost'] + storage_cost_estimate['total_cost']

        cost = {
            'hourly_instance_cost': instance_cost_estimate['hourly_cost'],
            'monthly_instance_cost': instance_cost_estimate['monthly_cost'],
            'monthly_storage_cost': storage_cost_estimate['storage_cost'],
            'monthly_iops_cost': storage_cost_estimate['iops_cost'],
            'total_monthly_cost': round(total_monthly, 2),
            'annual_cost': round(total_monthly * 12, 2),
            'pricing_details': {
                'engine_pricing_key': instance_cost_estimate['engine_key'],
                'storage_rate_per_gb': storage_cost_estimate['storage_rate_per_gb'],
                'provisioned_iops': storage_cost_estimate['provisioned_iops'],
                'multi_az_instance_multiplier': instance_cost_estimate['multi_az_multiplier'],
                'multi_az_storage_multiplier': storage_cost_estimate['multi_az_storage_multiplier'],
            },
            'note': 'Estimate based on on-demand pricing (us-east-1). '
                    'Oracle/SQL Server License Included and io1/io2 IOPS can significantly increase costs. '
                    'Use AWS Pricing Calculator for accurate quotes.'
        }

        # Security analysis
        security = {
            'publicly_accessible': db.get('PubliclyAccessible', False),
            'encrypted': db.get('StorageEncrypted', False),
            'kms_key_id': db.get('KmsKeyId', None),
            'iam_database_authentication': db.get('IAMDatabaseAuthenticationEnabled', False),
            'deletion_protection': db.get('DeletionProtection', False),
            'auto_minor_version_upgrade': db.get('AutoMinorVersionUpgrade', False)
        }

        # Security issues
        security_issues = []
        if security['publicly_accessible']:
            security_issues.append({
                'severity': 'critical',
                'issue': 'Database is publicly accessible',
                'recommendation': 'Disable public access unless absolutely necessary'
            })
        if not security['encrypted']:
            security_issues.append({
                'severity': 'high',
                'issue': 'Storage encryption not enabled',
                'recommendation': 'Enable encryption at rest for compliance'
            })
        if not security['deletion_protection']:
            security_issues.append({
                'severity': 'medium',
                'issue': 'Deletion protection not enabled',
                'recommendation': 'Enable deletion protection for production databases'
            })

        # Backup configuration
        backup = {
            'backup_retention_days': db.get('BackupRetentionPeriod', 0),
            'preferred_backup_window': db.get('PreferredBackupWindow', 'N/A'),
            'latest_restorable_time': db.get('LatestRestorableTime', 'N/A'),
            'automated_backups': db.get('BackupRetentionPeriod', 0) > 0
        }

        # Optimization recommendations
        recommendations = []

        # CPU-based recommendations
        if cpu_avg < 20:
            recommendations.append({
                'type': 'rightsizing',
                'priority': 'high',
                'recommendation': f'CPU average is only {cpu_avg:.1f}% - consider downsizing instance class',
                'potential_savings': f'${monthly_instance_cost * 0.5:.2f}/month (estimate)'
            })
        elif cpu_avg > 80:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'recommendation': f'CPU average is {cpu_avg:.1f}% - consider upsizing for better performance',
                'impact': 'Performance bottleneck likely'
            })

        # Storage type recommendations
        # Note: RDS gp2 and gp3 have the same storage price ($0.115/GB), but gp3 offers
        # better baseline performance (3000 IOPS vs scaled IOPS for gp2)
        if config['storage_type'] == 'gp2':
            recommendations.append({
                'type': 'performance',
                'priority': 'low',
                'recommendation': 'Consider migrating from gp2 to gp3 for better baseline performance',
                'details': 'gp3 provides 3000 IOPS baseline vs gp2 scaled IOPS. Same storage cost ($0.115/GB).'
            })

        # Multi-AZ recommendation
        if not config['multi_az'] and config['status'] == 'available':
            recommendations.append({
                'type': 'reliability',
                'priority': 'medium',
                'recommendation': 'Enable Multi-AZ for production workloads',
                'cost_impact': f'+${monthly_instance_cost:.2f}/month'
            })

        # Backup recommendation
        if backup['backup_retention_days'] < 7:
            recommendations.append({
                'type': 'compliance',
                'priority': 'high',
                'recommendation': f'Backup retention is only {backup["backup_retention_days"]} days - increase to 7+ days',
                'impact': 'Compliance and disaster recovery risk'
            })

        # Add security recommendations
        recommendations.extend([
            {
                'type': 'security',
                'priority': item['severity'],
                'recommendation': item['recommendation'],
                'issue': item['issue']
            }
            for item in security_issues
        ])

        return {
            'instance_identifier': db_instance_identifier,
            'configuration': config,
            'performance': performance,
            'cost': cost,
            'security': security,
            'security_issues': security_issues,
            'backup': backup,
            'recommendations': recommendations,
            'summary': {
                'status': config['status'],
                'monthly_cost': cost['total_monthly_cost'],
                'cpu_utilization': performance['cpu_average'],
                'total_recommendations': len(recommendations),
                'security_issues': len(security_issues)
            }
        }

    except rds.exceptions.DBInstanceNotFoundFault:
        return {
            'error': 'Database instance not found',
            'instance_identifier': db_instance_identifier,
            'exists': False
        }
    except Exception as e:
        return {
            'error': f'Failed to analyze RDS instance: {str(e)}',
            'instance_identifier': db_instance_identifier
        }


@tool
def find_idle_databases(
    cpu_threshold: float = 10.0,
    lookback_days: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Find underutilized RDS instances that are wasting money.

    Identifies databases with low CPU utilization that could be:
    - Downsized to smaller instance class
    - Stopped if not in use
    - Deleted if truly unused

    Args:
        cpu_threshold: CPU percentage threshold (default 10%)
        lookback_days: Days to analyze (default 7)
        aws_client: Optional AWSClient instance

    Returns:
        Dict with idle databases, costs, and savings recommendations

    Example:
        >>> result = find_idle_databases(cpu_threshold=15.0)
        >>> print(f"Found {result['summary']['total_idle_databases']} idle databases")
        >>> print(f"Potential savings: ${result['summary']['potential_monthly_savings']:.2f}/month")
    """
    if aws_client is None:
        aws_client = AWSClient()

    rds = aws_client.get_client('rds')
    cloudwatch = aws_client.get_client('cloudwatch')

    try:
        # Get all RDS instances
        response = rds.describe_db_instances()
        instances = response['DBInstances']

        idle_databases = []
        total_potential_savings = 0.0

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=lookback_days)

        for db in instances:
            db_id = db['DBInstanceIdentifier']
            instance_class = db['DBInstanceClass']
            status = db['DBInstanceStatus']

            # Skip stopped instances
            if status != 'available':
                continue

            # Get CPU metrics
            cpu_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average', 'Maximum']
            )

            datapoints = cpu_response.get('Datapoints', [])

            if not datapoints:
                # No metrics - possibly very idle
                idle_databases.append({
                    'instance_identifier': db_id,
                    'instance_class': instance_class,
                    'engine': db['Engine'],
                    'cpu_average': 0.0,
                    'cpu_maximum': 0.0,
                    'status': 'no_metrics',
                    'risk': 'high',
                    'recommendation': 'No CPU metrics found - database may be completely unused',
                    'action': 'Consider stopping or deleting if not needed'
                })
                continue

            cpu_avg = sum(dp['Average'] for dp in datapoints) / len(datapoints)
            cpu_max = max(dp['Maximum'] for dp in datapoints)

            if cpu_avg < cpu_threshold:
                # Calculate costs using engine-aware pricing
                engine = db['Engine']
                license_model = db.get('LicenseModel', None)
                multi_az = db.get('MultiAZ', False)
                storage_type = db.get('StorageType', 'gp2')
                allocated_storage = db.get('AllocatedStorage', 0)
                provisioned_iops = db.get('Iops', 0)

                instance_cost = _estimate_instance_cost(
                    instance_class=instance_class,
                    engine=engine,
                    license_model=license_model,
                    multi_az=multi_az
                )

                storage_cost = _estimate_storage_cost(
                    storage_type=storage_type,
                    allocated_storage_gb=allocated_storage,
                    provisioned_iops=provisioned_iops,
                    multi_az=multi_az
                )

                monthly_cost = instance_cost['monthly_cost'] + storage_cost['total_cost']

                # Estimate savings from downsizing (50% of instance cost if very idle)
                if cpu_avg < 5:
                    potential_savings = instance_cost['monthly_cost'] * 0.5
                    recommendation = 'Downsize to smaller instance class (50% instance savings)'
                else:
                    potential_savings = instance_cost['monthly_cost'] * 0.3
                    recommendation = 'Consider downsizing instance class (30% instance savings)'

                total_potential_savings += potential_savings

                idle_databases.append({
                    'instance_identifier': db_id,
                    'instance_class': instance_class,
                    'engine': engine,
                    'license_model': license_model,
                    'cpu_average': round(cpu_avg, 2),
                    'cpu_maximum': round(cpu_max, 2),
                    'monthly_instance_cost': instance_cost['monthly_cost'],
                    'monthly_storage_cost': storage_cost['total_cost'],
                    'monthly_total_cost': round(monthly_cost, 2),
                    'potential_monthly_savings': round(potential_savings, 2),
                    'potential_annual_savings': round(potential_savings * 12, 2),
                    'recommendation': recommendation,
                    'risk': 'low' if cpu_avg > 5 else 'medium',
                    'pricing_note': instance_cost['engine_key']
                })

        # Sort by potential savings
        idle_databases.sort(key=lambda x: x.get('potential_monthly_savings', 0), reverse=True)

        return {
            'idle_databases': idle_databases,
            'summary': {
                'total_idle_databases': len(idle_databases),
                'cpu_threshold': cpu_threshold,
                'lookback_days': lookback_days,
                'potential_monthly_savings': round(total_potential_savings, 2),
                'potential_annual_savings': round(total_potential_savings * 12, 2)
            },
            'recommendations': [
                'Review idle databases and downsize or stop unused instances',
                'Consider Reserved Instances for databases that must remain running',
                'Enable Aurora Serverless for variable workloads'
            ] if idle_databases else ['No idle databases found - good resource utilization!']
        }

    except Exception as e:
        return {
            'error': f'Failed to find idle databases: {str(e)}',
            'idle_databases': []
        }


@tool
def analyze_rds_backups(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze RDS backup configuration and costs across all databases.

    Checks:
    - Automated backup status and retention
    - Snapshot inventory and costs
    - Compliance with backup best practices
    - Manual snapshot cleanup opportunities

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict with backup status, costs, and compliance recommendations

    Example:
        >>> result = analyze_rds_backups()
        >>> print(f"Backup costs: ${result['costs']['total_monthly_cost']:.2f}/month")
        >>> print(f"Compliance score: {result['compliance']['score']}/100")
    """
    if aws_client is None:
        aws_client = AWSClient()

    rds = aws_client.get_client('rds')

    try:
        # Get all DB instances
        instances_response = rds.describe_db_instances()
        instances = instances_response['DBInstances']

        # Get all manual snapshots
        snapshots_response = rds.describe_db_snapshots(SnapshotType='manual')
        manual_snapshots = snapshots_response['DBSnapshots']

        # Analyze instances
        instance_backup_status = []
        compliant_count = 0

        for db in instances:
            db_id = db['DBInstanceIdentifier']
            retention = db.get('BackupRetentionPeriod', 0)

            is_compliant = retention >= 7  # 7 days minimum
            if is_compliant:
                compliant_count += 1

            instance_backup_status.append({
                'instance_identifier': db_id,
                'engine': db['Engine'],
                'backup_retention_days': retention,
                'automated_backups_enabled': retention > 0,
                'preferred_backup_window': db.get('PreferredBackupWindow', 'N/A'),
                'latest_restorable_time': str(db.get('LatestRestorableTime', 'N/A')),
                'compliance': 'compliant' if is_compliant else 'non_compliant',
                'issue': None if is_compliant else f'Retention only {retention} days (minimum 7 recommended)'
            })

        # Calculate total provisioned storage across all instances (for free tier)
        total_provisioned_storage = sum(
            inst.get('AllocatedStorage', 0) for inst in instances
        )

        # Analyze manual snapshots
        snapshot_analysis = []
        total_snapshot_size = 0
        old_snapshots = []

        now = datetime.now(manual_snapshots[0]['SnapshotCreateTime'].tzinfo) if manual_snapshots else datetime.utcnow()

        for snapshot in manual_snapshots:
            snapshot_id = snapshot['DBSnapshotIdentifier']
            size_gb = snapshot.get('AllocatedStorage', 0)
            created = snapshot['SnapshotCreateTime']
            age_days = (now - created).days

            total_snapshot_size += size_gb

            snapshot_info = {
                'snapshot_id': snapshot_id,
                'db_instance': snapshot.get('DBInstanceIdentifier', 'N/A'),
                'size_gb': size_gb,
                'created': str(created),
                'age_days': age_days,
                'status': snapshot['Status']
            }

            snapshot_analysis.append(snapshot_info)

            # Flag old snapshots (>90 days)
            if age_days > 90:
                old_snapshots.append({
                    **snapshot_info,
                    'recommendation': 'Consider deleting if no longer needed'
                })

        # Cost estimation using free tier calculation
        # Free tier: Backup storage up to 100% of total provisioned DB storage is free
        backup_cost = _estimate_backup_cost(
            total_backup_gb=total_snapshot_size,
            allocated_storage_gb=total_provisioned_storage
        )

        costs = {
            'total_snapshot_size_gb': total_snapshot_size,
            'total_provisioned_storage_gb': total_provisioned_storage,
            'free_backup_allocation_gb': backup_cost['free_allocation_gb'],
            'billable_backup_gb': backup_cost['billable_gb'],
            'monthly_snapshot_cost': backup_cost['monthly_cost'],
            'annual_snapshot_cost': round(backup_cost['monthly_cost'] * 12, 2),
            'cost_per_gb_month': RDS_BACKUP_PRICING_PER_GB,
            'note': 'Backup storage up to 100% of provisioned DB storage is FREE. '
                    'Only storage exceeding this amount is charged at $0.095/GB-month. '
                    'Automated backups within retention period use the same free allocation.'
        }

        # Compliance scoring
        total_instances = len(instances)
        compliance_score = int((compliant_count / total_instances * 100)) if total_instances > 0 else 100

        compliance = {
            'score': compliance_score,
            'total_instances': total_instances,
            'compliant_instances': compliant_count,
            'non_compliant_instances': total_instances - compliant_count,
            'issues': [inst for inst in instance_backup_status if inst['compliance'] == 'non_compliant']
        }

        # Recommendations
        recommendations = []

        if compliance_score < 100:
            recommendations.append({
                'priority': 'high',
                'category': 'compliance',
                'recommendation': f'{total_instances - compliant_count} databases have insufficient backup retention',
                'action': 'Increase backup retention to 7+ days for production databases'
            })

        if len(old_snapshots) > 0:
            potential_savings = len(old_snapshots) * 50 * snapshot_cost_per_gb  # Assume 50GB average
            recommendations.append({
                'priority': 'medium',
                'category': 'cost',
                'recommendation': f'{len(old_snapshots)} manual snapshots are >90 days old',
                'action': 'Review and delete unnecessary old snapshots',
                'potential_savings': f'${potential_savings:.2f}/month (estimate)'
            })

        if total_instances > 0 and compliant_count == total_instances:
            recommendations.append({
                'priority': 'info',
                'category': 'success',
                'recommendation': 'All databases have compliant backup configuration',
                'action': 'Continue monitoring backup status'
            })

        return {
            'instance_backup_status': instance_backup_status,
            'manual_snapshots': snapshot_analysis,
            'old_snapshots': old_snapshots,
            'costs': costs,
            'compliance': compliance,
            'recommendations': recommendations,
            'summary': {
                'total_databases': total_instances,
                'compliance_score': compliance_score,
                'total_manual_snapshots': len(manual_snapshots),
                'monthly_snapshot_cost': costs['monthly_snapshot_cost'],
                'old_snapshots_count': len(old_snapshots)
            }
        }

    except Exception as e:
        return {
            'error': f'Failed to analyze RDS backups: {str(e)}',
            'instance_backup_status': [],
            'manual_snapshots': []
        }


@tool
def get_rds_recommendations(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get RDS optimization recommendations from AWS Trusted Advisor and cost analysis.

    Provides recommendations for:
    - Instance rightsizing based on utilization
    - Reserved Instance purchase opportunities
    - Storage optimization (gp2 to gp3 migration)
    - Multi-AZ and backup improvements

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict with categorized recommendations and potential savings

    Example:
        >>> result = get_rds_recommendations()
        >>> print(f"Total recommendations: {result['summary']['total_recommendations']}")
        >>> print(f"Potential savings: ${result['summary']['total_potential_savings']:.2f}/month")
    """
    if aws_client is None:
        aws_client = AWSClient()

    rds = aws_client.get_client('rds')
    cloudwatch = aws_client.get_client('cloudwatch')

    try:
        # Get all DB instances
        response = rds.describe_db_instances()
        instances = response['DBInstances']

        recommendations = []
        total_potential_savings = 0.0

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        for db in instances:
            db_id = db['DBInstanceIdentifier']
            instance_class = db['DBInstanceClass']
            storage_type = db.get('StorageType', 'gp2')
            allocated_storage = db.get('AllocatedStorage', 0)
            multi_az = db.get('MultiAZ', False)
            engine = db['Engine']

            # Get CPU utilization
            cpu_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )

            datapoints = cpu_response.get('Datapoints', [])
            cpu_avg = sum(dp['Average'] for dp in datapoints) / len(datapoints) if datapoints else 50

            # Get license model for accurate pricing
            license_model = db.get('LicenseModel', None)
            provisioned_iops = db.get('Iops', 0)

            # Calculate current costs
            current_instance_cost = _estimate_instance_cost(
                instance_class=instance_class,
                engine=engine,
                license_model=license_model,
                multi_az=multi_az
            )

            # Rightsizing recommendations
            if cpu_avg < 20:
                # Define downgrade paths (current -> recommended)
                downgrade_paths = {
                    'db.t3.medium': 'db.t3.small',
                    'db.t3.large': 'db.t3.medium',
                    'db.m5.large': 'db.t3.large',
                    'db.m5.xlarge': 'db.m5.large',
                    'db.m5.2xlarge': 'db.m5.xlarge',
                    'db.r5.large': 'db.m5.large',
                    'db.r5.xlarge': 'db.r5.large',
                    'db.r5.2xlarge': 'db.r5.xlarge',
                }

                if instance_class in downgrade_paths:
                    recommended_class = downgrade_paths[instance_class]

                    recommended_cost = _estimate_instance_cost(
                        instance_class=recommended_class,
                        engine=engine,
                        license_model=license_model,
                        multi_az=multi_az
                    )

                    monthly_savings = current_instance_cost['monthly_cost'] - recommended_cost['monthly_cost']
                    total_potential_savings += monthly_savings

                    recommendations.append({
                        'db_instance': db_id,
                        'type': 'rightsizing',
                        'priority': 'high',
                        'current_class': instance_class,
                        'recommended_class': recommended_class,
                        'engine': engine,
                        'cpu_utilization': round(cpu_avg, 2),
                        'current_monthly_cost': current_instance_cost['monthly_cost'],
                        'recommended_monthly_cost': recommended_cost['monthly_cost'],
                        'monthly_savings': round(monthly_savings, 2),
                        'annual_savings': round(monthly_savings * 12, 2),
                        'recommendation': f'Downsize from {instance_class} to {recommended_class}',
                        'risk': 'low',
                        'effort': 'medium',
                        'pricing_note': f'Based on {current_instance_cost["engine_key"]} pricing'
                    })

            # Storage optimization (gp2 to gp3)
            # Note: RDS gp2 and gp3 have the same price, but gp3 has better baseline performance
            if storage_type == 'gp2':
                recommendations.append({
                    'db_instance': db_id,
                    'type': 'performance',
                    'priority': 'low',
                    'current_storage': f'{storage_type} ({allocated_storage} GB)',
                    'recommended_storage': 'gp3',
                    'monthly_savings': 0,  # Same price for RDS
                    'recommendation': f'Consider migrating {allocated_storage} GB from gp2 to gp3',
                    'details': 'gp3 provides 3000 IOPS baseline. Same storage cost ($0.115/GB).',
                    'risk': 'low',
                    'effort': 'low'
                })

            # Multi-AZ recommendation for production
            if not multi_az and 'prod' in db_id.lower():
                cost_increase = current_instance_cost['monthly_cost']  # Multi-AZ doubles instance cost
                recommendations.append({
                    'db_instance': db_id,
                    'type': 'reliability',
                    'priority': 'high',
                    'current_config': 'Single-AZ',
                    'recommended_config': 'Multi-AZ',
                    'cost_increase': round(cost_increase, 2),
                    'recommendation': f'Enable Multi-AZ for production database {db_id}',
                    'risk': 'high_without',
                    'effort': 'low',
                    'benefit': 'Automatic failover and high availability'
                })

            # io1/io2 IOPS cost warning
            if storage_type in ('io1', 'io2') and provisioned_iops > 0:
                iops_cost = provisioned_iops * RDS_IOPS_PRICING.get(storage_type, 0.10)
                if iops_cost > 100:  # Flag high IOPS costs
                    recommendations.append({
                        'db_instance': db_id,
                        'type': 'cost_awareness',
                        'priority': 'info',
                        'current_iops': provisioned_iops,
                        'monthly_iops_cost': round(iops_cost, 2),
                        'recommendation': f'High IOPS cost: ${iops_cost:.2f}/month for {provisioned_iops} IOPS',
                        'details': 'Consider if this IOPS level is necessary. gp3 provides 3000 IOPS baseline for free.',
                        'risk': 'none',
                        'effort': 'medium'
                    })

        # Sort recommendations by potential savings
        recommendations.sort(key=lambda x: x.get('monthly_savings', 0), reverse=True)

        # Categorize recommendations
        by_type = {}
        for rec in recommendations:
            rec_type = rec['type']
            if rec_type not in by_type:
                by_type[rec_type] = []
            by_type[rec_type].append(rec)

        return {
            'recommendations': recommendations,
            'by_type': by_type,
            'summary': {
                'total_recommendations': len(recommendations),
                'total_potential_savings': round(total_potential_savings, 2),
                'total_annual_savings': round(total_potential_savings * 12, 2),
                'by_priority': {
                    'high': len([r for r in recommendations if r['priority'] == 'high']),
                    'medium': len([r for r in recommendations if r['priority'] == 'medium']),
                    'low': len([r for r in recommendations if r['priority'] == 'low'])
                }
            },
            'top_opportunities': recommendations[:5] if recommendations else []
        }

    except Exception as e:
        return {
            'error': f'Failed to get RDS recommendations: {str(e)}',
            'recommendations': []
        }


@tool
def find_rds_security_issues(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Scan all RDS instances for security misconfigurations and compliance issues.

    Checks for:
    - Publicly accessible databases
    - Unencrypted storage
    - Missing deletion protection
    - Weak backup retention
    - Missing security patches
    - IAM authentication disabled

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict with security findings by severity and remediation steps

    Example:
        >>> result = find_rds_security_issues()
        >>> print(f"Critical issues: {result['summary']['critical']}")
        >>> print(f"Security score: {result['summary']['security_score']}/100")
    """
    if aws_client is None:
        aws_client = AWSClient()

    rds = aws_client.get_client('rds')

    try:
        # Get all DB instances
        response = rds.describe_db_instances()
        instances = response['DBInstances']

        findings = []
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        for db in instances:
            db_id = db['DBInstanceIdentifier']
            engine = db['Engine']

            # Check 1: Public accessibility
            if db.get('PubliclyAccessible', False):
                critical_count += 1
                findings.append({
                    'db_instance': db_id,
                    'severity': 'critical',
                    'category': 'network',
                    'finding': 'Database is publicly accessible',
                    'risk': 'Database exposed to internet - high breach risk',
                    'remediation': 'Set PubliclyAccessible to false',
                    'command': f"aws rds modify-db-instance --db-instance-identifier {db_id} --no-publicly-accessible"
                })

            # Check 2: Encryption
            if not db.get('StorageEncrypted', False):
                high_count += 1
                findings.append({
                    'db_instance': db_id,
                    'severity': 'high',
                    'category': 'encryption',
                    'finding': 'Storage encryption not enabled',
                    'risk': 'Data at rest not encrypted - compliance violation',
                    'remediation': 'Create encrypted snapshot and restore to new encrypted instance',
                    'note': 'Cannot enable encryption on existing instance - must restore from snapshot'
                })

            # Check 3: Deletion protection
            if not db.get('DeletionProtection', False):
                medium_count += 1
                findings.append({
                    'db_instance': db_id,
                    'severity': 'medium',
                    'category': 'data_protection',
                    'finding': 'Deletion protection not enabled',
                    'risk': 'Database can be accidentally deleted',
                    'remediation': 'Enable deletion protection',
                    'command': f"aws rds modify-db-instance --db-instance-identifier {db_id} --deletion-protection"
                })

            # Check 4: Backup retention
            retention = db.get('BackupRetentionPeriod', 0)
            if retention < 7:
                high_count += 1
                findings.append({
                    'db_instance': db_id,
                    'severity': 'high',
                    'category': 'backup',
                    'finding': f'Backup retention only {retention} days',
                    'risk': 'Insufficient backup retention for disaster recovery',
                    'remediation': 'Increase backup retention to 7+ days',
                    'command': f"aws rds modify-db-instance --db-instance-identifier {db_id} --backup-retention-period 7"
                })

            # Check 5: IAM database authentication
            if not db.get('IAMDatabaseAuthenticationEnabled', False):
                low_count += 1
                findings.append({
                    'db_instance': db_id,
                    'severity': 'low',
                    'category': 'authentication',
                    'finding': 'IAM database authentication not enabled',
                    'risk': 'Using database passwords instead of IAM',
                    'remediation': 'Enable IAM database authentication for better security',
                    'command': f"aws rds modify-db-instance --db-instance-identifier {db_id} --enable-iam-database-authentication"
                })

            # Check 6: Auto minor version upgrade
            if not db.get('AutoMinorVersionUpgrade', False):
                low_count += 1
                findings.append({
                    'db_instance': db_id,
                    'severity': 'low',
                    'category': 'patching',
                    'finding': 'Auto minor version upgrade disabled',
                    'risk': 'Missing security patches',
                    'remediation': 'Enable auto minor version upgrades',
                    'command': f"aws rds modify-db-instance --db-instance-identifier {db_id} --auto-minor-version-upgrade"
                })

            # Check 7: Enhanced monitoring
            if db.get('EnhancedMonitoringResourceArn') is None:
                low_count += 1
                findings.append({
                    'db_instance': db_id,
                    'severity': 'low',
                    'category': 'monitoring',
                    'finding': 'Enhanced monitoring not enabled',
                    'risk': 'Limited visibility into database performance',
                    'remediation': 'Enable enhanced monitoring for better insights',
                    'note': 'Additional cost: ~$1.40/month per instance'
                })

        # Calculate security score
        total_issues = critical_count + high_count + medium_count + low_count
        max_possible_issues = len(instances) * 7  # 7 checks per instance
        security_score = 100 - int((total_issues / max_possible_issues * 100)) if max_possible_issues > 0 else 100

        # Group findings by severity
        by_severity = {
            'critical': [f for f in findings if f['severity'] == 'critical'],
            'high': [f for f in findings if f['severity'] == 'high'],
            'medium': [f for f in findings if f['severity'] == 'medium'],
            'low': [f for f in findings if f['severity'] == 'low']
        }

        return {
            'findings': findings,
            'by_severity': by_severity,
            'summary': {
                'total_instances_scanned': len(instances),
                'total_findings': total_issues,
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
                'security_score': security_score
            },
            'top_priorities': by_severity['critical'] + by_severity['high'],
            'remediation_summary': [
                f"{critical_count} critical issues require immediate attention",
                f"{high_count} high severity issues should be addressed soon",
                f"Security score: {security_score}/100"
            ] if total_issues > 0 else ["No security issues found - excellent security posture!"]
        }

    except Exception as e:
        return {
            'error': f'Failed to scan RDS security: {str(e)}',
            'findings': []
        }
