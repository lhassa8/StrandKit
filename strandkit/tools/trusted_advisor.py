"""
Trusted Advisor-style checks for StrandKit.

This module replicates key AWS Trusted Advisor checks that are normally
only available with Business/Enterprise Support plans. These checks cover:

Security:
- CloudTrail logging status
- VPC Flow Logs enablement
- AWS Config recording status
- ACM certificate expiration
- Lambda deprecated runtimes

Cost Optimization:
- EC2 instances stopped >30 days
- S3 incomplete multipart uploads
- ECR repositories without lifecycle policies

All functions are decorated with @tool for AWS Strands Agents integration
and can also be used standalone.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from strands import tool
from strandkit.core.aws_client import AWSClient


# =============================================================================
# SECURITY CHECKS
# =============================================================================

@tool
def check_cloudtrail_logging(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check if CloudTrail is enabled and logging management events.

    This replicates the Trusted Advisor "AWS CloudTrail Management Event Logging" check.
    CloudTrail provides visibility into user activity by recording API calls made
    on your account.

    Args:
        aws_client: Optional AWSClient instance for custom credentials/region

    Returns:
        Dict containing:
        - status: 'ok', 'warning', or 'error'
        - trails: List of trails with their status
        - issues: List of identified issues
        - recommendations: Suggested actions

    Example:
        >>> result = check_cloudtrail_logging()
        >>> if result['status'] == 'error':
        ...     print("CloudTrail is not properly configured!")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ct_client = aws_client.get_client('cloudtrail')

        # Get all trails
        response = ct_client.describe_trails(includeShadowTrails=False)
        trails = response.get('trailList', [])

        if not trails:
            return {
                'status': 'error',
                'trails': [],
                'issues': ['No CloudTrail trails configured in this region'],
                'recommendations': [
                    'Create a CloudTrail trail to log API activity',
                    'Enable multi-region trail for comprehensive logging',
                    'Consider using AWS Organizations trail for all accounts'
                ],
                'summary': 'CRITICAL: No CloudTrail logging configured'
            }

        trail_details = []
        issues = []
        has_active_trail = False
        has_multi_region = False

        for trail in trails:
            trail_name = trail.get('Name', 'Unknown')
            trail_arn = trail.get('TrailARN', '')

            # Get trail status
            try:
                status_response = ct_client.get_trail_status(Name=trail_arn)
                is_logging = status_response.get('IsLogging', False)
                latest_delivery = status_response.get('LatestDeliveryTime')
                latest_error = status_response.get('LatestDeliveryError')
            except Exception:
                is_logging = False
                latest_delivery = None
                latest_error = 'Unable to get status'

            is_multi_region = trail.get('IsMultiRegionTrail', False)
            is_org_trail = trail.get('IsOrganizationTrail', False)
            has_log_validation = trail.get('LogFileValidationEnabled', False)
            s3_bucket = trail.get('S3BucketName', 'Not configured')
            kms_key = trail.get('KMSKeyId')

            if is_logging:
                has_active_trail = True
            if is_multi_region:
                has_multi_region = True

            # Check for issues
            trail_issues = []
            if not is_logging:
                trail_issues.append('Trail is not logging')
                issues.append(f'{trail_name}: Trail is not logging')
            if latest_error:
                trail_issues.append(f'Delivery error: {latest_error}')
                issues.append(f'{trail_name}: {latest_error}')
            if not has_log_validation:
                trail_issues.append('Log file validation not enabled')
            if not kms_key:
                trail_issues.append('Logs not encrypted with KMS')

            trail_details.append({
                'name': trail_name,
                'arn': trail_arn,
                'is_logging': is_logging,
                'is_multi_region': is_multi_region,
                'is_organization_trail': is_org_trail,
                'log_file_validation': has_log_validation,
                's3_bucket': s3_bucket,
                'kms_encrypted': kms_key is not None,
                'latest_delivery': str(latest_delivery) if latest_delivery else None,
                'issues': trail_issues
            })

        # Determine overall status
        if not has_active_trail:
            status = 'error'
            issues.append('No trails are actively logging')
        elif not has_multi_region:
            status = 'warning'
            issues.append('No multi-region trail configured - some regions may not be logged')
        elif issues:
            status = 'warning'
        else:
            status = 'ok'

        # Generate recommendations
        recommendations = []
        if not has_active_trail:
            recommendations.append('Enable logging on at least one CloudTrail trail')
        if not has_multi_region:
            recommendations.append('Configure a multi-region trail for comprehensive coverage')
        for trail in trail_details:
            if not trail['log_file_validation']:
                recommendations.append(f"Enable log file validation on '{trail['name']}'")
            if not trail['kms_encrypted']:
                recommendations.append(f"Enable KMS encryption on '{trail['name']}'")

        if not recommendations:
            recommendations.append('CloudTrail is properly configured')

        return {
            'status': status,
            'trails': trail_details,
            'trail_count': len(trail_details),
            'has_active_logging': has_active_trail,
            'has_multi_region': has_multi_region,
            'issues': issues,
            'recommendations': recommendations,
            'summary': f"{'OK' if status == 'ok' else 'ISSUES FOUND'}: {len(trail_details)} trail(s), {len(issues)} issue(s)"
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'trails': [],
            'issues': [f'Error checking CloudTrail: {str(e)}'],
            'recommendations': ['Verify IAM permissions for CloudTrail access'],
            'summary': f'Error: {str(e)}'
        }


@tool
def check_vpc_flow_logs(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check if VPC Flow Logs are enabled for all VPCs.

    VPC Flow Logs capture information about IP traffic going to and from
    network interfaces in your VPC. This is essential for security monitoring
    and troubleshooting.

    Args:
        aws_client: Optional AWSClient instance for custom credentials/region

    Returns:
        Dict containing:
        - status: 'ok', 'warning', or 'error'
        - vpcs: List of VPCs with flow log status
        - vpcs_without_flow_logs: VPCs missing flow logs
        - recommendations: Suggested actions

    Example:
        >>> result = check_vpc_flow_logs()
        >>> for vpc in result['vpcs_without_flow_logs']:
        ...     print(f"VPC {vpc['vpc_id']} needs flow logs!")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ec2_client = aws_client.get_client('ec2')

        # Get all VPCs
        vpcs_response = ec2_client.describe_vpcs()
        vpcs = vpcs_response.get('Vpcs', [])

        if not vpcs:
            return {
                'status': 'ok',
                'vpcs': [],
                'vpcs_without_flow_logs': [],
                'summary': 'No VPCs found in this region',
                'recommendations': []
            }

        # Get all flow logs
        flow_logs_response = ec2_client.describe_flow_logs()
        flow_logs = flow_logs_response.get('FlowLogs', [])

        # Map flow logs to VPCs
        vpc_flow_log_map = {}
        for fl in flow_logs:
            resource_id = fl.get('ResourceId', '')
            if fl.get('FlowLogStatus') == 'ACTIVE':
                if resource_id not in vpc_flow_log_map:
                    vpc_flow_log_map[resource_id] = []
                vpc_flow_log_map[resource_id].append({
                    'flow_log_id': fl.get('FlowLogId'),
                    'destination_type': fl.get('LogDestinationType'),
                    'traffic_type': fl.get('TrafficType'),
                    'status': fl.get('FlowLogStatus')
                })

        vpc_details = []
        vpcs_without_flow_logs = []

        for vpc in vpcs:
            vpc_id = vpc.get('VpcId', '')
            vpc_name = None
            for tag in vpc.get('Tags', []):
                if tag['Key'] == 'Name':
                    vpc_name = tag['Value']
                    break

            is_default = vpc.get('IsDefault', False)
            cidr_block = vpc.get('CidrBlock', '')
            flow_logs_for_vpc = vpc_flow_log_map.get(vpc_id, [])
            has_flow_logs = len(flow_logs_for_vpc) > 0

            vpc_info = {
                'vpc_id': vpc_id,
                'name': vpc_name,
                'cidr_block': cidr_block,
                'is_default': is_default,
                'has_flow_logs': has_flow_logs,
                'flow_logs': flow_logs_for_vpc
            }

            vpc_details.append(vpc_info)

            if not has_flow_logs:
                vpcs_without_flow_logs.append(vpc_info)

        # Determine status
        if not vpcs_without_flow_logs:
            status = 'ok'
        elif len(vpcs_without_flow_logs) == len(vpcs):
            status = 'error'
        else:
            status = 'warning'

        # Generate recommendations
        recommendations = []
        for vpc in vpcs_without_flow_logs:
            vpc_desc = vpc['name'] or vpc['vpc_id']
            recommendations.append(
                f"Enable VPC Flow Logs for {vpc_desc} ({vpc['vpc_id']})"
            )

        if not recommendations:
            recommendations.append('All VPCs have Flow Logs enabled')

        return {
            'status': status,
            'vpcs': vpc_details,
            'total_vpcs': len(vpcs),
            'vpcs_with_flow_logs': len(vpcs) - len(vpcs_without_flow_logs),
            'vpcs_without_flow_logs': vpcs_without_flow_logs,
            'issues': [f"{len(vpcs_without_flow_logs)} VPC(s) without Flow Logs"] if vpcs_without_flow_logs else [],
            'recommendations': recommendations,
            'summary': f"{len(vpcs) - len(vpcs_without_flow_logs)}/{len(vpcs)} VPCs have Flow Logs enabled"
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'vpcs': [],
            'vpcs_without_flow_logs': [],
            'summary': f'Error: {str(e)}',
            'recommendations': ['Verify IAM permissions for EC2/VPC access']
        }


@tool
def check_config_status(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check if AWS Config is enabled and recording.

    AWS Config provides a detailed view of the configuration of AWS resources
    in your account. This is essential for compliance, security analysis,
    and change tracking.

    Args:
        aws_client: Optional AWSClient instance for custom credentials/region

    Returns:
        Dict containing:
        - status: 'ok', 'warning', or 'error'
        - recorders: List of Config recorders with status
        - delivery_channels: Delivery channel configuration
        - recommendations: Suggested actions

    Example:
        >>> result = check_config_status()
        >>> if result['status'] != 'ok':
        ...     print("AWS Config needs attention!")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        config_client = aws_client.get_client('config')

        # Get configuration recorders
        recorders_response = config_client.describe_configuration_recorders()
        recorders = recorders_response.get('ConfigurationRecorders', [])

        # Get recorder status
        recorder_status_response = config_client.describe_configuration_recorder_status()
        recorder_statuses = {
            s['name']: s for s in recorder_status_response.get('ConfigurationRecordersStatus', [])
        }

        # Get delivery channels
        channels_response = config_client.describe_delivery_channels()
        channels = channels_response.get('DeliveryChannels', [])

        # Get delivery channel status
        channel_status_response = config_client.describe_delivery_channel_status()
        channel_statuses = {
            s['name']: s for s in channel_status_response.get('DeliveryChannelsStatus', [])
        }

        if not recorders:
            return {
                'status': 'error',
                'recorders': [],
                'delivery_channels': [],
                'issues': ['No AWS Config recorder configured'],
                'recommendations': [
                    'Enable AWS Config to track resource configurations',
                    'Configure a delivery channel to store configuration history',
                    'Consider enabling Config rules for compliance checking'
                ],
                'summary': 'CRITICAL: AWS Config is not configured'
            }

        recorder_details = []
        issues = []
        has_active_recorder = False
        is_recording_all = False

        for recorder in recorders:
            name = recorder.get('name', 'Unknown')
            role_arn = recorder.get('roleARN', '')
            recording_group = recorder.get('recordingGroup', {})
            all_supported = recording_group.get('allSupported', False)
            include_global = recording_group.get('includeGlobalResourceTypes', False)

            status = recorder_statuses.get(name, {})
            is_recording = status.get('recording', False)
            last_status = status.get('lastStatus', 'Unknown')

            if is_recording:
                has_active_recorder = True
            if all_supported:
                is_recording_all = True

            recorder_issues = []
            if not is_recording:
                recorder_issues.append('Recorder is not recording')
                issues.append(f'{name}: Recorder is not active')
            if last_status == 'FAILURE':
                recorder_issues.append(f'Last status: {last_status}')
                issues.append(f'{name}: Recording failed')
            if not all_supported:
                recorder_issues.append('Not recording all resource types')
            if not include_global:
                recorder_issues.append('Not recording global resources (IAM, etc.)')

            recorder_details.append({
                'name': name,
                'is_recording': is_recording,
                'last_status': last_status,
                'all_supported': all_supported,
                'include_global_resources': include_global,
                'role_arn': role_arn,
                'issues': recorder_issues
            })

        channel_details = []
        for channel in channels:
            name = channel.get('name', 'Unknown')
            s3_bucket = channel.get('s3BucketName', 'Not configured')
            sns_topic = channel.get('snsTopicARN')

            status = channel_statuses.get(name, {})
            last_success = status.get('configHistoryDeliveryInfo', {}).get('lastSuccessfulTime')
            last_error = status.get('configHistoryDeliveryInfo', {}).get('lastErrorMessage')

            if last_error:
                issues.append(f'Delivery channel {name}: {last_error}')

            channel_details.append({
                'name': name,
                's3_bucket': s3_bucket,
                'sns_topic': sns_topic,
                'last_successful_delivery': str(last_success) if last_success else None,
                'last_error': last_error
            })

        # Determine status
        if not has_active_recorder:
            status = 'error'
        elif not is_recording_all or issues:
            status = 'warning'
        else:
            status = 'ok'

        # Generate recommendations
        recommendations = []
        if not has_active_recorder:
            recommendations.append('Start the AWS Config recorder')
        if not is_recording_all:
            recommendations.append('Configure recorder to capture all resource types')
        for recorder in recorder_details:
            if not recorder['include_global_resources']:
                recommendations.append(f"Enable global resource recording for '{recorder['name']}'")

        if not recommendations:
            recommendations.append('AWS Config is properly configured')

        return {
            'status': status,
            'recorders': recorder_details,
            'delivery_channels': channel_details,
            'has_active_recorder': has_active_recorder,
            'is_recording_all_resources': is_recording_all,
            'issues': issues,
            'recommendations': recommendations,
            'summary': f"{'OK' if status == 'ok' else 'ISSUES FOUND'}: {len(recorder_details)} recorder(s), {len(issues)} issue(s)"
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'recorders': [],
            'delivery_channels': [],
            'issues': [f'Error checking AWS Config: {str(e)}'],
            'recommendations': ['Verify IAM permissions for Config access'],
            'summary': f'Error: {str(e)}'
        }


@tool
def check_certificate_expiration(
    days_warning: int = 30,
    days_critical: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check for expiring or expired ACM certificates.

    This replicates the Trusted Advisor certificate expiration checks.
    Expired certificates can cause service outages and security warnings.

    Args:
        days_warning: Days before expiration to warn (default: 30)
        days_critical: Days before expiration for critical alert (default: 7)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - status: 'ok', 'warning', or 'error'
        - certificates: List of certificates with expiration status
        - expiring_soon: Certificates expiring within warning period
        - expired: Already expired certificates
        - recommendations: Suggested actions

    Example:
        >>> result = check_certificate_expiration(days_warning=45)
        >>> for cert in result['expiring_soon']:
        ...     print(f"Certificate {cert['domain']} expires in {cert['days_until_expiry']} days")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        acm_client = aws_client.get_client('acm')

        # List all certificates
        certificates = []
        paginator = acm_client.get_paginator('list_certificates')

        for page in paginator.paginate():
            for cert_summary in page.get('CertificateSummaryList', []):
                cert_arn = cert_summary.get('CertificateArn')

                # Get certificate details
                cert_detail = acm_client.describe_certificate(CertificateArn=cert_arn)
                cert = cert_detail.get('Certificate', {})

                domain = cert.get('DomainName', 'Unknown')
                status = cert.get('Status', 'Unknown')
                cert_type = cert.get('Type', 'Unknown')
                not_after = cert.get('NotAfter')
                in_use_by = cert.get('InUseBy', [])

                # Calculate days until expiry
                days_until_expiry = None
                expiry_status = 'unknown'

                if not_after:
                    now = datetime.now(timezone.utc)
                    if not_after.tzinfo is None:
                        not_after = not_after.replace(tzinfo=timezone.utc)
                    delta = not_after - now
                    days_until_expiry = delta.days

                    if days_until_expiry < 0:
                        expiry_status = 'expired'
                    elif days_until_expiry <= days_critical:
                        expiry_status = 'critical'
                    elif days_until_expiry <= days_warning:
                        expiry_status = 'warning'
                    else:
                        expiry_status = 'ok'

                certificates.append({
                    'arn': cert_arn,
                    'domain': domain,
                    'status': status,
                    'type': cert_type,
                    'not_after': str(not_after) if not_after else None,
                    'days_until_expiry': days_until_expiry,
                    'expiry_status': expiry_status,
                    'in_use_by': in_use_by,
                    'is_in_use': len(in_use_by) > 0
                })

        # Categorize certificates
        expired = [c for c in certificates if c['expiry_status'] == 'expired']
        critical = [c for c in certificates if c['expiry_status'] == 'critical']
        warning = [c for c in certificates if c['expiry_status'] == 'warning']
        expiring_soon = critical + warning

        # Determine overall status
        if expired:
            status = 'error'
        elif critical:
            status = 'error'
        elif warning:
            status = 'warning'
        else:
            status = 'ok'

        # Generate issues and recommendations
        issues = []
        recommendations = []

        for cert in expired:
            issues.append(f"EXPIRED: {cert['domain']} expired {abs(cert['days_until_expiry'])} days ago")
            if cert['is_in_use']:
                recommendations.append(f"URGENT: Renew expired certificate for {cert['domain']} - currently in use!")
            else:
                recommendations.append(f"Delete or renew expired certificate for {cert['domain']}")

        for cert in critical:
            issues.append(f"CRITICAL: {cert['domain']} expires in {cert['days_until_expiry']} days")
            recommendations.append(f"Renew certificate for {cert['domain']} immediately")

        for cert in warning:
            issues.append(f"WARNING: {cert['domain']} expires in {cert['days_until_expiry']} days")
            recommendations.append(f"Plan renewal for {cert['domain']}")

        if not issues:
            recommendations.append('All certificates are valid and not expiring soon')

        return {
            'status': status,
            'certificates': certificates,
            'total_certificates': len(certificates),
            'expired': expired,
            'expired_count': len(expired),
            'expiring_soon': expiring_soon,
            'expiring_soon_count': len(expiring_soon),
            'issues': issues,
            'recommendations': recommendations,
            'summary': f"{len(certificates)} certificate(s): {len(expired)} expired, {len(expiring_soon)} expiring soon"
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'certificates': [],
            'expired': [],
            'expiring_soon': [],
            'issues': [f'Error checking certificates: {str(e)}'],
            'recommendations': ['Verify IAM permissions for ACM access'],
            'summary': f'Error: {str(e)}'
        }


@tool
def check_lambda_runtimes(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check for Lambda functions using deprecated or soon-to-be deprecated runtimes.

    This replicates the Trusted Advisor "AWS Lambda Functions Using Deprecated Runtimes" check.
    Deprecated runtimes don't receive security updates and may stop working.

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - status: 'ok', 'warning', or 'error'
        - functions: List of functions with runtime status
        - deprecated_functions: Functions using deprecated runtimes
        - recommendations: Suggested actions

    Example:
        >>> result = check_lambda_runtimes()
        >>> for func in result['deprecated_functions']:
        ...     print(f"{func['name']} uses deprecated {func['runtime']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    # Define runtime status (as of late 2024)
    # https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
    RUNTIME_STATUS = {
        # Active runtimes
        'python3.12': 'supported',
        'python3.11': 'supported',
        'python3.10': 'supported',
        'python3.9': 'supported',
        'nodejs20.x': 'supported',
        'nodejs18.x': 'supported',
        'java21': 'supported',
        'java17': 'supported',
        'java11': 'supported',
        'dotnet8': 'supported',
        'dotnet6': 'supported',
        'ruby3.3': 'supported',
        'ruby3.2': 'supported',
        'provided.al2023': 'supported',
        'provided.al2': 'supported',

        # Deprecating soon
        'python3.8': 'deprecating',  # Oct 2024
        'nodejs16.x': 'deprecating',  # Jun 2024

        # Deprecated
        'python3.7': 'deprecated',
        'python3.6': 'deprecated',
        'python2.7': 'deprecated',
        'nodejs14.x': 'deprecated',
        'nodejs12.x': 'deprecated',
        'nodejs10.x': 'deprecated',
        'nodejs8.10': 'deprecated',
        'java8': 'deprecated',
        'java8.al2': 'deprecating',
        'dotnet5.0': 'deprecated',
        'dotnetcore3.1': 'deprecated',
        'dotnetcore2.1': 'deprecated',
        'ruby2.7': 'deprecated',
        'ruby2.5': 'deprecated',
        'go1.x': 'deprecated',
        'provided': 'deprecated',
    }

    UPGRADE_PATHS = {
        'python3.8': 'python3.12',
        'python3.7': 'python3.12',
        'python3.6': 'python3.12',
        'python2.7': 'python3.12',
        'nodejs16.x': 'nodejs20.x',
        'nodejs14.x': 'nodejs20.x',
        'nodejs12.x': 'nodejs20.x',
        'nodejs10.x': 'nodejs20.x',
        'nodejs8.10': 'nodejs20.x',
        'java8': 'java21',
        'java8.al2': 'java21',
        'dotnetcore3.1': 'dotnet8',
        'dotnetcore2.1': 'dotnet8',
        'dotnet5.0': 'dotnet8',
        'ruby2.7': 'ruby3.3',
        'ruby2.5': 'ruby3.3',
        'go1.x': 'provided.al2023',
        'provided': 'provided.al2023',
    }

    try:
        lambda_client = aws_client.get_client('lambda')

        functions = []
        deprecated_functions = []
        deprecating_functions = []

        # List all functions
        paginator = lambda_client.get_paginator('list_functions')

        for page in paginator.paginate():
            for func in page.get('Functions', []):
                func_name = func.get('FunctionName', 'Unknown')
                runtime = func.get('Runtime', 'Unknown')
                last_modified = func.get('LastModified', '')
                memory = func.get('MemorySize', 0)
                timeout = func.get('Timeout', 0)
                code_size = func.get('CodeSize', 0)

                runtime_status = RUNTIME_STATUS.get(runtime, 'unknown')
                upgrade_to = UPGRADE_PATHS.get(runtime)

                func_info = {
                    'name': func_name,
                    'runtime': runtime,
                    'runtime_status': runtime_status,
                    'upgrade_to': upgrade_to,
                    'last_modified': last_modified,
                    'memory_mb': memory,
                    'timeout_seconds': timeout,
                    'code_size_bytes': code_size
                }

                functions.append(func_info)

                if runtime_status == 'deprecated':
                    deprecated_functions.append(func_info)
                elif runtime_status == 'deprecating':
                    deprecating_functions.append(func_info)

        # Determine status
        if deprecated_functions:
            status = 'error'
        elif deprecating_functions:
            status = 'warning'
        else:
            status = 'ok'

        # Generate issues and recommendations
        issues = []
        recommendations = []

        for func in deprecated_functions:
            issues.append(f"DEPRECATED: {func['name']} uses {func['runtime']}")
            if func['upgrade_to']:
                recommendations.append(f"Upgrade {func['name']} from {func['runtime']} to {func['upgrade_to']}")
            else:
                recommendations.append(f"Upgrade {func['name']} from deprecated {func['runtime']}")

        for func in deprecating_functions:
            issues.append(f"DEPRECATING: {func['name']} uses {func['runtime']} (deprecating soon)")
            if func['upgrade_to']:
                recommendations.append(f"Plan upgrade of {func['name']} from {func['runtime']} to {func['upgrade_to']}")

        if not issues:
            recommendations.append('All Lambda functions use supported runtimes')

        # Summary by runtime
        runtime_summary = {}
        for func in functions:
            rt = func['runtime']
            if rt not in runtime_summary:
                runtime_summary[rt] = {'count': 0, 'status': func['runtime_status']}
            runtime_summary[rt]['count'] += 1

        return {
            'status': status,
            'functions': functions,
            'total_functions': len(functions),
            'deprecated_functions': deprecated_functions,
            'deprecated_count': len(deprecated_functions),
            'deprecating_functions': deprecating_functions,
            'deprecating_count': len(deprecating_functions),
            'runtime_summary': runtime_summary,
            'issues': issues,
            'recommendations': recommendations,
            'summary': f"{len(functions)} function(s): {len(deprecated_functions)} deprecated, {len(deprecating_functions)} deprecating"
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'functions': [],
            'deprecated_functions': [],
            'deprecating_functions': [],
            'issues': [f'Error checking Lambda functions: {str(e)}'],
            'recommendations': ['Verify IAM permissions for Lambda access'],
            'summary': f'Error: {str(e)}'
        }


# =============================================================================
# COST OPTIMIZATION CHECKS
# =============================================================================

@tool
def check_stopped_ec2_instances(
    days_threshold: int = 30,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check for EC2 instances that have been stopped for extended periods.

    This replicates the Trusted Advisor "Amazon EC2 instances stopped" check.
    Stopped instances still incur costs for attached EBS volumes and Elastic IPs.

    Args:
        days_threshold: Number of days stopped to flag (default: 30)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - status: 'ok', 'warning', or 'error'
        - stopped_instances: List of stopped instances with details
        - total_monthly_waste: Estimated monthly cost of stopped instance storage
        - recommendations: Suggested actions

    Example:
        >>> result = check_stopped_ec2_instances(days_threshold=14)
        >>> print(f"Potential monthly savings: ${result['total_monthly_waste']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    # EBS pricing for cost estimation
    EBS_PRICING = {'gp3': 0.08, 'gp2': 0.10, 'io1': 0.125, 'io2': 0.125, 'st1': 0.045, 'sc1': 0.015}

    try:
        ec2_client = aws_client.get_client('ec2')

        # Get stopped instances
        response = ec2_client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}]
        )

        stopped_instances = []
        total_monthly_waste = 0.0

        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance.get('InstanceId')
                instance_type = instance.get('InstanceType')

                # Get instance name
                name = None
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break

                # Get state transition time (when it was stopped)
                state_transition = instance.get('StateTransitionReason', '')
                # Parse date from reason like "User initiated (2024-01-15 10:30:00 GMT)"
                stopped_date = None
                days_stopped = None

                if 'User initiated' in state_transition:
                    try:
                        import re
                        date_match = re.search(r'\((\d{4}-\d{2}-\d{2})', state_transition)
                        if date_match:
                            stopped_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                            days_stopped = (datetime.now() - stopped_date).days
                    except Exception:
                        pass

                # Calculate EBS storage cost
                ebs_cost = 0.0
                volumes = []
                for bdm in instance.get('BlockDeviceMappings', []):
                    if 'Ebs' in bdm:
                        vol_id = bdm['Ebs'].get('VolumeId')
                        try:
                            vol_response = ec2_client.describe_volumes(VolumeIds=[vol_id])
                            if vol_response['Volumes']:
                                vol = vol_response['Volumes'][0]
                                size = vol.get('Size', 0)
                                vol_type = vol.get('VolumeType', 'gp2')
                                rate = EBS_PRICING.get(vol_type, 0.10)
                                vol_cost = size * rate
                                ebs_cost += vol_cost
                                volumes.append({
                                    'volume_id': vol_id,
                                    'size_gb': size,
                                    'type': vol_type,
                                    'monthly_cost': round(vol_cost, 2)
                                })
                        except Exception:
                            pass

                # Only flag if stopped longer than threshold (or unknown)
                if days_stopped is None or days_stopped >= days_threshold:
                    total_monthly_waste += ebs_cost

                    stopped_instances.append({
                        'instance_id': instance_id,
                        'name': name,
                        'instance_type': instance_type,
                        'state_transition_reason': state_transition,
                        'stopped_date': str(stopped_date) if stopped_date else 'Unknown',
                        'days_stopped': days_stopped,
                        'volumes': volumes,
                        'monthly_ebs_cost': round(ebs_cost, 2),
                        'annual_ebs_cost': round(ebs_cost * 12, 2)
                    })

        # Determine status
        if not stopped_instances:
            status = 'ok'
        elif total_monthly_waste > 100:
            status = 'error'
        else:
            status = 'warning'

        # Generate recommendations
        issues = []
        recommendations = []

        for inst in stopped_instances:
            days = inst['days_stopped']
            days_str = f"{days} days" if days else "unknown period"
            issues.append(f"{inst['name'] or inst['instance_id']} stopped for {days_str} (${inst['monthly_ebs_cost']:.2f}/month in EBS)")

            if inst['monthly_ebs_cost'] > 10:
                recommendations.append(
                    f"Terminate {inst['name'] or inst['instance_id']} or snapshot and delete volumes "
                    f"(saves ${inst['monthly_ebs_cost']:.2f}/month)"
                )

        if total_monthly_waste > 0:
            recommendations.insert(0, f"Total potential savings: ${total_monthly_waste:.2f}/month (${total_monthly_waste * 12:.2f}/year)")

        if not issues:
            recommendations.append('No instances stopped longer than threshold')

        return {
            'status': status,
            'stopped_instances': stopped_instances,
            'stopped_count': len(stopped_instances),
            'days_threshold': days_threshold,
            'total_monthly_waste': round(total_monthly_waste, 2),
            'total_annual_waste': round(total_monthly_waste * 12, 2),
            'issues': issues,
            'recommendations': recommendations,
            'summary': f"{len(stopped_instances)} instance(s) stopped >{days_threshold} days, ${total_monthly_waste:.2f}/month waste"
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'stopped_instances': [],
            'total_monthly_waste': 0,
            'issues': [f'Error checking stopped instances: {str(e)}'],
            'recommendations': ['Verify IAM permissions for EC2 access'],
            'summary': f'Error: {str(e)}'
        }


@tool
def check_s3_incomplete_uploads(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check for S3 buckets with incomplete multipart uploads.

    This replicates the Trusted Advisor "Amazon S3 Incomplete Multipart Upload Abort Configuration" check.
    Incomplete multipart uploads consume storage but are often forgotten, wasting money.

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - status: 'ok', 'warning', or 'error'
        - buckets: List of buckets with incomplete upload info
        - buckets_without_lifecycle: Buckets without abort rules
        - recommendations: Suggested actions

    Example:
        >>> result = check_s3_incomplete_uploads()
        >>> for bucket in result['buckets_without_lifecycle']:
        ...     print(f"Add lifecycle rule to {bucket['name']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3_client = aws_client.get_client('s3')

        # List all buckets
        buckets_response = s3_client.list_buckets()
        all_buckets = buckets_response.get('Buckets', [])

        buckets = []
        buckets_without_lifecycle = []
        total_incomplete_uploads = 0

        for bucket in all_buckets:
            bucket_name = bucket['Name']

            # Check for lifecycle rule that aborts incomplete uploads
            has_abort_rule = False
            abort_days = None

            try:
                lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                for rule in lifecycle.get('Rules', []):
                    if rule.get('Status') == 'Enabled':
                        abort_config = rule.get('AbortIncompleteMultipartUpload')
                        if abort_config:
                            has_abort_rule = True
                            abort_days = abort_config.get('DaysAfterInitiation')
                            break
            except s3_client.exceptions.ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchLifecycleConfiguration':
                    pass  # Other error, skip

            # Count incomplete multipart uploads (sample - can be expensive for large buckets)
            incomplete_count = 0
            try:
                uploads = s3_client.list_multipart_uploads(Bucket=bucket_name, MaxUploads=100)
                incomplete_count = len(uploads.get('Uploads', []))
                total_incomplete_uploads += incomplete_count
            except Exception:
                pass

            bucket_info = {
                'name': bucket_name,
                'has_abort_lifecycle_rule': has_abort_rule,
                'abort_after_days': abort_days,
                'incomplete_uploads_sample': incomplete_count
            }

            buckets.append(bucket_info)

            if not has_abort_rule:
                buckets_without_lifecycle.append(bucket_info)

        # Determine status
        if len(buckets_without_lifecycle) == len(buckets) and len(buckets) > 0:
            status = 'error'
        elif buckets_without_lifecycle:
            status = 'warning'
        else:
            status = 'ok'

        # Generate recommendations
        issues = []
        recommendations = []

        if buckets_without_lifecycle:
            issues.append(f"{len(buckets_without_lifecycle)} bucket(s) without incomplete upload abort rule")

            # Provide sample lifecycle rule
            recommendations.append(
                "Add lifecycle rule to abort incomplete multipart uploads after 7 days. "
                "Example AWS CLI command:\n"
                "aws s3api put-bucket-lifecycle-configuration --bucket BUCKET_NAME "
                "--lifecycle-configuration '{\"Rules\":[{\"ID\":\"AbortIncompleteMultipartUpload\","
                "\"Status\":\"Enabled\",\"Filter\":{},\"AbortIncompleteMultipartUpload\":{\"DaysAfterInitiation\":7}}]}'"
            )

            for bucket in buckets_without_lifecycle[:5]:  # List first 5
                recommendations.append(f"Configure abort rule for: {bucket['name']}")

            if len(buckets_without_lifecycle) > 5:
                recommendations.append(f"... and {len(buckets_without_lifecycle) - 5} more buckets")

        if total_incomplete_uploads > 0:
            issues.append(f"{total_incomplete_uploads} incomplete multipart uploads found (sampled)")

        if not issues:
            recommendations.append('All buckets have lifecycle rules to abort incomplete uploads')

        return {
            'status': status,
            'buckets': buckets,
            'total_buckets': len(buckets),
            'buckets_without_lifecycle': buckets_without_lifecycle,
            'buckets_without_lifecycle_count': len(buckets_without_lifecycle),
            'total_incomplete_uploads': total_incomplete_uploads,
            'issues': issues,
            'recommendations': recommendations,
            'summary': f"{len(buckets_without_lifecycle)}/{len(buckets)} buckets missing abort lifecycle rule"
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'buckets': [],
            'buckets_without_lifecycle': [],
            'issues': [f'Error checking S3 buckets: {str(e)}'],
            'recommendations': ['Verify IAM permissions for S3 access'],
            'summary': f'Error: {str(e)}'
        }


@tool
def run_all_trusted_advisor_checks(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run all Trusted Advisor-style checks and return a consolidated report.

    This provides a comprehensive security and cost optimization assessment
    similar to AWS Trusted Advisor, but without requiring Business/Enterprise support.

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - overall_status: 'ok', 'warning', or 'error'
        - security_checks: Results of security-related checks
        - cost_checks: Results of cost optimization checks
        - summary: High-level summary of findings
        - total_issues: Count of all issues found

    Example:
        >>> report = run_all_trusted_advisor_checks()
        >>> print(f"Overall status: {report['overall_status']}")
        >>> print(f"Total issues: {report['total_issues']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    results = {
        'security_checks': {},
        'cost_checks': {},
        'issues_by_severity': {'error': [], 'warning': []},
        'recommendations': []
    }

    # Run security checks
    security_checks = [
        ('cloudtrail_logging', check_cloudtrail_logging),
        ('vpc_flow_logs', check_vpc_flow_logs),
        ('config_status', check_config_status),
        ('certificate_expiration', check_certificate_expiration),
        ('lambda_runtimes', check_lambda_runtimes),
    ]

    for check_name, check_func in security_checks:
        try:
            result = check_func(aws_client=aws_client)
            results['security_checks'][check_name] = result

            if result.get('status') == 'error':
                results['issues_by_severity']['error'].extend(result.get('issues', []))
            elif result.get('status') == 'warning':
                results['issues_by_severity']['warning'].extend(result.get('issues', []))

            results['recommendations'].extend(result.get('recommendations', []))
        except Exception as e:
            results['security_checks'][check_name] = {
                'status': 'error',
                'error': str(e)
            }

    # Run cost checks
    cost_checks = [
        ('stopped_ec2_instances', check_stopped_ec2_instances),
        ('s3_incomplete_uploads', check_s3_incomplete_uploads),
    ]

    for check_name, check_func in cost_checks:
        try:
            result = check_func(aws_client=aws_client)
            results['cost_checks'][check_name] = result

            if result.get('status') == 'error':
                results['issues_by_severity']['error'].extend(result.get('issues', []))
            elif result.get('status') == 'warning':
                results['issues_by_severity']['warning'].extend(result.get('issues', []))

            results['recommendations'].extend(result.get('recommendations', []))
        except Exception as e:
            results['cost_checks'][check_name] = {
                'status': 'error',
                'error': str(e)
            }

    # Calculate totals
    total_errors = len(results['issues_by_severity']['error'])
    total_warnings = len(results['issues_by_severity']['warning'])
    total_issues = total_errors + total_warnings

    # Determine overall status
    if total_errors > 0:
        overall_status = 'error'
    elif total_warnings > 0:
        overall_status = 'warning'
    else:
        overall_status = 'ok'

    # Build summary
    security_status = {name: r.get('status', 'error') for name, r in results['security_checks'].items()}
    cost_status = {name: r.get('status', 'error') for name, r in results['cost_checks'].items()}

    return {
        'overall_status': overall_status,
        'security_checks': results['security_checks'],
        'cost_checks': results['cost_checks'],
        'security_summary': security_status,
        'cost_summary': cost_status,
        'total_issues': total_issues,
        'errors_count': total_errors,
        'warnings_count': total_warnings,
        'issues_by_severity': results['issues_by_severity'],
        'top_recommendations': results['recommendations'][:10],  # Top 10
        'summary': f"Checked {len(security_checks)} security and {len(cost_checks)} cost items: "
                   f"{total_errors} errors, {total_warnings} warnings"
    }


# Export all tools
__all__ = [
    'check_cloudtrail_logging',
    'check_vpc_flow_logs',
    'check_config_status',
    'check_certificate_expiration',
    'check_lambda_runtimes',
    'check_stopped_ec2_instances',
    'check_s3_incomplete_uploads',
    'run_all_trusted_advisor_checks',
]
