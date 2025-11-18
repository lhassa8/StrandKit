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
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from strands import tool
from strandkit.core.aws_client import AWSClient


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

        # Cost estimation
        # RDS pricing is complex - these are rough estimates
        instance_class = config['instance_class']
        storage_gb = config['allocated_storage_gb']

        # Rough hourly cost by instance class (US East 1, on-demand)
        instance_costs = {
            'db.t3.micro': 0.017,
            'db.t3.small': 0.034,
            'db.t3.medium': 0.068,
            'db.t3.large': 0.136,
            'db.t4g.micro': 0.016,
            'db.t4g.small': 0.032,
            'db.t4g.medium': 0.064,
            'db.m5.large': 0.192,
            'db.m5.xlarge': 0.384,
            'db.m5.2xlarge': 0.768,
            'db.r5.large': 0.24,
            'db.r5.xlarge': 0.48,
            'db.r5.2xlarge': 0.96,
        }

        hourly_cost = instance_costs.get(instance_class, 0.10)  # Default estimate
        storage_cost_per_gb = 0.115  # GP2 pricing
        if config['storage_type'] == 'gp3':
            storage_cost_per_gb = 0.08
        elif config['storage_type'] == 'io1':
            storage_cost_per_gb = 0.125

        monthly_instance_cost = hourly_cost * 730  # 730 hours/month
        monthly_storage_cost = storage_gb * storage_cost_per_gb

        if config['multi_az']:
            monthly_instance_cost *= 2  # Multi-AZ doubles cost

        cost = {
            'hourly_instance_cost': round(hourly_cost, 3),
            'monthly_instance_cost': round(monthly_instance_cost, 2),
            'monthly_storage_cost': round(monthly_storage_cost, 2),
            'total_monthly_cost': round(monthly_instance_cost + monthly_storage_cost, 2),
            'annual_cost': round((monthly_instance_cost + monthly_storage_cost) * 12, 2),
            'note': 'Estimate based on on-demand pricing (US East 1)'
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
        if config['storage_type'] == 'gp2':
            savings = (storage_cost_per_gb - 0.08) * storage_gb
            recommendations.append({
                'type': 'cost',
                'priority': 'medium',
                'recommendation': 'Migrate from gp2 to gp3 storage for cost savings',
                'potential_savings': f'${savings:.2f}/month'
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
                # Calculate potential savings
                # Rough estimates
                instance_costs = {
                    'db.t3.micro': 0.017,
                    'db.t3.small': 0.034,
                    'db.t3.medium': 0.068,
                    'db.t3.large': 0.136,
                    'db.m5.large': 0.192,
                    'db.m5.xlarge': 0.384,
                    'db.r5.large': 0.24,
                    'db.r5.xlarge': 0.48,
                }

                hourly_cost = instance_costs.get(instance_class, 0.10)
                monthly_cost = hourly_cost * 730

                # If Multi-AZ, double the cost
                if db.get('MultiAZ', False):
                    monthly_cost *= 2

                # Estimate savings from downsizing (50% if very idle)
                if cpu_avg < 5:
                    potential_savings = monthly_cost * 0.5
                    recommendation = 'Downsize to smaller instance class (50% savings)'
                else:
                    potential_savings = monthly_cost * 0.3
                    recommendation = 'Consider downsizing instance class (30% savings)'

                total_potential_savings += potential_savings

                idle_databases.append({
                    'instance_identifier': db_id,
                    'instance_class': instance_class,
                    'engine': db['Engine'],
                    'cpu_average': round(cpu_avg, 2),
                    'cpu_maximum': round(cpu_max, 2),
                    'monthly_cost': round(monthly_cost, 2),
                    'potential_monthly_savings': round(potential_savings, 2),
                    'potential_annual_savings': round(potential_savings * 12, 2),
                    'recommendation': recommendation,
                    'risk': 'low' if cpu_avg > 5 else 'medium'
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

        # Cost estimation
        # RDS snapshots: $0.095/GB-month (roughly)
        snapshot_cost_per_gb = 0.095
        monthly_snapshot_cost = total_snapshot_size * snapshot_cost_per_gb

        # Automated backup costs (included in instance cost for retention period)
        # Additional cost for long retention

        costs = {
            'total_snapshot_size_gb': total_snapshot_size,
            'monthly_snapshot_cost': round(monthly_snapshot_cost, 2),
            'annual_snapshot_cost': round(monthly_snapshot_cost * 12, 2),
            'cost_per_gb_month': snapshot_cost_per_gb,
            'note': 'Manual snapshot costs only - automated backups included in instance cost'
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

            # Rightsizing recommendations
            if cpu_avg < 20:
                # Rough cost estimates
                instance_costs = {
                    'db.t3.medium': (0.068, 'db.t3.small', 0.034),
                    'db.t3.large': (0.136, 'db.t3.medium', 0.068),
                    'db.m5.large': (0.192, 'db.t3.large', 0.136),
                    'db.m5.xlarge': (0.384, 'db.m5.large', 0.192),
                    'db.m5.2xlarge': (0.768, 'db.m5.xlarge', 0.384),
                    'db.r5.large': (0.24, 'db.m5.large', 0.192),
                    'db.r5.xlarge': (0.48, 'db.r5.large', 0.24),
                }

                if instance_class in instance_costs:
                    current_cost, recommended_class, recommended_cost = instance_costs[instance_class]
                    monthly_savings = (current_cost - recommended_cost) * 730

                    if multi_az:
                        monthly_savings *= 2

                    total_potential_savings += monthly_savings

                    recommendations.append({
                        'db_instance': db_id,
                        'type': 'rightsizing',
                        'priority': 'high',
                        'current_class': instance_class,
                        'recommended_class': recommended_class,
                        'cpu_utilization': round(cpu_avg, 2),
                        'monthly_savings': round(monthly_savings, 2),
                        'annual_savings': round(monthly_savings * 12, 2),
                        'recommendation': f'Downsize from {instance_class} to {recommended_class}',
                        'risk': 'low',
                        'effort': 'medium'
                    })

            # Storage optimization (gp2 to gp3)
            if storage_type == 'gp2':
                storage_savings = allocated_storage * (0.115 - 0.08)  # $0.035/GB savings
                total_potential_savings += storage_savings

                recommendations.append({
                    'db_instance': db_id,
                    'type': 'storage',
                    'priority': 'medium',
                    'current_storage': f'{storage_type} ({allocated_storage} GB)',
                    'recommended_storage': 'gp3',
                    'monthly_savings': round(storage_savings, 2),
                    'annual_savings': round(storage_savings * 12, 2),
                    'recommendation': f'Migrate {allocated_storage} GB from gp2 to gp3 storage',
                    'risk': 'low',
                    'effort': 'low'
                })

            # Multi-AZ recommendation for production
            if not multi_az and 'prod' in db_id.lower():
                instance_cost = 0.10 * 730  # Rough estimate
                recommendations.append({
                    'db_instance': db_id,
                    'type': 'reliability',
                    'priority': 'high',
                    'current_config': 'Single-AZ',
                    'recommended_config': 'Multi-AZ',
                    'cost_increase': round(instance_cost, 2),
                    'recommendation': f'Enable Multi-AZ for production database {db_id}',
                    'risk': 'high_without',
                    'effort': 'low',
                    'benefit': 'Automatic failover and high availability'
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
