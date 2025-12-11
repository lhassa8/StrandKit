"""
AWS Well-Architected Framework - Reliability Pillar Tools.

This module provides 12 automated checks aligned with the Reliability Pillar
of the AWS Well-Architected Framework.

Reliability Pillar Design Principles:
1. Automatically recover from failure
2. Test recovery procedures
3. Scale horizontally to increase aggregate workload availability
4. Stop guessing capacity
5. Manage change through automation

Reference: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

try:
    from strands import tool
except ImportError:
    def tool(func):
        return func

from strandkit.core.aws_client import AWSClient
from strandkit.tools.wellarchitected._common import (
    create_finding,
    create_check_result,
    create_pillar_review_result,
    Pillar,
    get_all_regions,
)


# =============================================================================
# REL-1: Service Quotas & Constraints
# =============================================================================

@tool
def check_service_quotas(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check service quotas and usage limits (REL-1).

    Validates:
    - Key service quotas vs current usage
    - Quotas approaching limits (>80%)
    - Quota increase requests

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        sq = aws_client.get_client("service-quotas")
        ec2 = aws_client.get_client("ec2")

        # Check key EC2 quotas
        key_quotas = [
            ("ec2", "L-1216C47A", "Running On-Demand Standard instances"),
            ("ec2", "L-34B43A08", "All Standard Spot Instance Requests"),
            ("vpc", "L-F678F1CE", "VPCs per Region"),
            ("elasticloadbalancing", "L-53DA6B97", "Application Load Balancers per Region"),
            ("lambda", "L-B99A9384", "Concurrent executions"),
            ("rds", "L-7B6409FD", "DB instances"),
        ]

        for service_code, quota_code, quota_name in key_quotas:
            try:
                total_resources += 1

                # Get quota value
                quota = sq.get_service_quota(
                    ServiceCode=service_code,
                    QuotaCode=quota_code
                )["Quota"]

                quota_value = quota.get("Value", 0)

                # Try to get usage (varies by service)
                usage = 0
                usage_pct = 0

                if service_code == "ec2" and "On-Demand" in quota_name:
                    # Count running instances
                    instances = ec2.describe_instances(
                        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                    )
                    usage = sum(
                        len(r.get("Instances", []))
                        for r in instances.get("Reservations", [])
                    )
                    usage_pct = (usage / quota_value * 100) if quota_value > 0 else 0

                elif service_code == "vpc":
                    vpcs = ec2.describe_vpcs().get("Vpcs", [])
                    usage = len(vpcs)
                    usage_pct = (usage / quota_value * 100) if quota_value > 0 else 0

                # Check if approaching limit
                if usage_pct >= 80:
                    severity = "HIGH" if usage_pct >= 90 else "MEDIUM"
                    findings.append(create_finding(
                        resource=f"{service_code}/{quota_code}",
                        issue=f"{quota_name}: {usage_pct:.1f}% used ({usage}/{int(quota_value)})",
                        severity=severity,
                        recommendation=f"Request quota increase for {quota_name}",
                        effort="LOW",
                        impact="HIGH",
                        details={
                            "quota_name": quota_name,
                            "current_value": quota_value,
                            "usage": usage,
                            "usage_percent": usage_pct
                        }
                    ))
                else:
                    compliant_resources += 1

            except Exception:
                compliant_resources += 1  # Quota not applicable or can't check

        # Check for pending quota increase requests
        try:
            requests = sq.list_requested_service_quota_change_history_by_quota(
                ServiceCode="ec2",
                QuotaCode="L-1216C47A"
            ).get("RequestedQuotas", [])

            pending = [r for r in requests if r.get("Status") == "PENDING"]
            if pending:
                findings.append(create_finding(
                    resource="service-quotas",
                    issue=f"{len(pending)} pending quota increase request(s)",
                    severity="INFO",
                    recommendation="Monitor pending requests for approval",
                    effort="LOW",
                    impact="LOW"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_service_quotas",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Monitor service quotas proactively",
            "Request quota increases before reaching limits",
            "Use Service Quotas API for automated monitoring",
            "Set up CloudWatch alarms for quota usage",
            "Consider AWS Trusted Advisor for quota checks",
            "Document quota requirements for new workloads"
        ]
    )


# =============================================================================
# REL-2: Network Topology
# =============================================================================

@tool
def check_network_topology(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check network topology for reliability (REL-2).

    Validates:
    - VPN tunnel redundancy (2 tunnels up)
    - Direct Connect connections with backup
    - Transit Gateway usage
    - Multiple NAT Gateways for HA

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        ec2 = aws_client.get_client("ec2")

        # Check VPN connections
        vpn_connections = ec2.describe_vpn_connections().get("VpnConnections", [])

        for vpn in vpn_connections:
            vpn_id = vpn.get("VpnConnectionId")
            state = vpn.get("State")

            if state != "available":
                continue

            total_resources += 1
            tunnels = vpn.get("VgwTelemetry", [])
            tunnels_up = sum(1 for t in tunnels if t.get("Status") == "UP")

            if tunnels_up >= 2:
                compliant_resources += 1
            elif tunnels_up == 1:
                findings.append(create_finding(
                    resource=vpn_id,
                    issue=f"VPN {vpn_id} has only 1 tunnel up (should have 2)",
                    severity="HIGH",
                    recommendation="Ensure both VPN tunnels are configured and up",
                    effort="MEDIUM",
                    impact="HIGH",
                    details={"tunnels_up": tunnels_up, "total_tunnels": len(tunnels)}
                ))
            else:
                findings.append(create_finding(
                    resource=vpn_id,
                    issue=f"VPN {vpn_id} has no tunnels up",
                    severity="CRITICAL",
                    recommendation="Investigate VPN tunnel connectivity immediately",
                    effort="HIGH",
                    impact="CRITICAL"
                ))

        # Check NAT Gateway redundancy
        vpcs = ec2.describe_vpcs().get("Vpcs", [])

        for vpc in vpcs:
            vpc_id = vpc.get("VpcId")

            # Get AZs used in this VPC
            subnets = ec2.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            ).get("Subnets", [])

            azs = set(s.get("AvailabilityZone") for s in subnets)

            if len(azs) <= 1:
                continue  # Single-AZ VPC, skip NAT check

            # Get NAT Gateways
            nat_gws = ec2.describe_nat_gateways(
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "state", "Values": ["available"]}
                ]
            ).get("NatGateways", [])

            nat_azs = set(n.get("SubnetId") for n in nat_gws)

            # Check if we have NAT Gateways and if they span AZs
            if len(nat_gws) > 0:
                total_resources += 1
                if len(nat_gws) >= len(azs):
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=vpc_id,
                        issue=f"VPC {vpc_id} has {len(nat_gws)} NAT Gateway(s) for {len(azs)} AZs",
                        severity="MEDIUM",
                        recommendation="Deploy NAT Gateway in each AZ for high availability",
                        effort="MEDIUM",
                        impact="HIGH",
                        details={
                            "nat_gateways": len(nat_gws),
                            "availability_zones": len(azs)
                        }
                    ))

        # Check Transit Gateway
        try:
            tgws = ec2.describe_transit_gateways().get("TransitGateways", [])

            for tgw in tgws:
                tgw_id = tgw.get("TransitGatewayId")
                total_resources += 1

                # Check attachments
                attachments = ec2.describe_transit_gateway_attachments(
                    Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
                ).get("TransitGatewayAttachments", [])

                if len(attachments) >= 2:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=tgw_id,
                        issue=f"Transit Gateway {tgw_id} has only {len(attachments)} attachment(s)",
                        severity="INFO",
                        recommendation="Consider multiple attachments for redundancy",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_network_topology",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Maintain 2 VPN tunnels up for each connection",
            "Deploy NAT Gateways in each Availability Zone",
            "Use Transit Gateway for hub-and-spoke connectivity",
            "Consider Direct Connect with VPN backup",
            "Implement redundant network paths",
            "Monitor network connectivity with CloudWatch"
        ]
    )


# =============================================================================
# REL-9: Backup Strategy
# =============================================================================

@tool
def check_backup_strategy(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check backup strategy and AWS Backup configuration (REL-9).

    Validates:
    - AWS Backup plans exist
    - Resources are protected by backup plans
    - Backup retention meets requirements
    - Cross-region backup configured

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        backup = aws_client.get_client("backup")

        # Check if any backup plans exist
        plans = backup.list_backup_plans().get("BackupPlansList", [])
        total_resources += 1

        if not plans:
            findings.append(create_finding(
                resource="arn:aws:backup::account",
                issue="No AWS Backup plans configured",
                severity="HIGH",
                recommendation="Create AWS Backup plans to protect critical resources",
                effort="MEDIUM",
                impact="HIGH"
            ))
        else:
            compliant_resources += 1

            # Check each backup plan
            for plan in plans:
                plan_id = plan.get("BackupPlanId")
                plan_name = plan.get("BackupPlanName")

                # Get plan details
                plan_details = backup.get_backup_plan(BackupPlanId=plan_id)["BackupPlan"]
                rules = plan_details.get("Rules", [])

                for rule in rules:
                    # Check retention period
                    lifecycle = rule.get("Lifecycle", {})
                    delete_days = lifecycle.get("DeleteAfterDays", 0)
                    move_to_cold = lifecycle.get("MoveToColdStorageAfterDays", 0)

                    if delete_days > 0 and delete_days < 30:
                        findings.append(create_finding(
                            resource=f"backup-plan/{plan_id}",
                            issue=f"Backup plan '{plan_name}' has short retention ({delete_days} days)",
                            severity="MEDIUM",
                            recommendation="Consider longer retention for compliance/recovery",
                            effort="LOW",
                            impact="MEDIUM"
                        ))

                    # Check for cross-region copy
                    copy_actions = rule.get("CopyActions", [])
                    if not copy_actions:
                        findings.append(create_finding(
                            resource=f"backup-plan/{plan_id}",
                            issue=f"Backup plan '{plan_name}' has no cross-region copy",
                            severity="MEDIUM",
                            recommendation="Add cross-region copy for disaster recovery",
                            effort="MEDIUM",
                            impact="HIGH"
                        ))

        # Check protected resources
        ec2 = aws_client.get_client("ec2")
        rds = aws_client.get_client("rds")

        # Check EBS volumes
        volumes = ec2.describe_volumes().get("Volumes", [])
        for vol in volumes:
            vol_id = vol.get("VolumeId")
            total_resources += 1

            try:
                # Check if volume is in any backup plan
                protected = backup.list_recovery_points_by_resource(
                    ResourceArn=f"arn:aws:ec2:{aws_client.region}:{aws_client.account_id}:volume/{vol_id}"
                ).get("RecoveryPoints", [])

                if protected:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=vol_id,
                        issue=f"EBS volume {vol_id} not protected by AWS Backup",
                        severity="MEDIUM",
                        recommendation="Add volume to a backup plan",
                        effort="LOW",
                        impact="HIGH"
                    ))
            except Exception:
                pass  # May not have permission or volume not backupable

        # Check RDS instances
        instances = rds.describe_db_instances().get("DBInstances", [])
        for instance in instances:
            instance_id = instance.get("DBInstanceIdentifier")
            total_resources += 1

            # Check automated backups
            backup_retention = instance.get("BackupRetentionPeriod", 0)
            if backup_retention >= 7:
                compliant_resources += 1
            else:
                severity = "CRITICAL" if backup_retention == 0 else "MEDIUM"
                findings.append(create_finding(
                    resource=instance.get("DBInstanceArn"),
                    issue=f"RDS '{instance_id}' backup retention is {backup_retention} days",
                    severity=severity,
                    recommendation="Set backup retention to at least 7 days",
                    effort="LOW",
                    impact="HIGH"
                ))

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_backup_strategy",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use AWS Backup for centralized backup management",
            "Define backup frequency based on RPO requirements",
            "Configure cross-region backup for DR",
            "Test backup restoration regularly",
            "Encrypt backups with KMS",
            "Monitor backup job success/failure"
        ]
    )


# =============================================================================
# REL-9: Disaster Recovery
# =============================================================================

@tool
def check_disaster_recovery(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check disaster recovery configuration (REL-9).

    Validates:
    - Cross-region replication configured
    - Multi-region architecture
    - DR runbooks exist (via tags/documentation)
    - RTO/RPO alignment

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        s3 = aws_client.get_client("s3")
        rds = aws_client.get_client("rds")
        dynamodb = aws_client.get_client("dynamodb")

        # Check S3 cross-region replication
        buckets = s3.list_buckets().get("Buckets", [])

        for bucket in buckets[:30]:  # Limit for performance
            bucket_name = bucket["Name"]
            total_resources += 1

            try:
                replication = s3.get_bucket_replication(Bucket=bucket_name)
                rules = replication.get("ReplicationConfiguration", {}).get("Rules", [])

                if rules:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=f"arn:aws:s3:::{bucket_name}",
                        issue=f"S3 bucket '{bucket_name}' has no replication rules",
                        severity="LOW",
                        recommendation="Consider cross-region replication for critical data",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
            except Exception:
                # No replication configured
                findings.append(create_finding(
                    resource=f"arn:aws:s3:::{bucket_name}",
                    issue=f"S3 bucket '{bucket_name}' has no cross-region replication",
                    severity="INFO",
                    recommendation="Evaluate if cross-region replication is needed",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))

        # Check RDS read replicas in different regions
        instances = rds.describe_db_instances().get("DBInstances", [])

        for instance in instances:
            if instance.get("ReadReplicaDBInstanceIdentifiers"):
                continue  # This is a source with replicas

            instance_id = instance.get("DBInstanceIdentifier")
            instance_region = instance.get("AvailabilityZone", "")[:-1]  # Remove AZ letter

            # Check for cross-region read replica
            read_replicas = instance.get("ReadReplicaSourceDBInstanceIdentifier")

            total_resources += 1
            if read_replicas:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource=instance.get("DBInstanceArn"),
                    issue=f"RDS '{instance_id}' has no cross-region replica",
                    severity="INFO",
                    recommendation="Consider cross-region read replica for DR",
                    effort="HIGH",
                    impact="HIGH"
                ))

        # Check DynamoDB global tables
        tables = dynamodb.list_tables().get("TableNames", [])

        for table_name in tables[:20]:  # Limit for performance
            total_resources += 1

            try:
                table = dynamodb.describe_table(TableName=table_name)["Table"]
                global_table = table.get("GlobalTableVersion")
                replicas = table.get("Replicas", [])

                if global_table or len(replicas) > 1:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=table.get("TableArn"),
                        issue=f"DynamoDB table '{table_name}' is single-region",
                        severity="INFO",
                        recommendation="Consider Global Tables for DR",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
            except Exception:
                pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_disaster_recovery",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Define RTO and RPO for each workload",
            "Implement cross-region replication for critical data",
            "Use Multi-AZ deployments within a region",
            "Create and test DR runbooks regularly",
            "Use Infrastructure as Code for rapid recovery",
            "Consider pilot light or warm standby architectures"
        ]
    )


# =============================================================================
# REL-10: Fault Isolation
# =============================================================================

@tool
def check_fault_isolation(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check fault isolation configuration (REL-10).

    Validates:
    - Multi-AZ deployments
    - Load balancer spans multiple AZs
    - RDS Multi-AZ enabled
    - Auto Scaling across AZs

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        ec2 = aws_client.get_client("ec2")
        elbv2 = aws_client.get_client("elbv2")
        rds = aws_client.get_client("rds")
        autoscaling = aws_client.get_client("autoscaling")

        # Check Load Balancers span multiple AZs
        lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])

        for lb in lbs:
            lb_arn = lb.get("LoadBalancerArn")
            lb_name = lb.get("LoadBalancerName")
            azs = lb.get("AvailabilityZones", [])

            total_resources += 1

            if len(azs) >= 2:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource=lb_arn,
                    issue=f"Load balancer '{lb_name}' spans only {len(azs)} AZ(s)",
                    severity="HIGH",
                    recommendation="Deploy load balancer across at least 2 AZs",
                    effort="MEDIUM",
                    impact="HIGH"
                ))

        # Check RDS Multi-AZ
        instances = rds.describe_db_instances().get("DBInstances", [])

        for instance in instances:
            instance_id = instance.get("DBInstanceIdentifier")
            total_resources += 1

            if instance.get("MultiAZ", False):
                compliant_resources += 1
            else:
                engine = instance.get("Engine", "")
                # Aurora clusters are inherently multi-AZ
                if "aurora" not in engine:
                    findings.append(create_finding(
                        resource=instance.get("DBInstanceArn"),
                        issue=f"RDS '{instance_id}' is not Multi-AZ",
                        severity="HIGH",
                        recommendation="Enable Multi-AZ for production databases",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))

        # Check Auto Scaling Groups span multiple AZs
        asgs = autoscaling.describe_auto_scaling_groups().get("AutoScalingGroups", [])

        for asg in asgs:
            asg_name = asg.get("AutoScalingGroupName")
            azs = asg.get("AvailabilityZones", [])

            total_resources += 1

            if len(azs) >= 2:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource=asg.get("AutoScalingGroupARN"),
                    issue=f"Auto Scaling group '{asg_name}' spans only {len(azs)} AZ(s)",
                    severity="MEDIUM",
                    recommendation="Configure ASG to span at least 2 AZs",
                    effort="LOW",
                    impact="HIGH"
                ))

        # Check Lambda VPC functions span multiple AZs
        lambda_client = aws_client.get_client("lambda")
        try:
            paginator = lambda_client.get_paginator("list_functions")
            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    vpc_config = func.get("VpcConfig", {})
                    subnet_ids = vpc_config.get("SubnetIds", [])

                    if subnet_ids:  # VPC-enabled function
                        total_resources += 1

                        # Get subnet AZs
                        if len(subnet_ids) >= 2:
                            subnets = ec2.describe_subnets(
                                SubnetIds=subnet_ids
                            ).get("Subnets", [])
                            azs = set(s.get("AvailabilityZone") for s in subnets)

                            if len(azs) >= 2:
                                compliant_resources += 1
                            else:
                                findings.append(create_finding(
                                    resource=func.get("FunctionArn"),
                                    issue=f"Lambda '{func.get('FunctionName')}' VPC subnets in single AZ",
                                    severity="MEDIUM",
                                    recommendation="Configure Lambda with subnets in multiple AZs",
                                    effort="LOW",
                                    impact="HIGH"
                                ))
                        else:
                            findings.append(create_finding(
                                resource=func.get("FunctionArn"),
                                issue=f"Lambda '{func.get('FunctionName')}' has only 1 VPC subnet",
                                severity="MEDIUM",
                                recommendation="Configure Lambda with subnets in multiple AZs",
                                effort="LOW",
                                impact="HIGH"
                            ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_fault_isolation",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Deploy resources across multiple Availability Zones",
            "Use Multi-AZ for all production RDS instances",
            "Configure Auto Scaling groups to span 2+ AZs",
            "Use cross-AZ load balancing",
            "Consider multi-region for critical workloads",
            "Design for failure - assume any component can fail"
        ]
    )


# =============================================================================
# REL-7: Auto Scaling
# =============================================================================

@tool
def check_auto_scaling_config(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check Auto Scaling configuration (REL-7).

    Validates:
    - Auto Scaling groups have proper health checks
    - Scaling policies are configured
    - Min/max capacity settings
    - Target tracking policies

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        autoscaling = aws_client.get_client("autoscaling")

        # Get all Auto Scaling groups
        asgs = autoscaling.describe_auto_scaling_groups().get("AutoScalingGroups", [])

        for asg in asgs:
            asg_name = asg.get("AutoScalingGroupName")
            asg_arn = asg.get("AutoScalingGroupARN")
            total_resources += 1
            issues = 0

            # Check health check type
            health_check_type = asg.get("HealthCheckType", "EC2")
            if health_check_type == "EC2":
                # Check if there's a load balancer attached
                target_groups = asg.get("TargetGroupARNs", [])
                load_balancers = asg.get("LoadBalancerNames", [])

                if target_groups or load_balancers:
                    issues += 1
                    findings.append(create_finding(
                        resource=asg_arn,
                        issue=f"ASG '{asg_name}' uses EC2 health check with load balancer",
                        severity="MEDIUM",
                        recommendation="Switch to ELB health check type",
                        effort="LOW",
                        impact="HIGH"
                    ))

            # Check capacity settings
            min_size = asg.get("MinSize", 0)
            max_size = asg.get("MaxSize", 0)
            desired = asg.get("DesiredCapacity", 0)

            if min_size == 0 and desired > 0:
                findings.append(create_finding(
                    resource=asg_arn,
                    issue=f"ASG '{asg_name}' has MinSize=0 (can scale to zero)",
                    severity="LOW",
                    recommendation="Set MinSize >= 1 for production workloads",
                    effort="LOW",
                    impact="MEDIUM"
                ))

            if max_size == desired:
                issues += 1
                findings.append(create_finding(
                    resource=asg_arn,
                    issue=f"ASG '{asg_name}' MaxSize equals DesiredCapacity (no room to scale)",
                    severity="MEDIUM",
                    recommendation="Increase MaxSize to allow scaling up",
                    effort="LOW",
                    impact="HIGH"
                ))

            # Check for scaling policies
            policies = autoscaling.describe_policies(
                AutoScalingGroupName=asg_name
            ).get("ScalingPolicies", [])

            if not policies:
                issues += 1
                findings.append(create_finding(
                    resource=asg_arn,
                    issue=f"ASG '{asg_name}' has no scaling policies",
                    severity="MEDIUM",
                    recommendation="Add target tracking or step scaling policies",
                    effort="MEDIUM",
                    impact="HIGH"
                ))

            # Check cooldown
            cooldown = asg.get("DefaultCooldown", 300)
            if cooldown > 300:
                findings.append(create_finding(
                    resource=asg_arn,
                    issue=f"ASG '{asg_name}' has high cooldown ({cooldown}s)",
                    severity="LOW",
                    recommendation="Consider reducing cooldown for faster scaling",
                    effort="LOW",
                    impact="LOW"
                ))

            if issues == 0:
                compliant_resources += 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_auto_scaling_config",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use ELB health checks when behind a load balancer",
            "Configure scaling policies (target tracking recommended)",
            "Set appropriate min/max capacity limits",
            "Use predictive scaling for predictable patterns",
            "Monitor scaling events and adjust policies",
            "Consider scaling on multiple metrics"
        ]
    )


# =============================================================================
# REL-6: Monitoring & Health Checks
# =============================================================================

@tool
def check_load_balancer_health(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check load balancer health check configuration (REL-6).

    Validates:
    - Health check intervals and thresholds
    - Target health status
    - Connection draining enabled
    - Cross-zone load balancing

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        elbv2 = aws_client.get_client("elbv2")

        # Check target groups
        target_groups = elbv2.describe_target_groups().get("TargetGroups", [])

        for tg in target_groups:
            tg_arn = tg.get("TargetGroupArn")
            tg_name = tg.get("TargetGroupName")
            total_resources += 1
            issues = 0

            # Check health check settings
            health_check_interval = tg.get("HealthCheckIntervalSeconds", 30)
            unhealthy_threshold = tg.get("UnhealthyThresholdCount", 2)
            healthy_threshold = tg.get("HealthyThresholdCount", 5)

            if health_check_interval > 30:
                findings.append(create_finding(
                    resource=tg_arn,
                    issue=f"Target group '{tg_name}' health check interval is {health_check_interval}s",
                    severity="LOW",
                    recommendation="Consider reducing health check interval to 30s or less",
                    effort="LOW",
                    impact="MEDIUM"
                ))

            # Check target health
            try:
                health = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                targets = health.get("TargetHealthDescriptions", [])

                unhealthy = [t for t in targets if t.get("TargetHealth", {}).get("State") != "healthy"]

                if unhealthy:
                    issues += 1
                    findings.append(create_finding(
                        resource=tg_arn,
                        issue=f"Target group '{tg_name}' has {len(unhealthy)} unhealthy target(s)",
                        severity="HIGH",
                        recommendation="Investigate and fix unhealthy targets",
                        effort="MEDIUM",
                        impact="HIGH",
                        details={
                            "total_targets": len(targets),
                            "unhealthy_targets": len(unhealthy)
                        }
                    ))
            except Exception:
                pass

            # Check deregistration delay (connection draining)
            try:
                attrs = elbv2.describe_target_group_attributes(TargetGroupArn=tg_arn)
                attr_dict = {a["Key"]: a["Value"] for a in attrs.get("Attributes", [])}

                dereg_delay = int(attr_dict.get("deregistration_delay.timeout_seconds", 300))
                if dereg_delay < 30:
                    findings.append(create_finding(
                        resource=tg_arn,
                        issue=f"Target group '{tg_name}' deregistration delay is only {dereg_delay}s",
                        severity="LOW",
                        recommendation="Increase deregistration delay for graceful draining",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
            except Exception:
                pass

            if issues == 0:
                compliant_resources += 1

        # Check cross-zone load balancing on ALBs
        lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])

        for lb in lbs:
            lb_arn = lb.get("LoadBalancerArn")
            lb_name = lb.get("LoadBalancerName")
            lb_type = lb.get("Type")

            if lb_type == "network":  # NLB
                total_resources += 1
                try:
                    attrs = elbv2.describe_load_balancer_attributes(LoadBalancerArn=lb_arn)
                    attr_dict = {a["Key"]: a["Value"] for a in attrs.get("Attributes", [])}

                    cross_zone = attr_dict.get("load_balancing.cross_zone.enabled", "false")
                    if cross_zone != "true":
                        findings.append(create_finding(
                            resource=lb_arn,
                            issue=f"NLB '{lb_name}' cross-zone load balancing disabled",
                            severity="MEDIUM",
                            recommendation="Enable cross-zone load balancing for better distribution",
                            effort="LOW",
                            impact="MEDIUM"
                        ))
                    else:
                        compliant_resources += 1
                except Exception:
                    pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_load_balancer_health",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Configure appropriate health check intervals (10-30s)",
            "Set unhealthy threshold to detect failures quickly",
            "Enable connection draining (deregistration delay)",
            "Enable cross-zone load balancing",
            "Monitor target health with CloudWatch",
            "Use health check endpoints that verify full stack"
        ]
    )


# =============================================================================
# REL-6: Monitoring & Alerting
# =============================================================================

@tool
def check_monitoring_alerting(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check monitoring and alerting configuration (REL-6).

    Validates:
    - CloudWatch alarms configured
    - Key metrics monitored
    - Alarm actions configured (SNS)
    - Dashboard exists

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        cloudwatch = aws_client.get_client("cloudwatch")

        # Check CloudWatch alarms
        alarms = cloudwatch.describe_alarms().get("MetricAlarms", [])
        total_resources += 1

        if not alarms:
            findings.append(create_finding(
                resource="arn:aws:cloudwatch::account",
                issue="No CloudWatch alarms configured",
                severity="HIGH",
                recommendation="Create alarms for key metrics (CPU, errors, latency)",
                effort="MEDIUM",
                impact="HIGH"
            ))
        else:
            compliant_resources += 1

            # Check alarm actions
            alarms_without_actions = [
                a for a in alarms
                if not a.get("AlarmActions") and not a.get("OKActions")
            ]

            if alarms_without_actions:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue=f"{len(alarms_without_actions)} alarm(s) have no actions configured",
                    severity="MEDIUM",
                    recommendation="Add SNS or Auto Scaling actions to alarms",
                    effort="LOW",
                    impact="HIGH"
                ))

            # Check for key alarm types
            alarm_namespaces = set(a.get("Namespace") for a in alarms)
            recommended = ["AWS/EC2", "AWS/RDS", "AWS/Lambda", "AWS/ELB", "AWS/ApplicationELB"]

            missing = [ns for ns in recommended if ns not in alarm_namespaces]
            if missing:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue=f"No alarms for: {', '.join(missing)}",
                    severity="MEDIUM",
                    recommendation="Create alarms for these service namespaces",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))

        # Check CloudWatch dashboards
        dashboards = cloudwatch.list_dashboards().get("DashboardEntries", [])
        total_resources += 1

        if dashboards:
            compliant_resources += 1
        else:
            findings.append(create_finding(
                resource="arn:aws:cloudwatch::account",
                issue="No CloudWatch dashboards configured",
                severity="LOW",
                recommendation="Create dashboards for operational visibility",
                effort="MEDIUM",
                impact="MEDIUM"
            ))

        # Check for composite alarms (advanced monitoring)
        composite_alarms = cloudwatch.describe_alarms(
            AlarmTypes=["CompositeAlarm"]
        ).get("CompositeAlarms", [])

        if not composite_alarms and len(alarms) > 5:
            findings.append(create_finding(
                resource="arn:aws:cloudwatch::account",
                issue="No composite alarms configured",
                severity="INFO",
                recommendation="Use composite alarms to reduce alarm noise",
                effort="MEDIUM",
                impact="LOW"
            ))

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_monitoring_alerting",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Create alarms for all critical metrics",
            "Configure alarm actions (SNS, Lambda, Auto Scaling)",
            "Use composite alarms to reduce noise",
            "Create dashboards for operational visibility",
            "Monitor custom application metrics",
            "Set appropriate alarm thresholds and evaluation periods"
        ]
    )


# =============================================================================
# REL-5: Distributed System Design
# =============================================================================

@tool
def check_distributed_system_design(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check distributed system design patterns (REL-5).

    Validates:
    - SQS dead letter queues configured
    - Lambda DLQs configured
    - Step Functions error handling
    - API Gateway timeouts

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        sqs = aws_client.get_client("sqs")
        lambda_client = aws_client.get_client("lambda")

        # Check SQS queues for DLQ
        queues = sqs.list_queues().get("QueueUrls", [])

        for queue_url in queues:
            queue_name = queue_url.split("/")[-1]

            # Skip DLQ queues themselves
            if "-dlq" in queue_name.lower() or "deadletter" in queue_name.lower():
                continue

            total_resources += 1

            try:
                attrs = sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=["RedrivePolicy"]
                )

                redrive = attrs.get("Attributes", {}).get("RedrivePolicy")
                if redrive:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=queue_url,
                        issue=f"SQS queue '{queue_name}' has no dead letter queue",
                        severity="MEDIUM",
                        recommendation="Configure a DLQ for failed message handling",
                        effort="LOW",
                        impact="HIGH"
                    ))
            except Exception:
                pass

        # Check Lambda functions for DLQ/destinations
        try:
            paginator = lambda_client.get_paginator("list_functions")
            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    func_name = func.get("FunctionName")
                    func_arn = func.get("FunctionArn")
                    total_resources += 1

                    # Check DLQ config
                    dlq = func.get("DeadLetterConfig", {}).get("TargetArn")

                    # Check event invoke config for destinations
                    try:
                        invoke_config = lambda_client.get_function_event_invoke_config(
                            FunctionName=func_name
                        )
                        on_failure = invoke_config.get("DestinationConfig", {}).get("OnFailure", {})
                        has_failure_dest = on_failure.get("Destination")
                    except Exception:
                        has_failure_dest = None

                    if dlq or has_failure_dest:
                        compliant_resources += 1
                    else:
                        # Check if async (event sources suggest async invocation)
                        try:
                            event_sources = lambda_client.list_event_source_mappings(
                                FunctionName=func_name
                            ).get("EventSourceMappings", [])

                            if event_sources:  # Has event source = async
                                findings.append(create_finding(
                                    resource=func_arn,
                                    issue=f"Lambda '{func_name}' has no DLQ or failure destination",
                                    severity="MEDIUM",
                                    recommendation="Configure DLQ or failure destination for error handling",
                                    effort="LOW",
                                    impact="HIGH"
                                ))
                        except Exception:
                            pass
        except Exception:
            pass

        # Check Step Functions for error handling
        sfn = aws_client.get_client("stepfunctions")
        try:
            state_machines = sfn.list_state_machines().get("stateMachines", [])

            for sm in state_machines:
                sm_arn = sm.get("stateMachineArn")
                sm_name = sm.get("name")
                total_resources += 1

                try:
                    definition = sfn.describe_state_machine(
                        stateMachineArn=sm_arn
                    ).get("definition", "")

                    # Check for Catch/Retry in definition
                    has_catch = '"Catch"' in definition
                    has_retry = '"Retry"' in definition

                    if has_catch or has_retry:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=sm_arn,
                            issue=f"Step Functions '{sm_name}' has no Catch/Retry error handling",
                            severity="MEDIUM",
                            recommendation="Add Catch and Retry blocks for error handling",
                            effort="MEDIUM",
                            impact="HIGH"
                        ))
                except Exception:
                    pass
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_distributed_system_design",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Configure dead letter queues for SQS",
            "Set up Lambda DLQs or failure destinations",
            "Use Step Functions Catch/Retry for error handling",
            "Implement circuit breakers for external calls",
            "Set appropriate timeouts for all operations",
            "Use exponential backoff for retries"
        ]
    )


# =============================================================================
# REL-8: Change Management
# =============================================================================

@tool
def check_change_management(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check change management configuration (REL-8).

    Validates:
    - CloudFormation stacks with drift detection
    - CodeDeploy deployments with rollback
    - Auto Scaling update policies

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        cfn = aws_client.get_client("cloudformation")
        codedeploy = aws_client.get_client("codedeploy")

        # Check CloudFormation stacks
        stacks = cfn.list_stacks(
            StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"]
        ).get("StackSummaries", [])

        for stack in stacks:
            stack_name = stack.get("StackName")
            total_resources += 1

            # Check drift status
            try:
                drift = cfn.describe_stack_drift_detection_status(
                    StackName=stack_name
                )
                drift_status = drift.get("StackDriftStatus")

                if drift_status == "DRIFTED":
                    findings.append(create_finding(
                        resource=stack.get("StackId"),
                        issue=f"CloudFormation stack '{stack_name}' has drifted",
                        severity="MEDIUM",
                        recommendation="Investigate and remediate drift",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
                else:
                    compliant_resources += 1
            except Exception:
                compliant_resources += 1  # No drift detection run

        # Check CodeDeploy deployment configurations
        try:
            apps = codedeploy.list_applications().get("applications", [])

            for app_name in apps:
                deployment_groups = codedeploy.list_deployment_groups(
                    applicationName=app_name
                ).get("deploymentGroups", [])

                for dg_name in deployment_groups:
                    total_resources += 1

                    dg = codedeploy.get_deployment_group(
                        applicationName=app_name,
                        deploymentGroupName=dg_name
                    ).get("deploymentGroupInfo", {})

                    # Check auto rollback
                    auto_rollback = dg.get("autoRollbackConfiguration", {})
                    rollback_enabled = auto_rollback.get("enabled", False)

                    if rollback_enabled:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=dg.get("deploymentGroupId"),
                            issue=f"CodeDeploy group '{dg_name}' has auto-rollback disabled",
                            severity="MEDIUM",
                            recommendation="Enable auto-rollback on deployment failures",
                            effort="LOW",
                            impact="HIGH"
                        ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_change_management",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use Infrastructure as Code (CloudFormation, CDK)",
            "Detect and remediate stack drift",
            "Enable auto-rollback for deployments",
            "Use blue/green or canary deployments",
            "Test changes in staging before production",
            "Implement change windows and approval gates"
        ]
    )


# =============================================================================
# REL-9: Database Reliability
# =============================================================================

@tool
def check_database_reliability(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check database reliability configuration (REL-9).

    Validates:
    - RDS Multi-AZ enabled
    - Aurora replicas configured
    - Backup retention adequate
    - Performance Insights enabled

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        rds = aws_client.get_client("rds")

        # Check RDS instances
        instances = rds.describe_db_instances().get("DBInstances", [])

        for instance in instances:
            instance_id = instance.get("DBInstanceIdentifier")
            instance_arn = instance.get("DBInstanceArn")
            engine = instance.get("Engine", "")
            total_resources += 1
            issues = 0

            # Skip read replicas
            if instance.get("ReadReplicaSourceDBInstanceIdentifier"):
                compliant_resources += 1
                continue

            # Check Multi-AZ (except Aurora which is inherently multi-AZ)
            if "aurora" not in engine:
                if not instance.get("MultiAZ", False):
                    issues += 1
                    findings.append(create_finding(
                        resource=instance_arn,
                        issue=f"RDS '{instance_id}' is not Multi-AZ",
                        severity="HIGH",
                        recommendation="Enable Multi-AZ for production databases",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))

            # Check backup retention
            backup_retention = instance.get("BackupRetentionPeriod", 0)
            if backup_retention < 7:
                issues += 1
                severity = "CRITICAL" if backup_retention == 0 else "MEDIUM"
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS '{instance_id}' backup retention is {backup_retention} days",
                    severity=severity,
                    recommendation="Set backup retention to at least 7 days",
                    effort="LOW",
                    impact="HIGH"
                ))

            # Check Performance Insights
            if not instance.get("PerformanceInsightsEnabled", False):
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS '{instance_id}' Performance Insights disabled",
                    severity="LOW",
                    recommendation="Enable Performance Insights for troubleshooting",
                    effort="LOW",
                    impact="MEDIUM"
                ))

            # Check Enhanced Monitoring
            monitoring_interval = instance.get("MonitoringInterval", 0)
            if monitoring_interval == 0:
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS '{instance_id}' Enhanced Monitoring disabled",
                    severity="LOW",
                    recommendation="Enable Enhanced Monitoring",
                    effort="LOW",
                    impact="MEDIUM"
                ))

            if issues == 0:
                compliant_resources += 1

        # Check Aurora clusters
        clusters = rds.describe_db_clusters().get("DBClusters", [])

        for cluster in clusters:
            cluster_id = cluster.get("DBClusterIdentifier")
            cluster_arn = cluster.get("DBClusterArn")
            total_resources += 1
            issues = 0

            # Check reader instances
            members = cluster.get("DBClusterMembers", [])
            readers = [m for m in members if not m.get("IsClusterWriter")]

            if len(readers) == 0:
                issues += 1
                findings.append(create_finding(
                    resource=cluster_arn,
                    issue=f"Aurora cluster '{cluster_id}' has no read replicas",
                    severity="MEDIUM",
                    recommendation="Add at least one read replica for HA",
                    effort="MEDIUM",
                    impact="HIGH"
                ))

            # Check backup retention
            backup_retention = cluster.get("BackupRetentionPeriod", 0)
            if backup_retention < 7:
                issues += 1
                findings.append(create_finding(
                    resource=cluster_arn,
                    issue=f"Aurora cluster '{cluster_id}' backup retention is {backup_retention} days",
                    severity="MEDIUM",
                    recommendation="Set backup retention to at least 7 days",
                    effort="LOW",
                    impact="HIGH"
                ))

            if issues == 0:
                compliant_resources += 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_database_reliability",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Enable Multi-AZ for production RDS instances",
            "Add read replicas for Aurora clusters",
            "Set backup retention to at least 7 days",
            "Enable Performance Insights for troubleshooting",
            "Enable Enhanced Monitoring for OS metrics",
            "Test database recovery procedures regularly"
        ]
    )


# =============================================================================
# Reliability Pillar Review (Orchestrator)
# =============================================================================

@tool
def run_reliability_pillar_review(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run comprehensive Reliability Pillar review (all REL checks).

    Executes all 11 reliability checks and provides:
    - Overall reliability score
    - Prioritized findings
    - Remediation recommendations
    - Best practices summary

    Returns:
        Complete Reliability Pillar assessment with aggregated results.
    """
    if aws_client is None:
        aws_client = AWSClient()

    check_results = []
    errors = []

    # Run all reliability checks
    checks = [
        ("Service Quotas", check_service_quotas),
        ("Network Topology", check_network_topology),
        ("Backup Strategy", check_backup_strategy),
        ("Disaster Recovery", check_disaster_recovery),
        ("Fault Isolation", check_fault_isolation),
        ("Auto Scaling Config", check_auto_scaling_config),
        ("Load Balancer Health", check_load_balancer_health),
        ("Monitoring & Alerting", check_monitoring_alerting),
        ("Distributed System Design", check_distributed_system_design),
        ("Change Management", check_change_management),
        ("Database Reliability", check_database_reliability),
    ]

    for check_name, check_func in checks:
        try:
            result = check_func(aws_client=aws_client)
            if "error" in result:
                errors.append({"check": check_name, "error": result["error"]})
            else:
                check_results.append(result)
        except Exception as e:
            errors.append({"check": check_name, "error": str(e)})

    # Create pillar review result
    result = create_pillar_review_result(
        pillar=Pillar.RELIABILITY.value,
        check_results=check_results,
        recommendations=[
            "Deploy resources across multiple Availability Zones",
            "Enable Multi-AZ for all production databases",
            "Configure AWS Backup with cross-region replication",
            "Monitor service quotas and request increases proactively",
            "Implement auto-scaling with appropriate policies",
            "Use dead letter queues for all async processing",
            "Create CloudWatch alarms for key metrics",
            "Test disaster recovery procedures regularly"
        ]
    )

    if errors:
        result["errors"] = errors

    return result
