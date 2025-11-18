"""
High-level orchestrator tools for StrandKit.

These tools coordinate multiple granular tools to accomplish common workflows.
Agents should prefer these over calling individual tools directly.

This solves the "too many tools" problem by providing clear, task-focused
entry points that internally use the right combination of granular tools.

Usage:
    from strandkit import audit_security, optimize_costs

    # High-level: Agent calls one tool
    security_report = audit_security()

    # Instead of: Agent trying to pick from 11 IAM/security tools
"""

from typing import Dict, Any, Optional, List
from strands import tool
from strandkit.core.aws_client import AWSClient


@tool
def audit_security(
    include_iam: bool = True,
    include_s3: bool = True,
    include_ec2: bool = True,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Comprehensive AWS security audit across IAM, S3, and EC2.

    This orchestrates multiple security tools to provide a complete
    security assessment of your AWS account.

    Args:
        include_iam: Include IAM security checks (default: True)
        include_s3: Include S3 security checks (default: True)
        include_ec2: Include EC2 security group checks (default: True)
        aws_client: Optional AWS client (auto-created if not provided)

    Returns:
        Unified security report with findings, risks, and recommendations

    Example:
        >>> report = audit_security()
        >>> print(f"Critical risks: {report['summary']['critical_risks']}")
        >>> for finding in report['findings']:
        ...     print(f"{finding['severity']}: {finding['title']}")
    """
    from strandkit.tools.iam import find_overpermissive_roles
    from strandkit.tools.iam_security import (
        analyze_mfa_compliance,
        detect_privilege_escalation_paths
    )
    from strandkit.tools.s3 import find_public_buckets
    from strandkit.tools.ec2 import find_overpermissive_security_groups

    findings = []
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0

    # IAM Security
    if include_iam:
        # Check IAM roles
        iam_roles = find_overpermissive_roles(aws_client=aws_client)
        if 'summary' in iam_roles:
            critical_count += iam_roles['summary'].get('critical', 0)
            high_count += iam_roles['summary'].get('high', 0)
            medium_count += iam_roles['summary'].get('medium', 0)

            for role in iam_roles.get('overpermissive_roles', [])[:5]:  # Top 5
                findings.append({
                    'category': 'IAM',
                    'type': 'Overpermissive Role',
                    'severity': role['risk_level'],
                    'title': f"IAM Role: {role['role_name']}",
                    'details': role.get('risk_factors', []),
                    'resource': role['role_name']
                })

        # Check MFA compliance
        mfa = analyze_mfa_compliance(aws_client=aws_client)
        if not mfa.get('root_mfa_status', {}).get('enabled', True):
            findings.append({
                'category': 'IAM',
                'type': 'MFA Compliance',
                'severity': 'critical',
                'title': 'Root account MFA not enabled',
                'details': ['Root account should have MFA enabled'],
                'resource': 'root-account'
            })
            critical_count += 1

        # Check privilege escalation
        escalation = detect_privilege_escalation_paths(aws_client=aws_client)
        if 'summary' in escalation:
            critical_count += escalation['summary'].get('critical_severity', 0)
            high_count += escalation['summary'].get('high_severity', 0)

    # S3 Security
    if include_s3:
        s3_public = find_public_buckets(aws_client=aws_client)
        if 'summary' in s3_public:
            critical_count += s3_public['summary'].get('critical', 0)
            high_count += s3_public['summary'].get('high', 0)

            for bucket in s3_public.get('public_buckets', [])[:5]:  # Top 5
                findings.append({
                    'category': 'S3',
                    'type': 'Public Bucket',
                    'severity': bucket['risk_level'],
                    'title': f"S3 Bucket: {bucket['bucket_name']}",
                    'details': bucket.get('public_reason', []),
                    'resource': bucket['bucket_name']
                })

    # EC2 Security Groups
    if include_ec2:
        sg_scan = find_overpermissive_security_groups(aws_client=aws_client)
        if 'summary' in sg_scan:
            critical_count += sg_scan['summary'].get('critical', 0)
            high_count += sg_scan['summary'].get('high', 0)
            medium_count += sg_scan['summary'].get('medium', 0)

            for sg in sg_scan.get('risky_groups', [])[:5]:  # Top 5
                if sg['risk_level'] in ['critical', 'high']:
                    findings.append({
                        'category': 'EC2',
                        'type': 'Overpermissive Security Group',
                        'severity': sg['risk_level'],
                        'title': f"Security Group: {sg['group_name']}",
                        'details': sg.get('risk_factors', []),
                        'resource': sg['group_id']
                    })

    # Generate recommendations
    recommendations = []
    if critical_count > 0:
        recommendations.append(f"🚨 URGENT: {critical_count} critical security issue(s) require immediate attention")
    if high_count > 0:
        recommendations.append(f"⚠️  {high_count} high-risk issue(s) should be addressed soon")
    if critical_count == 0 and high_count == 0:
        recommendations.append("✅ No critical or high-risk security issues found")

    return {
        'summary': {
            'total_findings': len(findings),
            'critical_risks': critical_count,
            'high_risks': high_count,
            'medium_risks': medium_count,
            'low_risks': low_count,
            'areas_scanned': {
                'iam': include_iam,
                's3': include_s3,
                'ec2': include_ec2
            }
        },
        'findings': sorted(findings, key=lambda x: {
            'critical': 0, 'high': 1, 'medium': 2, 'low': 3
        }.get(x['severity'], 4)),
        'recommendations': recommendations,
        'next_steps': [
            "Review critical and high-risk findings immediately",
            "Use analyze_role() for detailed IAM role analysis",
            "Use analyze_security_group() for detailed SG analysis",
            "Enable root account MFA if not already enabled"
        ] if (critical_count > 0 or high_count > 0) else [
            "Continue monitoring with regular security audits",
            "Review medium and low-risk findings when time permits"
        ]
    }


@tool
def optimize_costs(
    include_waste: bool = True,
    include_idle: bool = True,
    include_storage: bool = True,
    min_impact: float = 10.0,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Find all AWS cost optimization opportunities across services.

    This orchestrates multiple cost analysis tools to identify waste,
    idle resources, and optimization opportunities.

    Args:
        include_waste: Check for zombie/unused resources (default: True)
        include_idle: Check for idle/underutilized resources (default: True)
        include_storage: Check for storage waste (snapshots, S3) (default: True)
        min_impact: Minimum monthly savings to report (default: $10)
        aws_client: Optional AWS client (auto-created if not provided)

    Returns:
        Unified cost optimization report with savings opportunities

    Example:
        >>> report = optimize_costs(min_impact=50.0)
        >>> print(f"Total savings: ${report['total_monthly_savings']:.2f}")
        >>> for opp in report['top_opportunities']:
        ...     print(f"${opp['monthly_savings']:.2f}: {opp['title']}")
    """
    from strandkit.tools.cost_waste import (
        find_zombie_resources,
        analyze_idle_resources,
        analyze_snapshot_waste
    )
    from strandkit.tools.s3 import find_unused_buckets
    from strandkit.tools.ec2 import find_unused_resources

    opportunities = []
    total_savings = 0.0

    # Find zombie resources (forgotten resources)
    if include_waste:
        zombies = find_zombie_resources(aws_client=aws_client)
        if 'summary' in zombies:
            zombie_savings = zombies['summary'].get('total_monthly_waste', 0)
            if zombie_savings >= min_impact:
                total_savings += zombie_savings
                opportunities.append({
                    'category': 'Zombie Resources',
                    'title': 'Delete forgotten resources',
                    'monthly_savings': zombie_savings,
                    'annual_savings': zombie_savings * 12,
                    'effort': 'low',
                    'risk': 'low',
                    'action': f"Delete {zombies['summary'].get('total_zombies', 0)} zombie resources",
                    'details': zombies.get('recommendations', [])[:3]
                })

        # EC2 unused resources
        ec2_unused = find_unused_resources(aws_client=aws_client)
        if 'total_potential_savings' in ec2_unused:
            ec2_savings = ec2_unused['total_potential_savings']
            if ec2_savings >= min_impact:
                total_savings += ec2_savings
                opportunities.append({
                    'category': 'EC2 Waste',
                    'title': 'Clean up unused EC2 resources',
                    'monthly_savings': ec2_savings,
                    'annual_savings': ec2_savings * 12,
                    'effort': 'low',
                    'risk': 'low',
                    'action': 'Delete stopped instances, unattached volumes, unused EIPs',
                    'details': [
                        f"{ec2_unused.get('stopped_instances_count', 0)} stopped instances",
                        f"{ec2_unused.get('unattached_volumes_count', 0)} unattached volumes",
                        f"{ec2_unused.get('unused_elastic_ips_count', 0)} unused Elastic IPs"
                    ]
                })

    # Find idle resources (running but not used)
    if include_idle:
        idle = analyze_idle_resources(cpu_threshold=5.0, lookback_days=7, aws_client=aws_client)
        if 'summary' in idle:
            idle_savings = idle['summary'].get('potential_monthly_savings', 0)
            if idle_savings >= min_impact:
                total_savings += idle_savings
                opportunities.append({
                    'category': 'Idle Resources',
                    'title': 'Stop or resize idle instances',
                    'monthly_savings': idle_savings,
                    'annual_savings': idle_savings * 12,
                    'effort': 'medium',
                    'risk': 'medium',
                    'action': f"Review {idle['summary'].get('total_idle', 0)} idle resources",
                    'details': idle.get('recommendations', [])[:3]
                })

    # Storage optimization
    if include_storage:
        # Snapshot waste
        snapshots = analyze_snapshot_waste(min_age_days=90, aws_client=aws_client)
        if 'summary' in snapshots:
            snapshot_savings = snapshots['summary'].get('potential_monthly_savings', 0)
            if snapshot_savings >= min_impact:
                total_savings += snapshot_savings
                opportunities.append({
                    'category': 'Storage Waste',
                    'title': 'Delete old EBS snapshots',
                    'monthly_savings': snapshot_savings,
                    'annual_savings': snapshot_savings * 12,
                    'effort': 'low',
                    'risk': 'low',
                    'action': 'Delete snapshots older than 90 days',
                    'details': snapshots.get('recommendations', [])[:3]
                })

        # Unused S3 buckets
        s3_unused = find_unused_buckets(min_age_days=90, aws_client=aws_client)
        if 'potential_savings' in s3_unused:
            s3_savings = s3_unused['potential_savings']
            if s3_savings >= min_impact:
                total_savings += s3_savings
                opportunities.append({
                    'category': 'S3 Waste',
                    'title': 'Delete empty/unused S3 buckets',
                    'monthly_savings': s3_savings,
                    'annual_savings': s3_savings * 12,
                    'effort': 'low',
                    'risk': 'low',
                    'action': f"Delete {len(s3_unused.get('empty_buckets', []))} empty buckets",
                    'details': ['Review empty and unused buckets for deletion']
                })

    # Sort by savings (highest first)
    opportunities.sort(key=lambda x: x['monthly_savings'], reverse=True)

    return {
        'total_monthly_savings': round(total_savings, 2),
        'total_annual_savings': round(total_savings * 12, 2),
        'total_opportunities': len(opportunities),
        'top_opportunities': opportunities[:10],  # Top 10
        'all_opportunities': opportunities,
        'summary': {
            'by_effort': {
                'low': len([o for o in opportunities if o['effort'] == 'low']),
                'medium': len([o for o in opportunities if o['effort'] == 'medium']),
                'high': len([o for o in opportunities if o['effort'] == 'high'])
            },
            'by_category': {
                cat: sum(o['monthly_savings'] for o in opportunities if o['category'] == cat)
                for cat in set(o['category'] for o in opportunities)
            }
        },
        'quick_wins': [o for o in opportunities if o['effort'] == 'low' and o['monthly_savings'] >= 20],
        'recommendations': [
            f"Start with {len([o for o in opportunities if o['effort'] == 'low'])} low-effort opportunities",
            f"Total potential savings: ${total_savings:.2f}/month (${total_savings * 12:.2f}/year)",
            "Focus on quick wins first (low effort, high impact)"
        ] if total_savings > 0 else [
            "✅ No significant cost optimization opportunities found",
            "Your AWS account is well-optimized"
        ]
    }


@tool
def diagnose_issue(
    resource_type: str,
    resource_name: str,
    issue_description: Optional[str] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Diagnose issues with AWS resources (Lambda, EC2, etc.).

    This orchestrates monitoring and analysis tools to troubleshoot problems.

    Args:
        resource_type: Type of resource ("lambda", "ec2", "s3", etc.)
        resource_name: Name or ID of the resource
        issue_description: Optional description of the issue
        aws_client: Optional AWS client (auto-created if not provided)

    Returns:
        Diagnostic report with findings and recommendations

    Example:
        >>> report = diagnose_issue("lambda", "my-api-function", "function is slow")
        >>> print(report['diagnosis'])
        >>> for rec in report['recommendations']:
        ...     print(f"- {rec}")
    """
    from strandkit.tools.cloudwatch import get_lambda_logs, get_metric
    from strandkit.tools.iam import analyze_role
    from strandkit.tools.ec2 import analyze_ec2_instance

    findings = []
    recommendations = []

    resource_type = resource_type.lower()

    if resource_type == "lambda":
        # Check error metrics
        errors = get_metric(
            namespace="AWS/Lambda",
            metric_name="Errors",
            dimensions={"FunctionName": resource_name},
            statistic="Sum",
            start_minutes=60,
            aws_client=aws_client
        )

        if 'summary' in errors and errors['summary'].get('max', 0) > 0:
            findings.append({
                'type': 'Errors Detected',
                'severity': 'high',
                'details': f"Function had {errors['summary']['max']} errors in the last hour"
            })

            # Get error logs
            logs = get_lambda_logs(
                resource_name,
                start_minutes=60,
                filter_pattern="ERROR",
                limit=10,
                aws_client=aws_client
            )

            if logs.get('total_events', 0) > 0:
                findings.append({
                    'type': 'Error Logs',
                    'severity': 'high',
                    'details': f"Found {logs['total_events']} error log events",
                    'sample_errors': [e['message'][:200] for e in logs.get('events', [])[:3]]
                })

        # Check duration
        duration = get_metric(
            namespace="AWS/Lambda",
            metric_name="Duration",
            dimensions={"FunctionName": resource_name},
            statistic="Average",
            start_minutes=60,
            aws_client=aws_client
        )

        if 'summary' in duration:
            avg_duration = duration['summary'].get('avg', 0)
            max_duration = duration['summary'].get('max', 0)

            if max_duration > 10000:  # > 10 seconds
                findings.append({
                    'type': 'Performance Issue',
                    'severity': 'medium',
                    'details': f"Function is slow (max: {max_duration:.0f}ms, avg: {avg_duration:.0f}ms)"
                })
                recommendations.append("Consider increasing memory allocation")
                recommendations.append("Review code for performance bottlenecks")

        # Check IAM role (if has permission issues)
        if issue_description and 'permission' in issue_description.lower():
            # Try to find role name (would need to describe function first)
            recommendations.append(f"Use analyze_role() to check Lambda execution role permissions")

        diagnosis = "Lambda function analysis complete"
        if len(findings) == 0:
            diagnosis = "✅ No issues detected with Lambda function"
            recommendations.append("Function metrics look healthy")
        else:
            diagnosis = f"⚠️ Found {len(findings)} issue(s) with Lambda function"

    elif resource_type == "ec2":
        # Analyze EC2 instance
        analysis = analyze_ec2_instance(resource_name, include_metrics=True, aws_client=aws_client)

        if 'error' in analysis:
            findings.append({
                'type': 'Resource Error',
                'severity': 'high',
                'details': analysis['error']
            })
            diagnosis = f"❌ Could not analyze EC2 instance: {analysis['error']}"
        else:
            # Check health
            if 'health_check' in analysis:
                health = analysis['health_check']
                if health.get('health_status') != 'healthy':
                    findings.extend([
                        {'type': 'Health Issue', 'severity': 'high', 'details': issue}
                        for issue in health.get('issues', [])
                    ])

            # Check performance
            if 'metrics' in analysis:
                cpu = analysis['metrics'].get('cpu_utilization', {})
                if cpu.get('average', 0) > 80:
                    findings.append({
                        'type': 'High CPU',
                        'severity': 'high',
                        'details': f"CPU averaging {cpu['average']:.1f}%"
                    })
                    recommendations.append("Consider upgrading instance type")

            diagnosis = "EC2 instance analysis complete"
            if len(findings) == 0:
                diagnosis = "✅ EC2 instance appears healthy"

    else:
        diagnosis = f"Diagnostic support for {resource_type} coming soon"
        recommendations.append(f"Use specific {resource_type} tools for analysis")

    return {
        'resource_type': resource_type,
        'resource_name': resource_name,
        'diagnosis': diagnosis,
        'findings': findings,
        'recommendations': recommendations if recommendations else [
            "No specific recommendations at this time",
            "Continue monitoring resource health"
        ],
        'next_steps': [
            "Review findings and address high-severity issues first",
            "Use specific tools for deeper analysis if needed"
        ] if findings else [
            "Resource appears healthy, continue normal monitoring"
        ]
    }


@tool
def get_aws_overview(
    include_costs: bool = True,
    include_security: bool = True,
    include_resources: bool = True,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get high-level overview of entire AWS account.

    This provides a dashboard-style summary of your AWS environment.

    Args:
        include_costs: Include cost summary (default: True)
        include_security: Include security summary (default: True)
        include_resources: Include resource inventory (default: True)
        aws_client: Optional AWS client (auto-created if not provided)

    Returns:
        Comprehensive account overview

    Example:
        >>> overview = get_aws_overview()
        >>> print(f"Monthly spend: ${overview['costs']['monthly_total']:.2f}")
        >>> print(f"Security score: {overview['security']['score']}/100")
    """
    from strandkit.tools.cost import get_cost_by_service
    from strandkit.tools.ec2 import get_ec2_inventory
    from strandkit.tools.s3 import find_public_buckets
    from strandkit.tools.iam import find_overpermissive_roles

    overview = {
        'account_health': 'healthy',
        'timestamp': None
    }

    # Cost summary
    if include_costs:
        costs = get_cost_by_service(days_back=30, top_n=5, aws_client=aws_client)
        overview['costs'] = {
            'monthly_total': costs.get('total_cost', 0),
            'top_services': [
                {'service': s['service'], 'cost': s['cost']}
                for s in costs.get('services', [])[:3]
            ],
            'status': 'normal' if costs.get('total_cost', 0) < 1000 else 'review'
        }

    # Security summary
    if include_security:
        iam_roles = find_overpermissive_roles(aws_client=aws_client)
        s3_public = find_public_buckets(aws_client=aws_client)

        critical_issues = (
            iam_roles.get('summary', {}).get('critical', 0) +
            s3_public.get('summary', {}).get('critical', 0)
        )
        high_issues = (
            iam_roles.get('summary', {}).get('high', 0) +
            s3_public.get('summary', {}).get('high', 0)
        )

        # Simple security score (100 - (critical*20 + high*10))
        security_score = max(0, 100 - (critical_issues * 20 + high_issues * 10))

        overview['security'] = {
            'score': security_score,
            'critical_issues': critical_issues,
            'high_issues': high_issues,
            'status': 'critical' if critical_issues > 0 else 'warning' if high_issues > 0 else 'good'
        }

        if overview['account_health'] == 'healthy' and critical_issues > 0:
            overview['account_health'] = 'critical'

    # Resource inventory
    if include_resources:
        ec2 = get_ec2_inventory(aws_client=aws_client)
        s3_public = find_public_buckets(aws_client=aws_client) if include_security else {'summary': {}}

        overview['resources'] = {
            'ec2_instances': ec2.get('summary', {}).get('total_instances', 0),
            's3_buckets': s3_public.get('summary', {}).get('total_buckets', 0),
            'monthly_compute_cost': ec2.get('total_monthly_cost', 0)
        }

    # Summary
    overview['summary'] = {
        'health': overview['account_health'],
        'requires_attention': overview.get('security', {}).get('critical_issues', 0) > 0,
        'quick_stats': {
            'monthly_spend': overview.get('costs', {}).get('monthly_total', 0),
            'security_score': overview.get('security', {}).get('score', 100),
            'total_instances': overview.get('resources', {}).get('ec2_instances', 0)
        }
    }

    return overview
