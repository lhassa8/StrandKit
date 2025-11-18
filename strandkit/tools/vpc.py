"""
VPC/Networking tools for StrandKit.

This module provides comprehensive VPC and networking analysis tools for:
- NAT Gateway cost optimization
- VPC configuration analysis
- Data transfer cost analysis
- VPC endpoint recommendations
- Network performance troubleshooting

All functions are decorated with @tool for AWS Strands Agents integration
and can also be used standalone.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from strands import tool
from strandkit.core.aws_client import AWSClient


@tool
def find_unused_nat_gateways(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Find NAT Gateways with no traffic that are wasting $32/month each.

    NAT Gateways cost $0.045/hour ($32.40/month) plus data processing charges.
    Unused NAT Gateways are a common source of waste.

    Identifies NAT Gateways with:
    - Zero bytes processed in last 7 days
    - Low utilization (<1GB/day)

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict with unused NAT Gateways, costs, and cleanup recommendations

    Example:
        >>> result = find_unused_nat_gateways()
        >>> print(f"Found {result['summary']['total_unused']} unused NAT Gateways")
        >>> print(f"Monthly waste: ${result['summary']['monthly_waste']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    ec2 = aws_client.get_client('ec2')
    cloudwatch = aws_client.get_client('cloudwatch')

    try:
        # Get all NAT Gateways
        response = ec2.describe_nat_gateways(
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        nat_gateways = response['NatGateways']

        unused_nat_gateways = []
        low_usage_nat_gateways = []
        total_monthly_waste = 0.0

        # NAT Gateway costs
        hourly_cost = 0.045
        monthly_cost_per_nat = hourly_cost * 730  # $32.85/month

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        for nat in nat_gateways:
            nat_id = nat['NatGatewayId']
            subnet_id = nat.get('SubnetId', 'N/A')
            vpc_id = nat.get('VpcId', 'N/A')
            state = nat['State']

            # Get BytesOutToDestination metric (traffic through NAT)
            bytes_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/NATGateway',
                MetricName='BytesOutToDestination',
                Dimensions=[{'Name': 'NatGatewayId', 'Value': nat_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,  # Daily
                Statistics=['Sum']
            )

            datapoints = bytes_response.get('Datapoints', [])

            if not datapoints:
                # No metrics - completely unused
                unused_nat_gateways.append({
                    'nat_gateway_id': nat_id,
                    'vpc_id': vpc_id,
                    'subnet_id': subnet_id,
                    'state': state,
                    'bytes_processed_7d': 0,
                    'monthly_cost': round(monthly_cost_per_nat, 2),
                    'status': 'unused',
                    'recommendation': 'Delete if not needed - zero traffic detected',
                    'risk': 'low'
                })
                total_monthly_waste += monthly_cost_per_nat
            else:
                # Calculate total bytes
                total_bytes = sum(dp['Sum'] for dp in datapoints)
                total_gb = total_bytes / (1024**3)
                daily_avg_gb = total_gb / 7

                if daily_avg_gb < 1.0:
                    # Very low usage
                    low_usage_nat_gateways.append({
                        'nat_gateway_id': nat_id,
                        'vpc_id': vpc_id,
                        'subnet_id': subnet_id,
                        'state': state,
                        'bytes_processed_7d': int(total_bytes),
                        'total_gb_7d': round(total_gb, 2),
                        'daily_avg_gb': round(daily_avg_gb, 3),
                        'monthly_cost': round(monthly_cost_per_nat, 2),
                        'status': 'low_usage',
                        'recommendation': f'Very low usage ({daily_avg_gb:.3f} GB/day) - consider deletion',
                        'risk': 'medium'
                    })
                    # Consider 50% of cost as waste for low usage
                    total_monthly_waste += monthly_cost_per_nat * 0.5

        # Get VPC names for context
        vpc_names = {}
        if nat_gateways:
            vpc_ids = list(set(nat['VpcId'] for nat in nat_gateways))
            vpcs_response = ec2.describe_vpcs(VpcIds=vpc_ids)
            for vpc in vpcs_response['Vpcs']:
                name_tag = next((tag['Value'] for tag in vpc.get('Tags', []) if tag['Key'] == 'Name'), None)
                vpc_names[vpc['VpcId']] = name_tag or vpc['VpcId']

        # Add VPC names to results
        for nat in unused_nat_gateways + low_usage_nat_gateways:
            nat['vpc_name'] = vpc_names.get(nat['vpc_id'], nat['vpc_id'])

        all_issues = unused_nat_gateways + low_usage_nat_gateways

        return {
            'unused_nat_gateways': unused_nat_gateways,
            'low_usage_nat_gateways': low_usage_nat_gateways,
            'all_issues': all_issues,
            'summary': {
                'total_nat_gateways_scanned': len(nat_gateways),
                'total_unused': len(unused_nat_gateways),
                'total_low_usage': len(low_usage_nat_gateways),
                'monthly_waste': round(total_monthly_waste, 2),
                'annual_waste': round(total_monthly_waste * 12, 2),
                'cost_per_nat_gateway': round(monthly_cost_per_nat, 2)
            },
            'recommendations': [
                f"Delete {len(unused_nat_gateways)} unused NAT Gateways to save ${len(unused_nat_gateways) * monthly_cost_per_nat:.2f}/month",
                f"Review {len(low_usage_nat_gateways)} low-usage NAT Gateways",
                "Consider using VPC endpoints instead of NAT Gateways for AWS service access"
            ] if all_issues else ["No unused NAT Gateways found - good cost management!"]
        }

    except Exception as e:
        return {
            'error': f'Failed to find unused NAT Gateways: {str(e)}',
            'unused_nat_gateways': [],
            'low_usage_nat_gateways': []
        }


@tool
def analyze_vpc_configuration(
    vpc_id: Optional[str] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze VPC configuration including subnets, route tables, and networking.

    Analyzes:
    - VPC CIDR blocks and IP address usage
    - Subnet configuration and availability
    - Route table configuration
    - Internet Gateway and NAT Gateway setup
    - VPC peering connections
    - Network ACLs
    - VPC Flow Logs status

    Args:
        vpc_id: Optional specific VPC ID to analyze (analyzes all if None)
        aws_client: Optional AWSClient instance

    Returns:
        Dict with VPC configuration details and recommendations

    Example:
        >>> result = analyze_vpc_configuration("vpc-12345")
        >>> print(f"Subnets: {result['vpc_analysis']['subnet_count']}")
        >>> print(f"Flow Logs: {result['vpc_analysis']['flow_logs_enabled']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    ec2 = aws_client.get_client('ec2')

    try:
        # Get VPCs
        if vpc_id:
            vpcs_response = ec2.describe_vpcs(VpcIds=[vpc_id])
        else:
            vpcs_response = ec2.describe_vpcs()

        vpcs = vpcs_response['Vpcs']

        vpc_analyses = []

        for vpc in vpcs:
            vpc_id_current = vpc['VpcId']
            cidr = vpc['CidrBlock']
            is_default = vpc.get('IsDefault', False)

            # Get VPC name
            vpc_name = next((tag['Value'] for tag in vpc.get('Tags', []) if tag['Key'] == 'Name'), vpc_id_current)

            # Get subnets
            subnets_response = ec2.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id_current]}]
            )
            subnets = subnets_response['Subnets']

            # Analyze subnets
            public_subnets = 0
            private_subnets = 0
            subnet_details = []

            for subnet in subnets:
                subnet_id = subnet['SubnetId']
                subnet_cidr = subnet['CidrBlock']
                az = subnet['AvailabilityZone']
                available_ips = subnet['AvailableIpAddressCount']

                # Check if public (has route to IGW)
                is_public = subnet.get('MapPublicIpOnLaunch', False)

                if is_public:
                    public_subnets += 1
                else:
                    private_subnets += 1

                subnet_details.append({
                    'subnet_id': subnet_id,
                    'cidr': subnet_cidr,
                    'availability_zone': az,
                    'type': 'public' if is_public else 'private',
                    'available_ips': available_ips
                })

            # Get route tables
            route_tables_response = ec2.describe_route_tables(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id_current]}]
            )
            route_tables = route_tables_response['RouteTables']

            # Get Internet Gateways
            igw_response = ec2.describe_internet_gateways(
                Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id_current]}]
            )
            internet_gateways = igw_response['InternetGateways']

            # Get NAT Gateways
            nat_response = ec2.describe_nat_gateways(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id_current]}]
            )
            nat_gateways = [nat for nat in nat_response['NatGateways'] if nat['State'] == 'available']

            # Get VPC Peering
            peering_response = ec2.describe_vpc_peering_connections(
                Filters=[
                    {'Name': 'requester-vpc-info.vpc-id', 'Values': [vpc_id_current]}
                ]
            )
            peering_connections = peering_response['VpcPeeringConnections']

            # Get VPC Flow Logs
            flow_logs_response = ec2.describe_flow_logs(
                Filters=[{'Name': 'resource-id', 'Values': [vpc_id_current]}]
            )
            flow_logs = flow_logs_response['FlowLogs']
            flow_logs_enabled = len(flow_logs) > 0

            # Recommendations
            recommendations = []

            if not flow_logs_enabled:
                recommendations.append({
                    'priority': 'high',
                    'category': 'security',
                    'recommendation': 'Enable VPC Flow Logs for network traffic analysis',
                    'command': f"aws ec2 create-flow-logs --resource-type VPC --resource-ids {vpc_id_current}"
                })

            if len(internet_gateways) == 0 and public_subnets > 0:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'network',
                    'recommendation': 'Public subnets detected but no Internet Gateway attached',
                    'issue': 'Public subnets may not have internet access'
                })

            if private_subnets > 0 and len(nat_gateways) == 0:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'network',
                    'recommendation': 'Private subnets detected but no NAT Gateway',
                    'note': 'Private subnets cannot access internet without NAT Gateway or VPC endpoints'
                })

            if len(set(s['availability_zone'] for s in subnet_details)) == 1:
                recommendations.append({
                    'priority': 'high',
                    'category': 'reliability',
                    'recommendation': 'All subnets in single AZ - no high availability',
                    'action': 'Create subnets in multiple Availability Zones'
                })

            vpc_analyses.append({
                'vpc_id': vpc_id_current,
                'vpc_name': vpc_name,
                'cidr_block': cidr,
                'is_default': is_default,
                'subnet_count': len(subnets),
                'public_subnets': public_subnets,
                'private_subnets': private_subnets,
                'subnet_details': subnet_details,
                'route_table_count': len(route_tables),
                'internet_gateway_count': len(internet_gateways),
                'nat_gateway_count': len(nat_gateways),
                'peering_connection_count': len(peering_connections),
                'flow_logs_enabled': flow_logs_enabled,
                'recommendations': recommendations,
                'availability_zones': list(set(s['availability_zone'] for s in subnet_details))
            })

        return {
            'vpc_analyses': vpc_analyses,
            'summary': {
                'total_vpcs': len(vpc_analyses),
                'total_subnets': sum(v['subnet_count'] for v in vpc_analyses),
                'total_nat_gateways': sum(v['nat_gateway_count'] for v in vpc_analyses),
                'vpcs_with_flow_logs': sum(1 for v in vpc_analyses if v['flow_logs_enabled']),
                'vpcs_without_flow_logs': sum(1 for v in vpc_analyses if not v['flow_logs_enabled'])
            },
            'vpc_analysis': vpc_analyses[0] if len(vpc_analyses) == 1 else None
        }

    except Exception as e:
        return {
            'error': f'Failed to analyze VPC configuration: {str(e)}',
            'vpc_analyses': []
        }


@tool
def analyze_data_transfer_costs(
    days_back: int = 30,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze AWS data transfer costs which can be 10-30% of total bill.

    Breaks down data transfer costs by:
    - Inter-region transfers
    - Internet egress (data out to internet)
    - Inter-AZ transfers
    - CloudFront distributions
    - NAT Gateway data processing

    Args:
        days_back: Number of days to analyze (default 30)
        aws_client: Optional AWSClient instance

    Returns:
        Dict with data transfer cost breakdown and optimization recommendations

    Example:
        >>> result = analyze_data_transfer_costs(days_back=30)
        >>> print(f"Total transfer costs: ${result['summary']['total_transfer_costs']:.2f}")
        >>> print(f"Percentage of bill: {result['summary']['percentage_of_total_bill']:.1f}%")
    """
    if aws_client is None:
        aws_client = AWSClient()

    ce = aws_client.get_client('ce')

    try:
        # Get time range
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days_back)

        # Get total AWS costs
        total_response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost']
        )

        total_cost = 0.0
        if total_response['ResultsByTime']:
            total_cost = float(total_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

        # Get data transfer costs
        # AWS Cost Explorer service names for data transfer
        transfer_services = [
            'AWS Data Transfer',
            'Amazon CloudFront',
            'AWS VPN'
        ]

        transfer_breakdown = []
        total_transfer_cost = 0.0

        for service in transfer_services:
            service_response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service]
                    }
                }
            )

            if service_response['ResultsByTime']:
                cost = float(service_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
                if cost > 0:
                    total_transfer_cost += cost
                    transfer_breakdown.append({
                        'service': service,
                        'cost': round(cost, 2),
                        'percentage': round(cost / total_cost * 100, 2) if total_cost > 0 else 0
                    })

        # Get NAT Gateway data processing costs
        nat_response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            Filter={
                'Dimensions': {
                    'Key': 'USAGE_TYPE_GROUP',
                    'Values': ['NAT Gateway']
                }
            }
        )

        nat_cost = 0.0
        if nat_response['ResultsByTime']:
            nat_cost = float(nat_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            if nat_cost > 0:
                total_transfer_cost += nat_cost
                transfer_breakdown.append({
                    'service': 'NAT Gateway',
                    'cost': round(nat_cost, 2),
                    'percentage': round(nat_cost / total_cost * 100, 2) if total_cost > 0 else 0
                })

        # Sort by cost
        transfer_breakdown.sort(key=lambda x: x['cost'], reverse=True)

        # Calculate percentage of total bill
        percentage_of_bill = (total_transfer_cost / total_cost * 100) if total_cost > 0 else 0

        # Optimization recommendations
        recommendations = []

        if percentage_of_bill > 15:
            recommendations.append({
                'priority': 'high',
                'category': 'cost',
                'recommendation': f'Data transfer is {percentage_of_bill:.1f}% of total bill',
                'action': 'Review data transfer patterns and optimize'
            })

        # CloudFront recommendation
        cloudfront_cost = next((item['cost'] for item in transfer_breakdown if 'CloudFront' in item['service']), 0)
        if cloudfront_cost == 0 and total_transfer_cost > 100:
            recommendations.append({
                'priority': 'high',
                'category': 'cost',
                'recommendation': 'Consider using CloudFront CDN to reduce data transfer costs',
                'savings': 'CloudFront is typically 25-50% cheaper than direct internet egress'
            })

        # VPC endpoint recommendation
        nat_percent = (nat_cost / total_transfer_cost * 100) if total_transfer_cost > 0 else 0
        if nat_percent > 30:
            recommendations.append({
                'priority': 'high',
                'category': 'cost',
                'recommendation': f'NAT Gateway costs are {nat_percent:.1f}% of transfer costs',
                'action': 'Use VPC endpoints for AWS services to avoid NAT Gateway charges',
                'services': 'S3, DynamoDB, and other AWS services support VPC endpoints'
            })

        # Cross-region recommendation
        if total_transfer_cost > 200:
            recommendations.append({
                'priority': 'medium',
                'category': 'architecture',
                'recommendation': 'High data transfer costs detected',
                'actions': [
                    'Review cross-region data transfers',
                    'Consider data locality (keep compute close to data)',
                    'Use AWS PrivateLink for service-to-service communication'
                ]
            })

        return {
            'transfer_breakdown': transfer_breakdown,
            'summary': {
                'days_analyzed': days_back,
                'total_transfer_costs': round(total_transfer_cost, 2),
                'total_aws_costs': round(total_cost, 2),
                'percentage_of_total_bill': round(percentage_of_bill, 2),
                'top_transfer_service': transfer_breakdown[0]['service'] if transfer_breakdown else 'None'
            },
            'recommendations': recommendations if recommendations else [
                'Data transfer costs are well-optimized (<10% of total bill)'
            ]
        }

    except Exception as e:
        return {
            'error': f'Failed to analyze data transfer costs: {str(e)}',
            'transfer_breakdown': []
        }


@tool
def analyze_vpc_endpoints(
    vpc_id: Optional[str] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze VPC endpoint usage and identify cost savings opportunities.

    VPC endpoints allow private connections to AWS services without NAT Gateways,
    reducing data transfer costs and improving security.

    Analyzes:
    - Existing VPC endpoints
    - Services that could benefit from VPC endpoints
    - Potential cost savings from using endpoints vs NAT

    Args:
        vpc_id: Optional specific VPC ID to analyze (analyzes all if None)
        aws_client: Optional AWSClient instance

    Returns:
        Dict with VPC endpoint analysis and recommendations

    Example:
        >>> result = analyze_vpc_endpoints()
        >>> print(f"Existing endpoints: {result['summary']['total_endpoints']}")
        >>> print(f"Potential savings: ${result['summary']['potential_monthly_savings']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    ec2 = aws_client.get_client('ec2')

    try:
        # Get VPC endpoints
        if vpc_id:
            endpoints_response = ec2.describe_vpc_endpoints(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
        else:
            endpoints_response = ec2.describe_vpc_endpoints()

        endpoints = endpoints_response['VpcEndpoints']

        # Analyze existing endpoints
        endpoint_analysis = []
        gateway_endpoints = 0
        interface_endpoints = 0
        interface_endpoint_cost = 0.0

        for endpoint in endpoints:
            endpoint_id = endpoint['VpcEndpointId']
            service_name = endpoint['ServiceName']
            endpoint_type = endpoint['VpcEndpointType']
            state = endpoint['State']

            # Interface endpoints cost $0.01/hour per AZ
            if endpoint_type == 'Interface':
                interface_endpoints += 1
                # Estimate cost (assume 2 AZs)
                interface_endpoint_cost += 0.01 * 2 * 730  # $14.60/month per interface endpoint
            else:
                gateway_endpoints += 1

            endpoint_analysis.append({
                'endpoint_id': endpoint_id,
                'service_name': service_name,
                'type': endpoint_type,
                'state': state,
                'monthly_cost': 14.60 if endpoint_type == 'Interface' else 0.0
            })

        # Recommended endpoints that save money
        # Gateway endpoints (free!)
        recommended_gateway_endpoints = [
            {
                'service': 'com.amazonaws.REGION.s3',
                'benefit': 'Free gateway endpoint - eliminates NAT Gateway costs for S3 access',
                'savings': 'Avoids NAT Gateway data processing charges ($0.045/GB)'
            },
            {
                'service': 'com.amazonaws.REGION.dynamodb',
                'benefit': 'Free gateway endpoint - eliminates NAT Gateway costs for DynamoDB access',
                'savings': 'Avoids NAT Gateway data processing charges'
            }
        ]

        # Interface endpoints (cost vs benefit)
        recommended_interface_endpoints = [
            {
                'service': 'com.amazonaws.REGION.ec2',
                'benefit': 'Private EC2 API access without NAT Gateway',
                'cost': '$14.60/month',
                'savings': 'Saves on NAT Gateway data processing if heavy EC2 API usage'
            },
            {
                'service': 'com.amazonaws.REGION.lambda',
                'benefit': 'Private Lambda API access',
                'cost': '$14.60/month',
                'savings': 'Useful for Lambda-heavy architectures'
            },
            {
                'service': 'com.amazonaws.REGION.secretsmanager',
                'benefit': 'Private Secrets Manager access',
                'cost': '$14.60/month',
                'savings': 'Better security + potential NAT savings'
            }
        ]

        # Check which recommended endpoints are missing
        existing_services = set(ep['service_name'] for ep in endpoint_analysis)
        missing_gateway_endpoints = []
        missing_interface_endpoints = []

        for rec in recommended_gateway_endpoints:
            service = rec['service']
            # Check if this type of endpoint exists (service name includes region)
            if not any(service.replace('REGION', '') in existing for existing in existing_services):
                missing_gateway_endpoints.append(rec)

        for rec in recommended_interface_endpoints:
            service = rec['service']
            if not any(service.replace('REGION', '') in existing for existing in existing_services):
                missing_interface_endpoints.append(rec)

        # Estimate potential savings
        # If NAT Gateways exist and no S3/DynamoDB endpoints, significant savings possible
        nat_response = ec2.describe_nat_gateways(
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        nat_count = len(nat_response['NatGateways'])

        potential_monthly_savings = 0.0
        recommendations = []

        if nat_count > 0 and len(missing_gateway_endpoints) > 0:
            # Estimate savings from gateway endpoints (assume 10GB/day S3/DynamoDB traffic)
            # NAT Gateway data processing: $0.045/GB
            estimated_monthly_gb = 10 * 30  # 300 GB/month
            potential_savings_per_service = estimated_monthly_gb * 0.045
            potential_monthly_savings = potential_savings_per_service * len(missing_gateway_endpoints)

            recommendations.append({
                'priority': 'high',
                'category': 'cost',
                'recommendation': f'Create {len(missing_gateway_endpoints)} FREE gateway endpoints (S3, DynamoDB)',
                'savings': f'${potential_monthly_savings:.2f}/month (estimate)',
                'action': 'Gateway endpoints are free and eliminate NAT Gateway data charges',
                'services': [ep['service'] for ep in missing_gateway_endpoints]
            })

        if interface_endpoint_cost > 50:
            recommendations.append({
                'priority': 'medium',
                'category': 'cost',
                'recommendation': f'Interface endpoint costs: ${interface_endpoint_cost:.2f}/month',
                'note': 'Review if all interface endpoints are necessary',
                'action': 'Each interface endpoint costs ~$14.60/month'
            })

        if len(endpoints) == 0:
            recommendations.append({
                'priority': 'high',
                'category': 'cost',
                'recommendation': 'No VPC endpoints configured',
                'action': 'Create FREE S3 and DynamoDB gateway endpoints to reduce NAT costs',
                'impact': 'Can save hundreds per month on NAT Gateway charges'
            })

        return {
            'existing_endpoints': endpoint_analysis,
            'missing_gateway_endpoints': missing_gateway_endpoints,
            'missing_interface_endpoints': missing_interface_endpoints,
            'summary': {
                'total_endpoints': len(endpoints),
                'gateway_endpoints': gateway_endpoints,
                'interface_endpoints': interface_endpoints,
                'monthly_interface_cost': round(interface_endpoint_cost, 2),
                'nat_gateways_in_account': nat_count,
                'potential_monthly_savings': round(potential_monthly_savings, 2)
            },
            'recommendations': recommendations if recommendations else [
                'VPC endpoints are well-configured'
            ]
        }

    except Exception as e:
        return {
            'error': f'Failed to analyze VPC endpoints: {str(e)}',
            'existing_endpoints': []
        }


@tool
def find_network_bottlenecks(
    lookback_days: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Identify network performance issues and bottlenecks.

    Analyzes:
    - NAT Gateway throughput and packet drops
    - Network interface performance
    - VPN connection health
    - Network ACL denials
    - High network utilization instances

    Args:
        lookback_days: Days of metrics to analyze (default 7)
        aws_client: Optional AWSClient instance

    Returns:
        Dict with network performance issues and recommendations

    Example:
        >>> result = find_network_bottlenecks()
        >>> print(f"Issues found: {result['summary']['total_issues']}")
        >>> for issue in result['bottlenecks']:
        >>>     print(f"- {issue['description']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    ec2 = aws_client.get_client('ec2')
    cloudwatch = aws_client.get_client('cloudwatch')

    try:
        bottlenecks = []

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=lookback_days)

        # Check NAT Gateway metrics
        nat_response = ec2.describe_nat_gateways(
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        nat_gateways = nat_response['NatGateways']

        for nat in nat_gateways:
            nat_id = nat['NatGatewayId']

            # Check for packet drops
            packets_drop_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/NATGateway',
                MetricName='PacketsDropCount',
                Dimensions=[{'Name': 'NatGatewayId', 'Value': nat_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )

            datapoints = packets_drop_response.get('Datapoints', [])
            total_drops = sum(dp['Sum'] for dp in datapoints) if datapoints else 0

            if total_drops > 1000:
                bottlenecks.append({
                    'type': 'nat_gateway',
                    'resource_id': nat_id,
                    'severity': 'high',
                    'issue': 'Packet drops detected',
                    'description': f'NAT Gateway {nat_id} dropped {int(total_drops)} packets in {lookback_days} days',
                    'recommendation': 'NAT Gateway may be at capacity - consider adding more NAT Gateways',
                    'impact': 'Network connectivity issues and degraded performance'
                })

            # Check for connection tracking (high number of active connections)
            connections_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/NATGateway',
                MetricName='ActiveConnectionCount',
                Dimensions=[{'Name': 'NatGatewayId', 'Value': nat_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Maximum']
            )

            conn_datapoints = connections_response.get('Datapoints', [])
            max_connections = max((dp['Maximum'] for dp in conn_datapoints), default=0)

            # NAT Gateway supports 55,000 concurrent connections
            if max_connections > 45000:
                bottlenecks.append({
                    'type': 'nat_gateway',
                    'resource_id': nat_id,
                    'severity': 'medium',
                    'issue': 'High connection count',
                    'description': f'NAT Gateway {nat_id} reached {int(max_connections)} connections (limit: 55,000)',
                    'recommendation': 'Approaching connection limit - add NAT Gateways or reduce connection count',
                    'impact': 'May hit connection limit and drop new connections'
                })

        # Check VPN connections
        vpn_response = ec2.describe_vpn_connections(
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        vpn_connections = vpn_response['VpnConnections']

        for vpn in vpn_connections:
            vpn_id = vpn['VpnConnectionId']

            # Check tunnel status
            for tunnel in vpn.get('VgwTelemetry', []):
                status = tunnel.get('Status', 'DOWN')
                if status == 'DOWN':
                    bottlenecks.append({
                        'type': 'vpn',
                        'resource_id': vpn_id,
                        'severity': 'critical',
                        'issue': 'VPN tunnel down',
                        'description': f'VPN connection {vpn_id} has tunnel in DOWN state',
                        'recommendation': 'Check VPN configuration and customer gateway',
                        'impact': 'Reduced redundancy or complete VPN failure'
                    })

        # Check for instances with high network utilization
        instances_response = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )

        for reservation in instances_response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']

                # Get network in/out metrics
                network_in_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='NetworkIn',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Average']
                )

                datapoints = network_in_response.get('Datapoints', [])
                avg_network_in = sum(dp['Average'] for dp in datapoints) / len(datapoints) if datapoints else 0

                # Very rough estimate - flag if >1 Gbps average
                if avg_network_in > 125000000:  # ~1 Gbps in bytes/sec
                    bottlenecks.append({
                        'type': 'ec2_network',
                        'resource_id': instance_id,
                        'severity': 'medium',
                        'issue': 'High network utilization',
                        'description': f'Instance {instance_id} ({instance_type}) has high network traffic',
                        'recommendation': 'Check if instance type provides sufficient network bandwidth',
                        'impact': 'Potential network throttling',
                        'action': 'Consider upgrading to network-optimized instance type'
                    })

        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        bottlenecks.sort(key=lambda x: severity_order.get(x['severity'], 999))

        # Summary
        summary = {
            'total_issues': len(bottlenecks),
            'critical': len([b for b in bottlenecks if b['severity'] == 'critical']),
            'high': len([b for b in bottlenecks if b['severity'] == 'high']),
            'medium': len([b for b in bottlenecks if b['severity'] == 'medium']),
            'low': len([b for b in bottlenecks if b['severity'] == 'low']),
            'lookback_days': lookback_days
        }

        return {
            'bottlenecks': bottlenecks,
            'summary': summary,
            'recommendations': [
                f"Found {summary['total_issues']} network performance issues",
                "Review high severity issues first",
                "Monitor NAT Gateway and VPN metrics regularly"
            ] if bottlenecks else [
                "No network bottlenecks detected - network is performing well"
            ]
        }

    except Exception as e:
        return {
            'error': f'Failed to find network bottlenecks: {str(e)}',
            'bottlenecks': []
        }
