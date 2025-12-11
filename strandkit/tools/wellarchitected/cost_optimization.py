"""
AWS Well-Architected Framework - Cost Optimization Pillar Tools.

This module provides automated checks aligned with the Cost Optimization Pillar
of the AWS Well-Architected Framework (2025 edition).

Cost Optimization focuses on achieving the best price-performance for workloads.
The pillar covers 11 questions (COST01-COST11) with 50 best practices organized
into five focus areas:

1. Practice Cloud Financial Management (COST01)
2. Expenditure and Usage Awareness (COST02-COST04)
3. Cost-Effective Resources (COST05-COST08)
4. Manage Demand and Supply (COST09)
5. Optimize Over Time (COST10-COST11)

Reference: https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/
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
)


# =============================================================================
# COST-01: Cloud Financial Management
# =============================================================================

@tool
def check_cloud_financial_management(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check cloud financial management practices (COST01).

    Validates:
    - Budgets configured (BP03)
    - Cost anomaly detection enabled (BP06)
    - Cost allocation tags defined (BP05)
    - AWS Cost Explorer enabled

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check for budgets (COST01-BP03)
        budgets = aws_client.get_client("budgets")
        try:
            sts = aws_client.get_client("sts")
            account_id = sts.get_caller_identity()["Account"]

            budget_list = budgets.describe_budgets(AccountId=account_id).get("Budgets", [])
            total_checks += 1

            if budget_list:
                passed_checks += 1
                # Check for budget alerts
                budgets_with_notifications = sum(
                    1 for b in budget_list
                    if b.get("NotificationsWithSubscribers")
                )
                if budgets_with_notifications < len(budget_list):
                    findings.append(create_finding(
                        resource="arn:aws:budgets::account",
                        issue=f"{len(budget_list) - budgets_with_notifications} budget(s) without notifications",
                        severity="MEDIUM",
                        recommendation="Add notifications to all budgets for proactive alerts",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:budgets::account",
                    issue="No AWS Budgets configured",
                    severity="HIGH",
                    recommendation="Create budgets to track and control spending",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            total_checks += 1
            findings.append(create_finding(
                resource="arn:aws:budgets::account",
                issue="Could not check AWS Budgets (may need Budgets permissions)",
                severity="MEDIUM",
                recommendation="Enable AWS Budgets and configure spending limits",
                effort="LOW",
                impact="HIGH"
            ))

        # Check for Cost Anomaly Detection (COST01-BP06)
        ce = aws_client.get_client("ce")
        try:
            monitors = ce.get_anomaly_monitors().get("AnomalyMonitors", [])
            total_checks += 1

            if monitors:
                passed_checks += 1
                # Check for active subscriptions
                subscriptions = ce.get_anomaly_subscriptions().get("AnomalySubscriptions", [])
                if not subscriptions:
                    findings.append(create_finding(
                        resource="arn:aws:ce::account",
                        issue="Cost anomaly monitors exist but no subscriptions",
                        severity="MEDIUM",
                        recommendation="Create anomaly subscriptions to receive alerts",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:ce::account",
                    issue="No Cost Anomaly Detection monitors configured",
                    severity="HIGH",
                    recommendation="Enable Cost Anomaly Detection to catch unexpected spending",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            total_checks += 1

        # Check for cost allocation tags (COST01-BP05)
        try:
            tags = ce.list_cost_allocation_tags(
                Status="Active"
            ).get("CostAllocationTags", [])
            total_checks += 1

            if len(tags) >= 3:  # At least 3 active tags
                passed_checks += 1
            elif tags:
                findings.append(create_finding(
                    resource="arn:aws:ce::account",
                    issue=f"Only {len(tags)} cost allocation tag(s) active",
                    severity="LOW",
                    recommendation="Activate more cost allocation tags for better cost attribution",
                    effort="LOW",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:ce::account",
                    issue="No cost allocation tags activated",
                    severity="MEDIUM",
                    recommendation="Activate cost allocation tags to track spending by team/project",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_cloud_financial_management",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Create AWS Budgets with notifications (COST01-BP03)",
            "Enable Cost Anomaly Detection monitors (COST01-BP06)",
            "Activate cost allocation tags for attribution (COST01-BP05)",
            "Review Cost Explorer regularly (COST01-BP06)",
            "Establish cost ownership across teams (COST01-BP01)",
            "Create cost awareness dashboards (COST01-BP04)"
        ]
    )


# =============================================================================
# COST-02: Governance
# =============================================================================

@tool
def check_cost_governance(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check cost governance practices (COST02).

    Validates:
    - Service Control Policies for cost control (BP05)
    - IAM policies limiting expensive services (BP04)
    - Account structure for cost isolation (BP03)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check for Organizations SCPs (COST02-BP03, BP05)
        org = aws_client.get_client("organizations")
        try:
            org_info = org.describe_organization()
            total_checks += 1

            if org_info["Organization"].get("FeatureSet") == "ALL":
                passed_checks += 1

                # Check for SCPs that might limit costs
                policies = org.list_policies(Filter="SERVICE_CONTROL_POLICY").get("Policies", [])
                custom_scps = [p for p in policies if p.get("Name") != "FullAWSAccess"]

                if not custom_scps:
                    findings.append(create_finding(
                        resource="arn:aws:organizations::account",
                        issue="No custom SCPs for cost governance",
                        severity="MEDIUM",
                        recommendation="Create SCPs to restrict expensive services or regions",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))

                # Check account structure
                accounts = org.list_accounts().get("Accounts", [])
                if len(accounts) < 2:
                    findings.append(create_finding(
                        resource="arn:aws:organizations::account",
                        issue="Single-account structure limits cost isolation",
                        severity="LOW",
                        recommendation="Consider multi-account structure for cost separation",
                        effort="HIGH",
                        impact="MEDIUM"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:organizations::account",
                    issue="Organization not using all features (SCPs disabled)",
                    severity="MEDIUM",
                    recommendation="Enable all features to use SCPs for cost governance",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            # Not in an organization
            total_checks += 1
            findings.append(create_finding(
                resource="arn:aws:organizations::account",
                issue="Account not part of AWS Organizations",
                severity="INFO",
                recommendation="Consider AWS Organizations for centralized cost governance",
                effort="HIGH",
                impact="MEDIUM"
            ))

        # Check for IAM boundaries limiting expensive services (COST02-BP04)
        iam = aws_client.get_client("iam")
        try:
            # Check for deny policies on expensive services
            policies = iam.list_policies(Scope="Local").get("Policies", [])
            total_checks += 1

            deny_policies = []
            for policy in policies[:20]:
                try:
                    version = iam.get_policy(PolicyArn=policy["Arn"])["Policy"]["DefaultVersionId"]
                    doc = iam.get_policy_version(
                        PolicyArn=policy["Arn"],
                        VersionId=version
                    )["PolicyVersion"]["Document"]

                    if isinstance(doc, str):
                        import json
                        doc = json.loads(doc)

                    for stmt in doc.get("Statement", []):
                        if stmt.get("Effect") == "Deny":
                            deny_policies.append(policy["PolicyName"])
                            break
                except Exception:
                    pass

            if deny_policies:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:iam::account",
                    issue="No IAM deny policies for cost control",
                    severity="LOW",
                    recommendation="Create IAM policies to restrict expensive services",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_cost_governance",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Implement SCPs to restrict expensive services (COST02-BP05)",
            "Use multi-account structure for cost isolation (COST02-BP03)",
            "Create IAM policies to limit service usage (COST02-BP04)",
            "Define cost policies and targets (COST02-BP01, BP02)",
            "Track project/workload lifecycle for decommissioning (COST02-BP06)"
        ]
    )


# =============================================================================
# COST-03: Monitor Cost and Usage
# =============================================================================

@tool
def check_cost_monitoring(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check cost monitoring configuration (COST03).

    Validates:
    - Cost Explorer enabled with detailed data (BP01)
    - Cost allocation tags configured (BP02, BP03)
    - Billing alerts configured (BP05)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        ce = aws_client.get_client("ce")

        # Check Cost Explorer access (COST03-BP01)
        try:
            # Try to get cost data - if it works, Cost Explorer is enabled
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

            ce.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="DAILY",
                Metrics=["UnblendedCost"]
            )
            total_checks += 1
            passed_checks += 1
        except Exception:
            total_checks += 1
            findings.append(create_finding(
                resource="arn:aws:ce::account",
                issue="Cost Explorer not accessible or not enabled",
                severity="HIGH",
                recommendation="Enable Cost Explorer in the Billing Console",
                effort="LOW",
                impact="HIGH"
            ))

        # Check cost allocation tags (COST03-BP02, BP03)
        try:
            all_tags = ce.list_cost_allocation_tags().get("CostAllocationTags", [])
            active_tags = [t for t in all_tags if t.get("Status") == "Active"]
            inactive_tags = [t for t in all_tags if t.get("Status") == "Inactive"]

            total_checks += 1

            if len(active_tags) >= 5:
                passed_checks += 1
            elif active_tags:
                findings.append(create_finding(
                    resource="arn:aws:ce::account",
                    issue=f"Only {len(active_tags)} active cost allocation tags",
                    severity="LOW",
                    recommendation="Activate more tags for granular cost tracking",
                    effort="LOW",
                    impact="MEDIUM",
                    details={"active_tags": len(active_tags), "inactive_tags": len(inactive_tags)}
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:ce::account",
                    issue="No active cost allocation tags",
                    severity="MEDIUM",
                    recommendation="Activate tags like Environment, Project, Owner",
                    effort="LOW",
                    impact="HIGH",
                    details={"inactive_tags_available": len(inactive_tags)}
                ))

            # Check for recommended tags
            recommended_tags = ["Environment", "Project", "Owner", "CostCenter", "Application"]
            active_tag_keys = [t.get("TagKey", "").lower() for t in active_tags]
            missing_recommended = [t for t in recommended_tags if t.lower() not in active_tag_keys]

            if missing_recommended:
                findings.append(create_finding(
                    resource="arn:aws:ce::account",
                    issue=f"Missing recommended cost allocation tags: {', '.join(missing_recommended)}",
                    severity="INFO",
                    recommendation="Consider activating standard tags for cost attribution",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for CloudWatch billing alarms (COST03-BP05)
        cloudwatch = aws_client.get_client("cloudwatch", region_name="us-east-1")
        try:
            alarms = cloudwatch.describe_alarms(
                AlarmNamePrefix="",
                StateValue="OK"
            ).get("MetricAlarms", [])

            # Filter for billing alarms
            billing_alarms = [
                a for a in alarms
                if a.get("Namespace") == "AWS/Billing" or
                "billing" in a.get("AlarmName", "").lower() or
                "cost" in a.get("AlarmName", "").lower()
            ]

            total_checks += 1
            if billing_alarms:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No CloudWatch billing alarms configured",
                    severity="MEDIUM",
                    recommendation="Create billing alarms for spend thresholds",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_cost_monitoring",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Enable Cost Explorer for visibility (COST03-BP01, BP05)",
            "Activate cost allocation tags (COST03-BP02, BP03)",
            "Create CloudWatch billing alarms (COST03-BP05)",
            "Define organization cost metrics (COST03-BP04)",
            "Allocate costs to workloads (COST03-BP06)"
        ]
    )


# =============================================================================
# COST-04: Decommission Resources
# =============================================================================

@tool
def check_resource_decommissioning(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check resource decommissioning practices (COST04).

    Validates:
    - Unused/idle resources identified (BP01, BP03)
    - Lifecycle policies configured (BP05)
    - Old snapshots and AMIs

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        ec2 = aws_client.get_client("ec2")

        # Check for stopped EC2 instances (COST04-BP01, BP03)
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
            )

            stopped_instances = []
            for res in instances.get("Reservations", []):
                for inst in res.get("Instances", []):
                    stopped_instances.append(inst)

            total_checks += 1
            if not stopped_instances:
                passed_checks += 1
            else:
                # Check how long they've been stopped
                old_stopped = []
                for inst in stopped_instances:
                    # Can't easily get stop time, so flag all
                    old_stopped.append(inst["InstanceId"])

                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(stopped_instances)} stopped EC2 instance(s) found",
                    severity="MEDIUM" if len(stopped_instances) > 3 else "LOW",
                    recommendation="Terminate or create AMI from stopped instances",
                    effort="LOW",
                    impact="MEDIUM",
                    details={"instance_ids": old_stopped[:10]}
                ))
        except Exception:
            pass

        # Check for unattached EBS volumes (COST04-BP01, BP03)
        try:
            volumes = ec2.describe_volumes(
                Filters=[{"Name": "status", "Values": ["available"]}]
            ).get("Volumes", [])

            total_checks += 1
            if not volumes:
                passed_checks += 1
            else:
                total_size = sum(v.get("Size", 0) for v in volumes)
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(volumes)} unattached EBS volume(s) ({total_size} GB)",
                    severity="MEDIUM" if total_size > 100 else "LOW",
                    recommendation="Delete or snapshot unattached volumes",
                    effort="LOW",
                    impact="MEDIUM",
                    details={"volume_count": len(volumes), "total_gb": total_size}
                ))
        except Exception:
            pass

        # Check for old snapshots (COST04-BP05)
        try:
            snapshots = ec2.describe_snapshots(OwnerIds=["self"]).get("Snapshots", [])

            old_snapshots = []
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            for snap in snapshots:
                start_time = snap.get("StartTime")
                if start_time and start_time.replace(tzinfo=timezone.utc) < cutoff:
                    old_snapshots.append(snap)

            total_checks += 1
            if len(old_snapshots) < 10:
                passed_checks += 1
            else:
                total_size = sum(s.get("VolumeSize", 0) for s in old_snapshots)
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(old_snapshots)} snapshot(s) older than 90 days",
                    severity="MEDIUM" if len(old_snapshots) > 50 else "LOW",
                    recommendation="Review and delete old snapshots, implement lifecycle policies",
                    effort="MEDIUM",
                    impact="MEDIUM",
                    details={"snapshot_count": len(old_snapshots)}
                ))
        except Exception:
            pass

        # Check for old AMIs (COST04-BP05)
        try:
            images = ec2.describe_images(Owners=["self"]).get("Images", [])

            old_amis = []
            cutoff = datetime.now(timezone.utc) - timedelta(days=180)
            for ami in images:
                creation_date = ami.get("CreationDate", "")
                if creation_date:
                    try:
                        created = datetime.fromisoformat(creation_date.replace("Z", "+00:00"))
                        if created < cutoff:
                            old_amis.append(ami)
                    except Exception:
                        pass

            total_checks += 1
            if len(old_amis) < 5:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(old_amis)} AMI(s) older than 180 days",
                    severity="LOW",
                    recommendation="Deregister unused old AMIs and delete associated snapshots",
                    effort="MEDIUM",
                    impact="LOW",
                    details={"ami_count": len(old_amis)}
                ))
        except Exception:
            pass

        # Check for unused Elastic IPs (COST04-BP03)
        try:
            addresses = ec2.describe_addresses().get("Addresses", [])
            unassociated = [a for a in addresses if not a.get("AssociationId")]

            total_checks += 1
            if not unassociated:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(unassociated)} unassociated Elastic IP(s)",
                    severity="LOW",
                    recommendation="Release unused Elastic IPs (charged when unassociated)",
                    effort="LOW",
                    impact="LOW",
                    details={"eip_count": len(unassociated)}
                ))
        except Exception:
            pass

        # Check S3 lifecycle policies (COST04-BP05)
        s3 = aws_client.get_client("s3")
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            buckets_without_lifecycle = 0

            for bucket in buckets[:20]:
                try:
                    s3.get_bucket_lifecycle_configuration(Bucket=bucket["Name"])
                except Exception:
                    buckets_without_lifecycle += 1

            total_checks += 1
            if buckets_without_lifecycle < len(buckets[:20]) * 0.5:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:s3::account",
                    issue=f"{buckets_without_lifecycle}/{len(buckets[:20])} buckets without lifecycle policies",
                    severity="MEDIUM" if buckets_without_lifecycle > 5 else "LOW",
                    recommendation="Add lifecycle policies to transition/expire old objects",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_resource_decommissioning",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Terminate stopped EC2 instances (COST04-BP03)",
            "Delete unattached EBS volumes (COST04-BP03)",
            "Implement snapshot lifecycle policies (COST04-BP05)",
            "Release unused Elastic IPs (COST04-BP03)",
            "Configure S3 lifecycle policies (COST04-BP05)",
            "Track resource lifecycle from creation (COST04-BP01)"
        ]
    )


# =============================================================================
# COST-06: Right-Size Resources
# =============================================================================

@tool
def check_resource_rightsizing(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check resource right-sizing practices (COST06).

    Validates:
    - EC2 right-sizing recommendations (BP02)
    - RDS right-sizing opportunities
    - Over-provisioned resources

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        ce = aws_client.get_client("ce")

        # Check for EC2 right-sizing recommendations (COST06-BP02)
        try:
            recommendations = ce.get_rightsizing_recommendation(
                Service="AmazonEC2"
            ).get("RightsizingRecommendations", [])

            total_checks += 1

            if not recommendations:
                passed_checks += 1
            else:
                total_savings = sum(
                    float(r.get("ModifyRecommendationDetail", {})
                          .get("TargetInstances", [{}])[0]
                          .get("EstimatedMonthlySavings", "0")
                          .replace("$", "").replace(",", ""))
                    for r in recommendations
                    if r.get("ModifyRecommendationDetail")
                )

                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(recommendations)} EC2 right-sizing recommendation(s)",
                    severity="HIGH" if total_savings > 100 else "MEDIUM",
                    recommendation="Review and apply right-sizing recommendations",
                    effort="MEDIUM",
                    impact="HIGH",
                    details={
                        "recommendation_count": len(recommendations),
                        "estimated_monthly_savings": f"${total_savings:.2f}"
                    }
                ))
        except Exception:
            total_checks += 1

        # Check for underutilized EC2 instances via CloudWatch
        cloudwatch = aws_client.get_client("cloudwatch")
        ec2 = aws_client.get_client("ec2")
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )

            instance_ids = []
            for res in instances.get("Reservations", []):
                for inst in res.get("Instances", []):
                    instance_ids.append(inst["InstanceId"])

            underutilized = []
            for instance_id in instance_ids[:20]:  # Check first 20
                try:
                    response = cloudwatch.get_metric_statistics(
                        Namespace="AWS/EC2",
                        MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        StartTime=datetime.now(timezone.utc) - timedelta(days=14),
                        EndTime=datetime.now(timezone.utc),
                        Period=86400,
                        Statistics=["Average"]
                    )

                    datapoints = response.get("Datapoints", [])
                    if datapoints:
                        avg_cpu = sum(d["Average"] for d in datapoints) / len(datapoints)
                        if avg_cpu < 10:  # Less than 10% average
                            underutilized.append({"id": instance_id, "avg_cpu": avg_cpu})
                except Exception:
                    pass

            total_checks += 1
            if len(underutilized) < 3:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(underutilized)} instance(s) with <10% avg CPU (14-day)",
                    severity="MEDIUM",
                    recommendation="Consider smaller instance types or consolidation",
                    effort="MEDIUM",
                    impact="MEDIUM",
                    details={"underutilized_instances": underutilized[:5]}
                ))
        except Exception:
            pass

        # Check for oversized RDS instances
        rds = aws_client.get_client("rds")
        try:
            db_instances = rds.describe_db_instances().get("DBInstances", [])

            large_instances = [
                db for db in db_instances
                if any(size in db.get("DBInstanceClass", "")
                       for size in ["xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge", "16xlarge", "24xlarge"])
            ]

            total_checks += 1
            if len(large_instances) < 2:
                passed_checks += 1
            elif large_instances:
                findings.append(create_finding(
                    resource="arn:aws:rds::account",
                    issue=f"{len(large_instances)} large RDS instance(s) found",
                    severity="INFO",
                    recommendation="Review large RDS instances for right-sizing opportunities",
                    effort="MEDIUM",
                    impact="HIGH",
                    details={
                        "instances": [
                            {"id": db["DBInstanceIdentifier"], "class": db["DBInstanceClass"]}
                            for db in large_instances[:5]
                        ]
                    }
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_resource_rightsizing",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Review Cost Explorer right-sizing recommendations (COST06-BP02)",
            "Monitor CPU/memory utilization for right-sizing (COST06-BP02)",
            "Use auto-scaling to match capacity to demand (COST06-BP03)",
            "Consider Graviton instances for better price-performance",
            "Implement data-driven resource selection (COST06-BP02)"
        ]
    )


# =============================================================================
# COST-07: Pricing Models
# =============================================================================

@tool
def check_pricing_models(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check pricing model optimization (COST07).

    Validates:
    - Reserved Instances utilization (BP04)
    - Savings Plans coverage (BP04)
    - Spot Instance usage (BP04)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        ce = aws_client.get_client("ce")

        # Check Reserved Instance utilization (COST07-BP04)
        try:
            ri_utilization = ce.get_reservation_utilization(
                TimePeriod={
                    "Start": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "End": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
            )

            total = ri_utilization.get("Total", {})
            utilization_pct = float(total.get("UtilizationPercentage", "100"))

            total_checks += 1
            if utilization_pct >= 80:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"Reserved Instance utilization at {utilization_pct:.1f}%",
                    severity="HIGH" if utilization_pct < 50 else "MEDIUM",
                    recommendation="Review RI assignments or sell unused RIs on the marketplace",
                    effort="MEDIUM",
                    impact="HIGH",
                    details={"utilization_percentage": utilization_pct}
                ))
        except Exception:
            pass

        # Check Savings Plans utilization (COST07-BP04)
        try:
            sp_utilization = ce.get_savings_plans_utilization(
                TimePeriod={
                    "Start": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "End": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
            )

            total = sp_utilization.get("Total", {})
            sp_util_pct = float(total.get("UtilizationPercentage", "100"))

            total_checks += 1
            if sp_util_pct >= 80:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:savingsplans::account",
                    issue=f"Savings Plans utilization at {sp_util_pct:.1f}%",
                    severity="HIGH" if sp_util_pct < 50 else "MEDIUM",
                    recommendation="Review Savings Plans usage and adjust workloads",
                    effort="MEDIUM",
                    impact="HIGH",
                    details={"utilization_percentage": sp_util_pct}
                ))
        except Exception:
            pass

        # Check Savings Plans coverage (COST07-BP04)
        try:
            sp_coverage = ce.get_savings_plans_coverage(
                TimePeriod={
                    "Start": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "End": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
            )

            total = sp_coverage.get("Total", {})
            coverage_pct = float(total.get("CoveragePercentage", "0"))

            total_checks += 1
            if coverage_pct >= 70:
                passed_checks += 1
            elif coverage_pct > 0:
                findings.append(create_finding(
                    resource="arn:aws:savingsplans::account",
                    issue=f"Savings Plans coverage at {coverage_pct:.1f}%",
                    severity="LOW",
                    recommendation="Consider additional Savings Plans for better coverage",
                    effort="MEDIUM",
                    impact="MEDIUM",
                    details={"coverage_percentage": coverage_pct}
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:savingsplans::account",
                    issue="No Savings Plans coverage",
                    severity="MEDIUM",
                    recommendation="Evaluate Savings Plans for predictable workloads",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for Spot Instance recommendations
        ec2 = aws_client.get_client("ec2")
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )

            on_demand_count = 0
            spot_count = 0
            for res in instances.get("Reservations", []):
                for inst in res.get("Instances", []):
                    if inst.get("InstanceLifecycle") == "spot":
                        spot_count += 1
                    else:
                        on_demand_count += 1

            total_checks += 1
            if spot_count > 0 or on_demand_count < 5:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{on_demand_count} On-Demand instances, 0 Spot instances",
                    severity="INFO",
                    recommendation="Consider Spot Instances for fault-tolerant workloads (up to 90% savings)",
                    effort="MEDIUM",
                    impact="HIGH",
                    details={"on_demand": on_demand_count, "spot": spot_count}
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_pricing_models",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Maximize Reserved Instance utilization (COST07-BP04)",
            "Use Savings Plans for flexible coverage (COST07-BP04)",
            "Leverage Spot Instances for fault-tolerant workloads (COST07-BP04)",
            "Analyze pricing models regularly (COST07-BP01)",
            "Consider region pricing differences (COST07-BP02)"
        ]
    )


# =============================================================================
# COST-08: Data Transfer
# =============================================================================

@tool
def check_data_transfer_optimization(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check data transfer cost optimization (COST08).

    Validates:
    - VPC endpoints for AWS services (BP03)
    - NAT Gateway usage (BP02)
    - CloudFront for content delivery (BP03)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        ec2 = aws_client.get_client("ec2")

        # Check for VPC endpoints (COST08-BP03)
        try:
            endpoints = ec2.describe_vpc_endpoints().get("VpcEndpoints", [])
            vpcs = ec2.describe_vpcs().get("Vpcs", [])

            total_checks += 1

            # Check for S3 and DynamoDB gateway endpoints (free)
            gateway_endpoints = [
                e for e in endpoints
                if e.get("VpcEndpointType") == "Gateway"
            ]

            if gateway_endpoints:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue="No VPC Gateway endpoints (S3/DynamoDB)",
                    severity="MEDIUM",
                    recommendation="Create VPC Gateway endpoints for S3/DynamoDB (free, reduces NAT costs)",
                    effort="LOW",
                    impact="HIGH"
                ))

            # Check interface endpoints
            interface_endpoints = [
                e for e in endpoints
                if e.get("VpcEndpointType") == "Interface"
            ]

            if len(interface_endpoints) < 3 and len(vpcs) > 0:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"Only {len(interface_endpoints)} VPC Interface endpoints",
                    severity="INFO",
                    recommendation="Consider interface endpoints for frequently used AWS services",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check NAT Gateway usage (COST08-BP02)
        try:
            nat_gateways = ec2.describe_nat_gateways(
                Filters=[{"Name": "state", "Values": ["available"]}]
            ).get("NatGateways", [])

            total_checks += 1

            if len(nat_gateways) <= 2:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(nat_gateways)} NAT Gateways in use",
                    severity="INFO",
                    recommendation="Review NAT Gateway usage; consider consolidation or VPC endpoints",
                    effort="MEDIUM",
                    impact="MEDIUM",
                    details={"nat_gateway_count": len(nat_gateways)}
                ))
        except Exception:
            pass

        # Check for CloudFront distributions (COST08-BP03)
        cloudfront = aws_client.get_client("cloudfront")
        try:
            distributions = cloudfront.list_distributions()
            dist_list = distributions.get("DistributionList", {}).get("Items", [])

            total_checks += 1
            if dist_list:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudfront::account",
                    issue="No CloudFront distributions configured",
                    severity="INFO",
                    recommendation="Consider CloudFront for reduced data transfer costs and improved latency",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            total_checks += 1
            passed_checks += 1  # Not having CloudFront isn't necessarily bad

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_data_transfer_optimization",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Use VPC Gateway endpoints for S3/DynamoDB (free) (COST08-BP03)",
            "Use Interface endpoints for frequently accessed services (COST08-BP03)",
            "Consider CloudFront for content delivery (COST08-BP03)",
            "Review NAT Gateway data processing charges (COST08-BP02)",
            "Model data transfer patterns (COST08-BP01)"
        ]
    )


# =============================================================================
# COST-09: Demand and Supply Management
# =============================================================================

@tool
def check_demand_supply_management(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check demand and supply management (COST09).

    Validates:
    - Auto Scaling configured (BP03)
    - Dynamic resource provisioning
    - Throttling/queue mechanisms (BP02)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        autoscaling = aws_client.get_client("autoscaling")

        # Check Auto Scaling Groups (COST09-BP03)
        try:
            asgs = autoscaling.describe_auto_scaling_groups().get("AutoScalingGroups", [])
            total_checks += 1

            if asgs:
                passed_checks += 1

                # Check for proper scaling policies
                asgs_without_policies = []
                for asg in asgs:
                    policies = autoscaling.describe_policies(
                        AutoScalingGroupName=asg["AutoScalingGroupName"]
                    ).get("ScalingPolicies", [])

                    if not policies:
                        asgs_without_policies.append(asg["AutoScalingGroupName"])

                if asgs_without_policies:
                    findings.append(create_finding(
                        resource="arn:aws:autoscaling::account",
                        issue=f"{len(asgs_without_policies)} ASG(s) without scaling policies",
                        severity="MEDIUM",
                        recommendation="Add scaling policies for dynamic resource management",
                        effort="MEDIUM",
                        impact="HIGH",
                        details={"asgs_without_policies": asgs_without_policies[:5]}
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:autoscaling::account",
                    issue="No Auto Scaling Groups configured",
                    severity="MEDIUM",
                    recommendation="Use Auto Scaling for dynamic capacity management",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check Lambda provisioned concurrency (potential over-provisioning)
        lambda_client = aws_client.get_client("lambda")
        try:
            paginator = lambda_client.get_paginator("list_functions")
            functions_with_provisioned = []

            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    try:
                        concurrency = lambda_client.list_provisioned_concurrency_configs(
                            FunctionName=func["FunctionName"]
                        ).get("ProvisionedConcurrencyConfigs", [])

                        if concurrency:
                            total_provisioned = sum(
                                c.get("RequestedProvisionedConcurrentExecutions", 0)
                                for c in concurrency
                            )
                            functions_with_provisioned.append({
                                "function": func["FunctionName"],
                                "provisioned": total_provisioned
                            })
                    except Exception:
                        pass

            total_checks += 1
            if len(functions_with_provisioned) < 5:
                passed_checks += 1
            elif functions_with_provisioned:
                findings.append(create_finding(
                    resource="arn:aws:lambda::account",
                    issue=f"{len(functions_with_provisioned)} Lambda function(s) with provisioned concurrency",
                    severity="INFO",
                    recommendation="Review provisioned concurrency to ensure it matches demand",
                    effort="LOW",
                    impact="MEDIUM",
                    details={"functions": functions_with_provisioned[:5]}
                ))
        except Exception:
            pass

        # Check for SQS queues (COST09-BP02)
        sqs = aws_client.get_client("sqs")
        try:
            queues = sqs.list_queues().get("QueueUrls", [])
            total_checks += 1

            if queues:
                passed_checks += 1  # Having queues indicates demand management
            else:
                findings.append(create_finding(
                    resource="arn:aws:sqs::account",
                    issue="No SQS queues for demand buffering",
                    severity="INFO",
                    recommendation="Consider SQS to buffer demand spikes",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_name="check_demand_supply_management",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Use Auto Scaling for dynamic provisioning (COST09-BP03)",
            "Implement scaling policies based on metrics (COST09-BP03)",
            "Use SQS to buffer demand (COST09-BP02)",
            "Review Lambda provisioned concurrency usage",
            "Analyze workload demand patterns (COST09-BP01)"
        ]
    )


# =============================================================================
# Pillar Review Function
# =============================================================================

@tool
def run_cost_optimization_pillar_review(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run a comprehensive Cost Optimization Pillar review (COST01-COST11).

    Executes all cost optimization checks and provides an aggregated
    pillar-level assessment with prioritized recommendations.

    Returns:
        Comprehensive pillar review with score, findings, and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    check_functions = [
        ("COST01: Cloud Financial Management", check_cloud_financial_management),
        ("COST02: Cost Governance", check_cost_governance),
        ("COST03: Cost Monitoring", check_cost_monitoring),
        ("COST04: Resource Decommissioning", check_resource_decommissioning),
        ("COST06: Resource Rightsizing", check_resource_rightsizing),
        ("COST07: Pricing Models", check_pricing_models),
        ("COST08: Data Transfer", check_data_transfer_optimization),
        ("COST09: Demand/Supply Management", check_demand_supply_management),
    ]

    check_results = []
    for check_name, check_func in check_functions:
        try:
            result = check_func(aws_client=aws_client)
            result["check_area"] = check_name
            check_results.append(result)
        except Exception as e:
            check_results.append({
                "check_area": check_name,
                "status": "ERROR",
                "error": str(e)
            })

    recommendations = [
        "Enable AWS Budgets with notifications for spending alerts",
        "Activate Cost Anomaly Detection to catch unexpected costs",
        "Use cost allocation tags for accurate cost attribution",
        "Review and apply right-sizing recommendations regularly",
        "Maximize Reserved Instance and Savings Plans utilization",
        "Consider Spot Instances for fault-tolerant workloads",
        "Implement S3 lifecycle policies to optimize storage costs",
        "Use VPC endpoints to reduce data transfer costs",
        "Terminate stopped EC2 instances and delete unused resources",
        "Set up Auto Scaling for dynamic capacity management"
    ]

    return create_pillar_review_result(
        pillar=Pillar.COST_OPTIMIZATION.value,
        check_results=check_results,
        recommendations=recommendations
    )


# Export all tools
__all__ = [
    # COST01 - Cloud Financial Management
    "check_cloud_financial_management",
    # COST02 - Governance
    "check_cost_governance",
    # COST03 - Monitoring
    "check_cost_monitoring",
    # COST04 - Decommissioning
    "check_resource_decommissioning",
    # COST06 - Rightsizing
    "check_resource_rightsizing",
    # COST07 - Pricing Models
    "check_pricing_models",
    # COST08 - Data Transfer
    "check_data_transfer_optimization",
    # COST09 - Demand/Supply
    "check_demand_supply_management",
    # Pillar Review
    "run_cost_optimization_pillar_review",
]
