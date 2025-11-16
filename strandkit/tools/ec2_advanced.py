"""
Advanced EC2 tools for performance analysis, auto-scaling, load balancing, and cost optimization.

This module provides advanced EC2 analysis capabilities:
- Performance monitoring and metrics analysis
- Auto Scaling Group configuration and optimization
- Load balancer health and cost analysis
- Spot instance opportunity identification

All functions return structured JSON with consistent schema.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from strandkit.core.aws_client import AWSClient


def analyze_ec2_performance(
    instance_id: str,
    lookback_days: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Deep dive into EC2 instance performance metrics using CloudWatch.

    Analyzes CPU, network, disk I/O, and status checks over a specified period
    to identify performance issues, trends, and optimization opportunities.

    Args:
        instance_id: EC2 instance ID to analyze
        lookback_days: Number of days to analyze (default: 7)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        - instance_id: Instance identifier
        - instance_type: Instance type and specifications
        - analysis_period: Time range analyzed
        - cpu_metrics: CPU utilization statistics and trends
        - network_metrics: Network in/out statistics
        - disk_metrics: Disk read/write operations and bytes
        - status_checks: System and instance status check failures
        - performance_issues: List of detected issues
        - recommendations: Performance optimization suggestions
        - summary: Overall health score and key metrics

    Example:
        >>> perf = analyze_ec2_performance("i-1234567890abcdef0", lookback_days=7)
        >>> print(f"Health Score: {perf['summary']['health_score']}/100")
        >>> print(f"Avg CPU: {perf['cpu_metrics']['average']:.1f}%")
        >>> for issue in perf['performance_issues']:
        ...     print(f"⚠️ {issue}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    ec2 = aws_client.get_client('ec2')
    cloudwatch = aws_client.get_client('cloudwatch')

    try:
        # Get instance details
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if not response['Reservations']:
            return {'error': f'Instance {instance_id} not found'}

        instance = response['Reservations'][0]['Instances'][0]
        instance_type = instance['InstanceType']
        instance_state = instance['State']['Name']

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=lookback_days)

        # Helper function to get metric statistics
        def get_metric_stats(metric_name: str, stat: str = 'Average', unit: Optional[str] = None):
            params = {
                'Namespace': 'AWS/EC2',
                'MetricName': metric_name,
                'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}],
                'StartTime': start_time,
                'EndTime': end_time,
                'Period': 3600,  # 1 hour intervals
                'Statistics': [stat]
            }
            if unit:
                params['Unit'] = unit

            result = cloudwatch.get_metric_statistics(**params)
            datapoints = sorted(result['Datapoints'], key=lambda x: x['Timestamp'])
            return datapoints

        # Get CPU metrics
        cpu_datapoints = get_metric_stats('CPUUtilization', 'Average', 'Percent')
        cpu_values = [dp[list(dp.keys())[1]] for dp in cpu_datapoints if len(dp.keys()) > 1]

        cpu_metrics = {
            'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            'maximum': max(cpu_values) if cpu_values else 0,
            'minimum': min(cpu_values) if cpu_values else 0,
            'datapoints': len(cpu_values),
            'trend': 'stable'
        }

        # Calculate trend
        if len(cpu_values) >= 2:
            first_half = cpu_values[:len(cpu_values)//2]
            second_half = cpu_values[len(cpu_values)//2:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            if second_avg > first_avg * 1.2:
                cpu_metrics['trend'] = 'increasing'
            elif second_avg < first_avg * 0.8:
                cpu_metrics['trend'] = 'decreasing'

        # Get Network metrics
        network_in = get_metric_stats('NetworkIn', 'Sum', 'Bytes')
        network_out = get_metric_stats('NetworkOut', 'Sum', 'Bytes')

        network_in_values = [dp[list(dp.keys())[1]] for dp in network_in if len(dp.keys()) > 1]
        network_out_values = [dp[list(dp.keys())[1]] for dp in network_out if len(dp.keys()) > 1]

        network_metrics = {
            'network_in_avg_mbps': (sum(network_in_values) / len(network_in_values) / 1024 / 1024 / 3600 * 8) if network_in_values else 0,
            'network_out_avg_mbps': (sum(network_out_values) / len(network_out_values) / 1024 / 1024 / 3600 * 8) if network_out_values else 0,
            'total_network_in_gb': sum(network_in_values) / 1024 / 1024 / 1024 if network_in_values else 0,
            'total_network_out_gb': sum(network_out_values) / 1024 / 1024 / 1024 if network_out_values else 0
        }

        # Get Disk metrics (EBS-backed instances)
        disk_read_ops = get_metric_stats('DiskReadOps', 'Sum')
        disk_write_ops = get_metric_stats('DiskWriteOps', 'Sum')
        disk_read_bytes = get_metric_stats('DiskReadBytes', 'Sum', 'Bytes')
        disk_write_bytes = get_metric_stats('DiskWriteBytes', 'Sum', 'Bytes')

        disk_read_ops_values = [dp[list(dp.keys())[1]] for dp in disk_read_ops if len(dp.keys()) > 1]
        disk_write_ops_values = [dp[list(dp.keys())[1]] for dp in disk_write_ops if len(dp.keys()) > 1]
        disk_read_bytes_values = [dp[list(dp.keys())[1]] for dp in disk_read_bytes if len(dp.keys()) > 1]
        disk_write_bytes_values = [dp[list(dp.keys())[1]] for dp in disk_write_bytes if len(dp.keys()) > 1]

        disk_metrics = {
            'read_ops_per_hour': sum(disk_read_ops_values) / len(disk_read_ops_values) if disk_read_ops_values else 0,
            'write_ops_per_hour': sum(disk_write_ops_values) / len(disk_write_ops_values) if disk_write_ops_values else 0,
            'read_mb_per_hour': (sum(disk_read_bytes_values) / len(disk_read_bytes_values) / 1024 / 1024) if disk_read_bytes_values else 0,
            'write_mb_per_hour': (sum(disk_write_bytes_values) / len(disk_write_bytes_values) / 1024 / 1024) if disk_write_bytes_values else 0,
            'total_read_gb': sum(disk_read_bytes_values) / 1024 / 1024 / 1024 if disk_read_bytes_values else 0,
            'total_write_gb': sum(disk_write_bytes_values) / 1024 / 1024 / 1024 if disk_write_bytes_values else 0
        }

        # Get Status Checks
        status_check_failed = get_metric_stats('StatusCheckFailed', 'Sum')
        status_check_failed_instance = get_metric_stats('StatusCheckFailed_Instance', 'Sum')
        status_check_failed_system = get_metric_stats('StatusCheckFailed_System', 'Sum')

        status_failed_values = [dp[list(dp.keys())[1]] for dp in status_check_failed if len(dp.keys()) > 1]
        status_instance_values = [dp[list(dp.keys())[1]] for dp in status_check_failed_instance if len(dp.keys()) > 1]
        status_system_values = [dp[list(dp.keys())[1]] for dp in status_check_failed_system if len(dp.keys()) > 1]

        status_checks = {
            'total_failures': int(sum(status_failed_values)) if status_failed_values else 0,
            'instance_failures': int(sum(status_instance_values)) if status_instance_values else 0,
            'system_failures': int(sum(status_system_values)) if status_system_values else 0,
            'health_status': 'healthy' if sum(status_failed_values or [0]) == 0 else 'degraded'
        }

        # Detect performance issues
        performance_issues = []

        if cpu_metrics['average'] > 80:
            performance_issues.append(f"High average CPU utilization ({cpu_metrics['average']:.1f}%) - consider upsizing")
        elif cpu_metrics['average'] < 5:
            performance_issues.append(f"Very low CPU utilization ({cpu_metrics['average']:.1f}%) - consider downsizing")

        if cpu_metrics['maximum'] > 95:
            performance_issues.append(f"CPU spikes to {cpu_metrics['maximum']:.1f}% - may cause performance degradation")

        if status_checks['total_failures'] > 0:
            performance_issues.append(f"{status_checks['total_failures']} status check failures detected")

        if cpu_metrics['trend'] == 'increasing':
            performance_issues.append("CPU usage trending upward - monitor for capacity issues")

        # Generate recommendations
        recommendations = []

        if cpu_metrics['average'] < 10 and instance_state == 'running':
            recommendations.append(f"CPU averaging {cpu_metrics['average']:.1f}% - consider downsizing to save costs")

        if cpu_metrics['average'] > 70:
            recommendations.append("High CPU utilization - consider scaling up or out")

        if cpu_metrics['maximum'] > 90 and cpu_metrics['average'] < 50:
            recommendations.append("CPU has spikes but low average - consider burst-optimized instance types (T3/T4)")

        if status_checks['instance_failures'] > 0:
            recommendations.append("Instance status check failures - investigate application/OS issues")

        if status_checks['system_failures'] > 0:
            recommendations.append("System status check failures - consider stop/start to migrate to new hardware")

        if disk_metrics['read_ops_per_hour'] > 10000 or disk_metrics['write_ops_per_hour'] > 10000:
            recommendations.append("High disk I/O - consider provisioned IOPS volumes or instance store")

        # Calculate health score (0-100)
        health_score = 100

        if cpu_metrics['average'] > 80:
            health_score -= 20
        elif cpu_metrics['average'] > 60:
            health_score -= 10

        if cpu_metrics['maximum'] > 95:
            health_score -= 15

        if status_checks['total_failures'] > 0:
            health_score -= 30

        if len(performance_issues) > 0:
            health_score -= min(20, len(performance_issues) * 5)

        health_score = max(0, health_score)

        return {
            'instance_id': instance_id,
            'instance_type': instance_type,
            'instance_state': instance_state,
            'analysis_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': lookback_days
            },
            'cpu_metrics': cpu_metrics,
            'network_metrics': network_metrics,
            'disk_metrics': disk_metrics,
            'status_checks': status_checks,
            'performance_issues': performance_issues,
            'recommendations': recommendations,
            'summary': {
                'health_score': health_score,
                'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
                'avg_cpu': cpu_metrics['average'],
                'max_cpu': cpu_metrics['maximum'],
                'total_issues': len(performance_issues),
                'total_recommendations': len(recommendations)
            }
        }

    except Exception as e:
        return {'error': str(e)}


def analyze_auto_scaling_groups(
    asg_name: Optional[str] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze Auto Scaling Group configuration, health, and optimization opportunities.

    Reviews ASG settings, scaling policies, instance health, and provides
    recommendations for cost optimization and reliability improvements.

    Args:
        asg_name: Optional specific ASG name to analyze (analyzes all if None)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        - total_asgs: Number of Auto Scaling Groups
        - auto_scaling_groups: List of ASG details with configuration
        - scaling_policies: Scaling policy analysis
        - health_summary: Instance health across ASGs
        - cost_optimization: Potential savings opportunities
        - recommendations: Configuration improvement suggestions
        - summary: Overall ASG health and statistics

    Example:
        >>> asgs = analyze_auto_scaling_groups()
        >>> print(f"Total ASGs: {asgs['total_asgs']}")
        >>> for asg in asgs['auto_scaling_groups']:
        ...     print(f"{asg['name']}: {asg['desired_capacity']} instances")
    """
    if aws_client is None:
        aws_client = AWSClient()

    autoscaling = aws_client.get_client('autoscaling')

    try:
        # Get Auto Scaling Groups
        if asg_name:
            response = autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )
        else:
            response = autoscaling.describe_auto_scaling_groups()

        asgs = response['AutoScalingGroups']

        if not asgs:
            return {
                'total_asgs': 0,
                'auto_scaling_groups': [],
                'message': 'No Auto Scaling Groups found'
            }

        asg_details = []
        total_instances = 0
        total_healthy = 0
        total_unhealthy = 0
        total_desired = 0

        for asg in asgs:
            name = asg['AutoScalingGroupName']
            min_size = asg['MinSize']
            max_size = asg['MaxSize']
            desired = asg['DesiredCapacity']
            total_desired += desired

            # Get instance health
            instances = asg.get('Instances', [])
            healthy_count = sum(1 for i in instances if i['HealthStatus'] == 'Healthy')
            unhealthy_count = len(instances) - healthy_count
            total_instances += len(instances)
            total_healthy += healthy_count
            total_unhealthy += unhealthy_count

            # Get scaling policies
            policies_response = autoscaling.describe_policies(
                AutoScalingGroupName=name
            )
            policies = policies_response.get('ScalingPolicies', [])

            # Analyze configuration
            issues = []
            recommendations = []

            if min_size == max_size:
                issues.append("Fixed size ASG (min=max) - no auto-scaling benefit")
                recommendations.append("Set min < max to enable auto-scaling")

            if len(instances) < desired:
                issues.append(f"Under capacity: {len(instances)}/{desired} instances")

            if unhealthy_count > 0:
                issues.append(f"{unhealthy_count} unhealthy instances")
                recommendations.append("Investigate and replace unhealthy instances")

            if len(policies) == 0:
                issues.append("No scaling policies configured")
                recommendations.append("Add target tracking or step scaling policies")

            # Check for mixed instance types (cost optimization)
            has_mixed_instances = 'MixedInstancesPolicy' in asg
            if not has_mixed_instances:
                recommendations.append("Consider mixed instances policy for cost savings with spot instances")

            # Get availability zones
            azs = asg.get('AvailabilityZones', [])
            if len(azs) < 2:
                issues.append(f"Single AZ deployment - reliability risk")
                recommendations.append("Deploy across multiple AZs for high availability")

            asg_details.append({
                'name': name,
                'min_size': min_size,
                'max_size': max_size,
                'desired_capacity': desired,
                'current_instances': len(instances),
                'healthy_instances': healthy_count,
                'unhealthy_instances': unhealthy_count,
                'availability_zones': azs,
                'az_count': len(azs),
                'scaling_policies': len(policies),
                'has_mixed_instances': has_mixed_instances,
                'health_check_type': asg.get('HealthCheckType', 'EC2'),
                'health_check_grace_period': asg.get('HealthCheckGracePeriod', 0),
                'issues': issues,
                'recommendations': recommendations,
                'status': 'healthy' if len(issues) == 0 else 'warning' if unhealthy_count == 0 else 'critical'
            })

        # Overall recommendations
        overall_recommendations = []

        if total_unhealthy > 0:
            overall_recommendations.append(f"{total_unhealthy} unhealthy instances across ASGs - investigate health check failures")

        asgs_without_policies = sum(1 for asg in asg_details if asg['scaling_policies'] == 0)
        if asgs_without_policies > 0:
            overall_recommendations.append(f"{asgs_without_policies} ASGs without scaling policies - enable dynamic scaling")

        asgs_single_az = sum(1 for asg in asg_details if asg['az_count'] < 2)
        if asgs_single_az > 0:
            overall_recommendations.append(f"{asgs_single_az} ASGs in single AZ - deploy multi-AZ for reliability")

        asgs_without_mixed = sum(1 for asg in asg_details if not asg['has_mixed_instances'])
        if asgs_without_mixed > 0:
            overall_recommendations.append(f"{asgs_without_mixed} ASGs could use mixed instances policy for 50-90% cost savings with spot")

        return {
            'total_asgs': len(asgs),
            'auto_scaling_groups': asg_details,
            'health_summary': {
                'total_instances': total_instances,
                'healthy_instances': total_healthy,
                'unhealthy_instances': total_unhealthy,
                'health_percentage': (total_healthy / total_instances * 100) if total_instances > 0 else 100
            },
            'recommendations': overall_recommendations,
            'summary': {
                'total_desired_capacity': total_desired,
                'asgs_with_issues': sum(1 for asg in asg_details if len(asg['issues']) > 0),
                'asgs_without_scaling': asgs_without_policies,
                'asgs_single_az': asgs_single_az,
                'overall_health': 'healthy' if total_unhealthy == 0 else 'degraded'
            }
        }

    except Exception as e:
        return {'error': str(e)}


def analyze_load_balancers(
    lb_name: Optional[str] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze Elastic Load Balancers (ALB, NLB, CLB) for health, cost, and optimization.

    Reviews load balancer configuration, target health, listener rules,
    and identifies cost optimization opportunities.

    Args:
        lb_name: Optional specific load balancer name/ARN to analyze
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        - total_load_balancers: Number of load balancers
        - load_balancers: List of LB details with configuration
        - target_health: Health status of registered targets
        - cost_analysis: Monthly cost estimates
        - unused_load_balancers: LBs with no healthy targets
        - recommendations: Optimization suggestions
        - summary: Overall statistics and health

    Example:
        >>> lbs = analyze_load_balancers()
        >>> print(f"Total LBs: {lbs['total_load_balancers']}")
        >>> print(f"Unused LBs: {lbs['summary']['unused_count']}")
        >>> print(f"Estimated monthly cost: ${lbs['summary']['total_monthly_cost']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    elbv2 = aws_client.get_client('elbv2')  # For ALB/NLB
    elb = aws_client.get_client('elb')      # For Classic LB

    try:
        # Get Application and Network Load Balancers
        if lb_name:
            alb_nlb_response = elbv2.describe_load_balancers(Names=[lb_name])
        else:
            alb_nlb_response = elbv2.describe_load_balancers()

        alb_nlbs = alb_nlb_response.get('LoadBalancers', [])

        # Get Classic Load Balancers
        if lb_name:
            clb_response = elb.describe_load_balancers(LoadBalancerNames=[lb_name])
        else:
            clb_response = elb.describe_load_balancers()

        clbs = clb_response.get('LoadBalancerDescriptions', [])

        if not alb_nlbs and not clbs:
            return {
                'total_load_balancers': 0,
                'load_balancers': [],
                'message': 'No load balancers found'
            }

        lb_details = []
        total_monthly_cost = 0
        unused_lbs = []

        # Pricing (us-east-1 estimates)
        ALB_HOURLY = 0.0225  # $0.0225/hour
        NLB_HOURLY = 0.0225  # $0.0225/hour
        CLB_HOURLY = 0.025   # $0.025/hour
        HOURS_PER_MONTH = 730

        # Analyze ALBs and NLBs
        for lb in alb_nlbs:
            lb_type = lb['Type']  # 'application' or 'network'
            lb_arn = lb['LoadBalancerArn']
            lb_name_str = lb['LoadBalancerName']
            lb_dns = lb['DNSName']
            scheme = lb['Scheme']  # 'internet-facing' or 'internal'
            azs = lb.get('AvailabilityZones', [])

            # Get target groups
            tg_response = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
            target_groups = tg_response.get('TargetGroups', [])

            total_targets = 0
            healthy_targets = 0
            unhealthy_targets = 0

            for tg in target_groups:
                tg_arn = tg['TargetGroupArn']
                health_response = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                targets = health_response.get('TargetHealthDescriptions', [])

                total_targets += len(targets)
                healthy_targets += sum(1 for t in targets if t['TargetHealth']['State'] == 'healthy')
                unhealthy_targets += sum(1 for t in targets if t['TargetHealth']['State'] != 'healthy')

            # Calculate cost
            hourly_cost = ALB_HOURLY if lb_type == 'application' else NLB_HOURLY
            monthly_cost = hourly_cost * HOURS_PER_MONTH
            total_monthly_cost += monthly_cost

            # Detect issues
            issues = []
            recommendations = []

            if total_targets == 0:
                issues.append("No registered targets")
                unused_lbs.append(lb_name_str)
                recommendations.append(f"Delete unused {lb_type.upper()} to save ${monthly_cost:.2f}/month")
            elif healthy_targets == 0:
                issues.append("No healthy targets")
                recommendations.append("All targets unhealthy - investigate health check configuration")
            elif unhealthy_targets > 0:
                issues.append(f"{unhealthy_targets}/{total_targets} unhealthy targets")

            if len(azs) < 2:
                issues.append("Single AZ deployment")
                recommendations.append("Deploy across multiple AZs for high availability")

            if len(target_groups) == 0:
                issues.append("No target groups configured")
                recommendations.append("Configure target groups or delete unused LB")

            lb_details.append({
                'name': lb_name_str,
                'type': lb_type.upper(),
                'dns_name': lb_dns,
                'scheme': scheme,
                'availability_zones': len(azs),
                'target_groups': len(target_groups),
                'total_targets': total_targets,
                'healthy_targets': healthy_targets,
                'unhealthy_targets': unhealthy_targets,
                'monthly_cost': monthly_cost,
                'issues': issues,
                'recommendations': recommendations,
                'status': 'healthy' if healthy_targets > 0 and unhealthy_targets == 0 else 'warning' if healthy_targets > 0 else 'critical'
            })

        # Analyze Classic Load Balancers
        for lb in clbs:
            lb_name_str = lb['LoadBalancerName']
            lb_dns = lb['DNSName']
            scheme = lb['Scheme']
            azs = lb.get('AvailabilityZones', [])
            instances = lb.get('Instances', [])

            # Get instance health
            if instances:
                health_response = elb.describe_instance_health(LoadBalancerName=lb_name_str)
                instance_states = health_response.get('InstanceStates', [])

                total_targets = len(instance_states)
                healthy_targets = sum(1 for i in instance_states if i['State'] == 'InService')
                unhealthy_targets = total_targets - healthy_targets
            else:
                total_targets = 0
                healthy_targets = 0
                unhealthy_targets = 0

            # Calculate cost
            monthly_cost = CLB_HOURLY * HOURS_PER_MONTH
            total_monthly_cost += monthly_cost

            # Detect issues
            issues = ['Classic Load Balancer (legacy - consider migrating to ALB/NLB)']
            recommendations = ['Migrate to ALB or NLB for better features and potential cost savings']

            if total_targets == 0:
                issues.append("No registered instances")
                unused_lbs.append(lb_name_str)
                recommendations.append(f"Delete unused CLB to save ${monthly_cost:.2f}/month")
            elif healthy_targets == 0:
                issues.append("No healthy instances")
            elif unhealthy_targets > 0:
                issues.append(f"{unhealthy_targets}/{total_targets} unhealthy instances")

            if len(azs) < 2:
                issues.append("Single AZ deployment")

            lb_details.append({
                'name': lb_name_str,
                'type': 'CLB',
                'dns_name': lb_dns,
                'scheme': scheme,
                'availability_zones': len(azs),
                'target_groups': 0,
                'total_targets': total_targets,
                'healthy_targets': healthy_targets,
                'unhealthy_targets': unhealthy_targets,
                'monthly_cost': monthly_cost,
                'issues': issues,
                'recommendations': recommendations,
                'status': 'warning'  # CLBs always warning due to legacy
            })

        # Overall recommendations
        overall_recommendations = []

        if len(unused_lbs) > 0:
            unused_cost = sum(lb['monthly_cost'] for lb in lb_details if lb['name'] in unused_lbs)
            overall_recommendations.append(f"Delete {len(unused_lbs)} unused load balancers to save ${unused_cost:.2f}/month")

        clb_count = sum(1 for lb in lb_details if lb['type'] == 'CLB')
        if clb_count > 0:
            overall_recommendations.append(f"Migrate {clb_count} Classic Load Balancers to ALB/NLB for better performance")

        single_az_count = sum(1 for lb in lb_details if lb['availability_zones'] < 2)
        if single_az_count > 0:
            overall_recommendations.append(f"{single_az_count} load balancers in single AZ - deploy multi-AZ for reliability")

        return {
            'total_load_balancers': len(lb_details),
            'load_balancers': lb_details,
            'unused_load_balancers': unused_lbs,
            'recommendations': overall_recommendations,
            'summary': {
                'total_monthly_cost': total_monthly_cost,
                'alb_count': sum(1 for lb in lb_details if lb['type'] == 'ALB'),
                'nlb_count': sum(1 for lb in lb_details if lb['type'] == 'NLB'),
                'clb_count': clb_count,
                'unused_count': len(unused_lbs),
                'unhealthy_count': sum(1 for lb in lb_details if lb['status'] in ['warning', 'critical']),
                'potential_savings': sum(lb['monthly_cost'] for lb in lb_details if lb['name'] in unused_lbs)
            }
        }

    except Exception as e:
        return {'error': str(e)}


def get_ec2_spot_recommendations(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Identify EC2 instances that could be converted to Spot for 50-90% cost savings.

    Analyzes running on-demand instances and identifies candidates for Spot instances
    based on instance characteristics, usage patterns, and interruption tolerance.

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        - total_instances: Total on-demand instances analyzed
        - spot_candidates: Instances suitable for Spot conversion
        - current_monthly_cost: Current on-demand costs
        - potential_spot_cost: Estimated Spot costs
        - potential_savings: Monthly and annual savings
        - recommendations: Detailed conversion recommendations
        - summary: Overall savings opportunity

    Example:
        >>> spot = get_ec2_spot_recommendations()
        >>> print(f"Potential savings: ${spot['potential_savings']['monthly']:.2f}/month")
        >>> print(f"Spot candidates: {len(spot['spot_candidates'])} instances")
        >>> for candidate in spot['spot_candidates']:
        ...     print(f"{candidate['instance_id']}: Save ${candidate['monthly_savings']:.2f}/month")
    """
    if aws_client is None:
        aws_client = AWSClient()

    ec2 = aws_client.get_client('ec2')

    # Simplified EC2 pricing (us-east-1, on-demand hourly rates)
    # In production, use AWS Price List API for accurate pricing
    PRICING = {
        't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464,
        't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416, 't3.large': 0.0832,
        'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
        'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
        'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504
    }

    HOURS_PER_MONTH = 730
    SPOT_DISCOUNT = 0.70  # Typical 70% discount (50-90% range)

    try:
        # Get all running on-demand instances
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'instance-lifecycle', 'Values': ['on-demand', 'scheduled']}  # Exclude existing spot
            ]
        )

        instances = []
        for reservation in response['Reservations']:
            instances.extend(reservation['Instances'])

        if not instances:
            # Try without lifecycle filter (some instances don't have this attribute)
            response = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    # Exclude spot instances
                    if instance.get('InstanceLifecycle') != 'spot':
                        instances.append(instance)

        if not instances:
            return {
                'total_instances': 0,
                'spot_candidates': [],
                'message': 'No running on-demand instances found'
            }

        spot_candidates = []
        total_current_cost = 0
        total_spot_cost = 0

        for instance in instances:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            launch_time = instance['LaunchTime']

            # Get tags
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            name = tags.get('Name', 'N/A')

            # Get pricing
            hourly_rate = PRICING.get(instance_type, 0.10)  # Default fallback
            monthly_cost = hourly_rate * HOURS_PER_MONTH
            total_current_cost += monthly_cost

            spot_hourly = hourly_rate * SPOT_DISCOUNT
            spot_monthly = spot_hourly * HOURS_PER_MONTH
            total_spot_cost += spot_monthly

            monthly_savings = monthly_cost - spot_monthly
            savings_percentage = ((monthly_cost - spot_monthly) / monthly_cost * 100) if monthly_cost > 0 else 0

            # Determine suitability for Spot
            suitability_score = 100
            suitability_factors = []
            interruption_tolerance = "High"

            # Check instance type - burstable instances (T-series) are excellent for spot
            if instance_type.startswith('t2.') or instance_type.startswith('t3.'):
                suitability_factors.append("Burstable instance type (T-series) - excellent for Spot")
            else:
                suitability_score -= 10

            # Check for Auto Scaling Group (good for spot)
            if any('aws:autoscaling:groupName' in tag for tag in tags):
                suitability_factors.append("Part of Auto Scaling Group - good for Spot with mixed instances policy")
                suitability_score += 10
            else:
                suitability_score -= 5
                interruption_tolerance = "Medium"

            # Check for production tag
            environment = tags.get('Environment', '').lower()
            if 'prod' in environment or 'production' in environment:
                suitability_score -= 20
                suitability_factors.append("Production instance - use Spot with caution (ASG + mixed instances)")
                interruption_tolerance = "Low"
            else:
                suitability_factors.append("Non-production instance - ideal for Spot")

            # Check for stateful applications (databases, etc.)
            if 'database' in name.lower() or 'db' in name.lower() or 'sql' in name.lower():
                suitability_score -= 30
                suitability_factors.append("Database workload - Spot not recommended unless read replica")
                interruption_tolerance = "Very Low"

            # Determine recommendation
            if suitability_score >= 70:
                recommendation = "Strongly recommended for Spot - high savings, low risk"
            elif suitability_score >= 50:
                recommendation = "Good Spot candidate - use with Auto Scaling for fault tolerance"
            elif suitability_score >= 30:
                recommendation = "Consider Spot for non-critical workloads only"
            else:
                recommendation = "Not recommended for Spot - use on-demand or Reserved Instances"

            # Implementation guide
            implementation_steps = [
                "1. Create Launch Template with same configuration",
                "2. Update Auto Scaling Group with mixed instances policy",
                "3. Set On-Demand base capacity (e.g., 20%) for stability",
                "4. Add multiple instance types for better Spot availability",
                "5. Monitor interruption rates and adjust strategy"
            ]

            if suitability_score >= 50:
                spot_candidates.append({
                    'instance_id': instance_id,
                    'name': name,
                    'instance_type': instance_type,
                    'current_hourly_cost': hourly_rate,
                    'spot_hourly_cost': spot_hourly,
                    'monthly_cost': monthly_cost,
                    'spot_monthly_cost': spot_monthly,
                    'monthly_savings': monthly_savings,
                    'annual_savings': monthly_savings * 12,
                    'savings_percentage': savings_percentage,
                    'suitability_score': suitability_score,
                    'interruption_tolerance': interruption_tolerance,
                    'suitability_factors': suitability_factors,
                    'recommendation': recommendation,
                    'implementation_steps': implementation_steps
                })

        # Sort by savings
        spot_candidates.sort(key=lambda x: x['monthly_savings'], reverse=True)

        total_monthly_savings = total_current_cost - total_spot_cost
        total_annual_savings = total_monthly_savings * 12

        # Overall recommendations
        recommendations = []

        if len(spot_candidates) > 0:
            top_savings = sum(c['monthly_savings'] for c in spot_candidates[:5])
            recommendations.append(f"Convert top {min(5, len(spot_candidates))} candidates to Spot for ${top_savings:.2f}/month savings")

        recommendations.append("Use Auto Scaling Groups with mixed instances policy (combine on-demand + spot)")
        recommendations.append("Set on-demand base capacity to 10-30% for stability")
        recommendations.append("Use multiple instance types to increase Spot availability")
        recommendations.append("Implement graceful shutdown handling for Spot interruptions")
        recommendations.append("Monitor Spot interruption rates in CloudWatch")

        return {
            'total_instances': len(instances),
            'spot_candidates': spot_candidates,
            'current_monthly_cost': total_current_cost,
            'potential_spot_cost': total_spot_cost,
            'potential_savings': {
                'monthly': total_monthly_savings,
                'annual': total_annual_savings,
                'percentage': (total_monthly_savings / total_current_cost * 100) if total_current_cost > 0 else 0
            },
            'recommendations': recommendations,
            'summary': {
                'total_candidates': len(spot_candidates),
                'high_suitability': sum(1 for c in spot_candidates if c['suitability_score'] >= 70),
                'medium_suitability': sum(1 for c in spot_candidates if 50 <= c['suitability_score'] < 70),
                'estimated_discount': f"{SPOT_DISCOUNT * 100:.0f}%",
                'top_opportunity': spot_candidates[0]['instance_id'] if spot_candidates else None,
                'top_savings': spot_candidates[0]['monthly_savings'] if spot_candidates else 0
            }
        }

    except Exception as e:
        return {'error': str(e)}
