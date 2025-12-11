"""
AWS Well-Architected Framework - Sustainability Pillar Tools.

This module provides automated checks aligned with the Sustainability
Pillar of the AWS Well-Architected Framework (2025 edition).

Sustainability focuses on minimizing environmental impacts of cloud workloads.
The pillar covers 6 questions (SUS01-SUS06) organized into focus areas:

1. Region Selection (SUS01)
2. Alignment to Demand (SUS02)
3. Software and Architecture (SUS03)
4. Data Management (SUS04)
5. Hardware and Services (SUS05)
6. Process and Culture (SUS06)

Reference: https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/
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
# SUS-01: Region Selection
# =============================================================================

@tool
def check_region_sustainability(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check region selection for sustainability (SUS01).

    Validates:
    - Resources in regions with lower carbon intensity (SUS01-BP01)
    - Use of AWS Carbon Footprint Tool

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    # AWS regions with renewable energy commitments (as of 2024)
    # These regions have achieved or are close to 100% renewable energy
    sustainable_regions = [
        "us-west-2",      # Oregon - 100% renewable
        "eu-west-1",      # Ireland - 100% renewable
        "eu-central-1",   # Frankfurt - renewable commitments
        "eu-north-1",     # Stockholm - 100% renewable
        "ca-central-1",   # Canada - high hydro power
        "us-east-2",      # Ohio - renewable investments
    ]

    try:
        ec2 = aws_client.get_client("ec2")

        # Check current region
        current_region = aws_client.region or "unknown"
        total_checks += 1

        if current_region in sustainable_regions:
            passed_checks += 1
        else:
            findings.append(create_finding(
                resource=f"arn:aws:ec2:{current_region}:account",
                issue=f"Primary region ({current_region}) may have higher carbon intensity",
                severity="INFO",
                recommendation="Consider us-west-2, eu-west-1, or eu-north-1 for lower carbon footprint",
                effort="HIGH",
                impact="MEDIUM"
            ))

        # Check for resources across regions
        try:
            # Check EC2 instances
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            ).get("Reservations", [])

            if instances:
                total_checks += 1
                passed_checks += 1  # At least they're consolidated in one region
        except Exception:
            pass

        # Check if Customer Carbon Footprint Tool might be available
        # (This is accessed via AWS Console/Billing, not API)
        total_checks += 1
        findings.append(create_finding(
            resource="arn:aws:billing::account",
            issue="Review AWS Customer Carbon Footprint Tool",
            severity="INFO",
            recommendation="Use AWS Customer Carbon Footprint Tool in Billing console to track emissions",
            effort="LOW",
            impact="MEDIUM"
        ))

    except Exception as e:
        return {"error": str(e), "check_area": "SUS01: Region Selection"}

    return create_check_result(
        pillar=Pillar.SUSTAINABILITY,
        check_name="check_region_sustainability",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Choose regions based on sustainability goals (SUS01-BP01)",
            "Consider carbon intensity of different AWS regions",
            "Use AWS Customer Carbon Footprint Tool for tracking",
            "Balance sustainability with latency requirements",
        ]
    )


# =============================================================================
# SUS-02: Alignment to Demand
# =============================================================================

@tool
def check_demand_alignment(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check alignment of resources to demand (SUS02).

    Validates:
    - Dynamic scaling configured (SUS02-BP01)
    - Unused assets identified (SUS02-BP03)
    - Buffering/throttling implemented (SUS02-BP06)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check Auto Scaling (SUS02-BP01)
        autoscaling = aws_client.get_client("autoscaling")
        try:
            asgs = autoscaling.describe_auto_scaling_groups().get("AutoScalingGroups", [])
            total_checks += 1

            if asgs:
                # Check for scale-in policies
                scale_in_enabled = 0
                for asg in asgs:
                    policies = autoscaling.describe_policies(
                        AutoScalingGroupName=asg["AutoScalingGroupName"]
                    ).get("ScalingPolicies", [])

                    if any(p.get("ScalingAdjustment", 0) < 0 or
                           p.get("PolicyType") == "TargetTrackingScaling"
                           for p in policies):
                        scale_in_enabled += 1

                if scale_in_enabled >= len(asgs) * 0.5:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:autoscaling::account",
                        issue="Auto Scaling groups may not scale in efficiently",
                        severity="MEDIUM",
                        recommendation="Configure target tracking scaling for automatic scale-in",
                        effort="LOW",
                        impact="HIGH"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:autoscaling::account",
                    issue="No Auto Scaling groups configured",
                    severity="MEDIUM",
                    recommendation="Use Auto Scaling to match capacity to demand",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for stopped EC2 instances (SUS02-BP03)
        ec2 = aws_client.get_client("ec2")
        try:
            stopped = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
            ).get("Reservations", [])

            stopped_instances = []
            for r in stopped:
                stopped_instances.extend(r.get("Instances", []))

            total_checks += 1
            if len(stopped_instances) == 0:
                passed_checks += 1
            elif len(stopped_instances) <= 3:
                passed_checks += 0.5
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(stopped_instances)} stopped EC2 instances",
                    severity="LOW",
                    recommendation="Terminate stopped instances or convert to AMIs",
                    effort="LOW",
                    impact="LOW"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(stopped_instances)} stopped EC2 instances consuming resources",
                    severity="MEDIUM",
                    recommendation="Terminate unused instances to reduce resource waste",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for unattached EBS volumes (SUS02-BP03)
        try:
            volumes = ec2.describe_volumes(
                Filters=[{"Name": "status", "Values": ["available"]}]
            ).get("Volumes", [])

            total_checks += 1
            if len(volumes) == 0:
                passed_checks += 1
            else:
                total_size = sum(v.get("Size", 0) for v in volumes)
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"{len(volumes)} unattached EBS volumes ({total_size} GB)",
                    severity="MEDIUM",
                    recommendation="Delete or snapshot unattached volumes",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check Lambda provisioned concurrency usage (SUS02-BP01)
        lambda_client = aws_client.get_client("lambda")
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            if functions:
                total_checks += 1

                # Check for functions with provisioned concurrency
                prov_conc_count = 0
                for f in functions[:20]:  # Check first 20
                    try:
                        prov = lambda_client.list_provisioned_concurrency_configs(
                            FunctionName=f["FunctionName"]
                        ).get("ProvisionedConcurrencyConfigs", [])
                        if prov:
                            prov_conc_count += 1
                    except Exception:
                        pass

                # Provisioned concurrency should be used sparingly
                if prov_conc_count <= len(functions) * 0.2:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:lambda::account",
                        issue=f"{prov_conc_count} functions with provisioned concurrency",
                        severity="INFO",
                        recommendation="Review if provisioned concurrency is needed vs on-demand",
                        effort="LOW",
                        impact="LOW"
                    ))
        except Exception:
            pass

        # Check SQS for buffering (SUS02-BP06)
        sqs = aws_client.get_client("sqs")
        try:
            queues = sqs.list_queues().get("QueueUrls", [])
            total_checks += 1

            if queues:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:sqs::account",
                    issue="No SQS queues for workload buffering",
                    severity="INFO",
                    recommendation="Consider SQS for buffering to flatten demand curves",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "SUS02: Alignment to Demand"}

    return create_check_result(
        pillar=Pillar.SUSTAINABILITY,
        check_name="check_demand_alignment",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=int(passed_checks),
        best_practices=[
            "Scale workload infrastructure dynamically (SUS02-BP01)",
            "Align SLAs with sustainability goals (SUS02-BP02)",
            "Stop creation and maintenance of unused assets (SUS02-BP03)",
            "Optimize geographic placement of workloads (SUS02-BP04)",
            "Implement buffering or throttling to flatten demand (SUS02-BP06)",
        ]
    )


# =============================================================================
# SUS-03: Software and Architecture
# =============================================================================

@tool
def check_software_architecture_efficiency(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check software and architecture patterns for sustainability (SUS03).

    Validates:
    - Async/event-driven patterns used (SUS03-BP01)
    - Unused components identified (SUS03-BP02)
    - Code optimization practices (SUS03-BP03)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check for async patterns - SQS, SNS, EventBridge (SUS03-BP01)
        sqs = aws_client.get_client("sqs")
        sns = aws_client.get_client("sns")
        events = aws_client.get_client("events")

        async_services_used = 0

        try:
            queues = sqs.list_queues().get("QueueUrls", [])
            if queues:
                async_services_used += 1
        except Exception:
            pass

        try:
            topics = sns.list_topics().get("Topics", [])
            if topics:
                async_services_used += 1
        except Exception:
            pass

        try:
            rules = events.list_rules().get("Rules", [])
            if rules:
                async_services_used += 1
        except Exception:
            pass

        total_checks += 1
        if async_services_used >= 2:
            passed_checks += 1
        elif async_services_used == 1:
            passed_checks += 0.5
            findings.append(create_finding(
                resource="arn:aws::account",
                issue="Limited use of async/event-driven patterns",
                severity="INFO",
                recommendation="Consider SQS, SNS, and EventBridge for async processing",
                effort="MEDIUM",
                impact="MEDIUM"
            ))
        else:
            findings.append(create_finding(
                resource="arn:aws::account",
                issue="No async messaging services detected",
                severity="MEDIUM",
                recommendation="Implement event-driven architecture for better resource utilization",
                effort="MEDIUM",
                impact="HIGH"
            ))

        # Check Step Functions for orchestration (SUS03-BP01)
        sfn = aws_client.get_client("stepfunctions")
        try:
            state_machines = sfn.list_state_machines().get("stateMachines", [])
            total_checks += 1

            if state_machines:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:states::account",
                    issue="No Step Functions state machines",
                    severity="INFO",
                    recommendation="Consider Step Functions for workflow orchestration",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check Lambda for serverless compute (SUS03-BP01)
        lambda_client = aws_client.get_client("lambda")
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            total_checks += 1

            if len(functions) >= 5:
                passed_checks += 1
            elif functions:
                passed_checks += 0.5
            else:
                findings.append(create_finding(
                    resource="arn:aws:lambda::account",
                    issue="Limited serverless adoption",
                    severity="INFO",
                    recommendation="Consider Lambda for event-driven workloads",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for old/unused Lambda functions (SUS03-BP02)
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            if functions:
                total_checks += 1
                old_threshold = datetime.now(timezone.utc) - timedelta(days=180)

                old_functions = []
                for f in functions:
                    last_modified = f.get("LastModified", "")
                    if last_modified:
                        try:
                            mod_date = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                            if mod_date < old_threshold:
                                old_functions.append(f)
                        except Exception:
                            pass

                if len(old_functions) > len(functions) * 0.3:
                    findings.append(create_finding(
                        resource="arn:aws:lambda::account",
                        issue=f"{len(old_functions)} Lambda functions not modified in 6+ months",
                        severity="LOW",
                        recommendation="Review and remove unused Lambda functions",
                        effort="LOW",
                        impact="LOW"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check API Gateway for efficient APIs
        apigateway = aws_client.get_client("apigatewayv2")
        try:
            apis = apigateway.get_apis().get("Items", [])
            total_checks += 1

            http_apis = [a for a in apis if a.get("ProtocolType") == "HTTP"]

            if http_apis:
                passed_checks += 1  # HTTP APIs are more efficient than REST APIs
            elif apis:
                passed_checks += 0.5
                findings.append(create_finding(
                    resource="arn:aws:apigateway::account",
                    issue="Using REST APIs instead of HTTP APIs",
                    severity="INFO",
                    recommendation="Consider HTTP APIs for lower latency and cost",
                    effort="MEDIUM",
                    impact="LOW"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "SUS03: Software and Architecture"}

    return create_check_result(
        pillar=Pillar.SUSTAINABILITY,
        check_name="check_software_architecture_efficiency",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=int(passed_checks),
        best_practices=[
            "Optimize for asynchronous and scheduled jobs (SUS03-BP01)",
            "Remove or refactor unused components (SUS03-BP02)",
            "Optimize code that consumes most resources (SUS03-BP03)",
            "Optimize impact on devices and equipment (SUS03-BP04)",
            "Use patterns that support data access patterns (SUS03-BP05)",
        ]
    )


# =============================================================================
# SUS-04: Data Management
# =============================================================================

@tool
def check_data_sustainability(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check data management for sustainability (SUS04).

    Validates:
    - Data lifecycle policies (SUS04-BP03)
    - Redundant data removal (SUS04-BP05)
    - Efficient storage usage (SUS04-BP02)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        s3 = aws_client.get_client("s3")

        # Check S3 lifecycle policies (SUS04-BP03)
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            if buckets:
                total_checks += 1
                buckets_with_lifecycle = 0

                for bucket in buckets[:20]:  # Check first 20
                    try:
                        lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=bucket["Name"])
                        if lifecycle.get("Rules"):
                            buckets_with_lifecycle += 1
                    except Exception:
                        pass  # No lifecycle = not configured

                lifecycle_pct = buckets_with_lifecycle / min(len(buckets), 20)
                if lifecycle_pct >= 0.5:
                    passed_checks += 1
                elif lifecycle_pct > 0:
                    passed_checks += 0.5
                    findings.append(create_finding(
                        resource="arn:aws:s3::account",
                        issue=f"Only {buckets_with_lifecycle}/{min(len(buckets), 20)} buckets have lifecycle policies",
                        severity="MEDIUM",
                        recommendation="Configure lifecycle policies to transition/expire data",
                        effort="LOW",
                        impact="HIGH"
                    ))
                else:
                    findings.append(create_finding(
                        resource="arn:aws:s3::account",
                        issue="No S3 lifecycle policies configured",
                        severity="MEDIUM",
                        recommendation="Implement lifecycle policies to reduce storage footprint",
                        effort="LOW",
                        impact="HIGH"
                    ))
        except Exception:
            pass

        # Check S3 Intelligent-Tiering (SUS04-BP02)
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            if buckets:
                total_checks += 1
                intelligent_tiering = 0

                for bucket in buckets[:10]:
                    try:
                        configs = s3.list_bucket_intelligent_tiering_configurations(
                            Bucket=bucket["Name"]
                        ).get("IntelligentTieringConfigurationList", [])
                        if configs:
                            intelligent_tiering += 1
                    except Exception:
                        pass

                if intelligent_tiering > 0:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:s3::account",
                        issue="S3 Intelligent-Tiering not configured",
                        severity="INFO",
                        recommendation="Use Intelligent-Tiering for automatic storage optimization",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check for incomplete multipart uploads (SUS04-BP05)
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            total_incomplete = 0

            for bucket in buckets[:10]:
                try:
                    uploads = s3.list_multipart_uploads(Bucket=bucket["Name"]).get("Uploads", [])
                    total_incomplete += len(uploads)
                except Exception:
                    pass

            total_checks += 1
            if total_incomplete == 0:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:s3::account",
                    issue=f"{total_incomplete} incomplete multipart uploads",
                    severity="LOW",
                    recommendation="Configure lifecycle rules to abort incomplete uploads",
                    effort="LOW",
                    impact="LOW"
                ))
        except Exception:
            pass

        # Check EBS volume types (SUS04-BP02)
        ec2 = aws_client.get_client("ec2")
        try:
            volumes = ec2.describe_volumes().get("Volumes", [])
            if volumes:
                total_checks += 1

                # gp3 is more efficient than gp2
                gp2_volumes = [v for v in volumes if v.get("VolumeType") == "gp2"]

                if len(gp2_volumes) > len(volumes) * 0.3:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue=f"{len(gp2_volumes)} EBS volumes using gp2 (less efficient)",
                        severity="MEDIUM",
                        recommendation="Migrate gp2 volumes to gp3 for better efficiency",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check RDS storage optimization (SUS04-BP02)
        rds = aws_client.get_client("rds")
        try:
            instances = rds.describe_db_instances().get("DBInstances", [])
            if instances:
                total_checks += 1

                # Check for storage autoscaling
                autoscaling_enabled = [
                    i for i in instances
                    if i.get("MaxAllocatedStorage")
                ]

                if len(autoscaling_enabled) >= len(instances) * 0.5:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:rds::account",
                        issue="RDS storage autoscaling not widely enabled",
                        severity="INFO",
                        recommendation="Enable storage autoscaling to avoid over-provisioning",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check DynamoDB on-demand mode (SUS04-BP04)
        dynamodb = aws_client.get_client("dynamodb")
        try:
            tables = dynamodb.list_tables().get("TableNames", [])
            if tables:
                total_checks += 1
                on_demand = 0

                for table in tables[:10]:
                    try:
                        desc = dynamodb.describe_table(TableName=table).get("Table", {})
                        if desc.get("BillingModeSummary", {}).get("BillingMode") == "PAY_PER_REQUEST":
                            on_demand += 1
                    except Exception:
                        pass

                # On-demand can reduce waste for variable workloads
                if on_demand > 0:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:dynamodb::account",
                        issue="DynamoDB tables using provisioned capacity",
                        severity="INFO",
                        recommendation="Consider on-demand mode for variable workloads",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "SUS04: Data Management"}

    return create_check_result(
        pillar=Pillar.SUSTAINABILITY,
        check_name="check_data_sustainability",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=int(passed_checks),
        best_practices=[
            "Implement a data classification policy (SUS04-BP01)",
            "Use technologies that support data access patterns (SUS04-BP02)",
            "Use policies to manage dataset lifecycle (SUS04-BP03)",
            "Use elasticity for storage expansion (SUS04-BP04)",
            "Remove unneeded or redundant data (SUS04-BP05)",
            "Minimize data movement across networks (SUS04-BP07)",
        ]
    )


# =============================================================================
# SUS-05: Hardware and Services
# =============================================================================

@tool
def check_hardware_efficiency(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check hardware and service efficiency for sustainability (SUS05).

    Validates:
    - Minimum hardware to meet needs (SUS05-BP01)
    - Efficient instance types used (SUS05-BP02)
    - Managed services adoption (SUS05-BP03)

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

        # Check for Graviton instances (SUS05-BP02)
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            ).get("Reservations", [])

            running_instances = []
            for r in instances:
                running_instances.extend(r.get("Instances", []))

            if running_instances:
                total_checks += 1

                # Graviton (ARM) instances are more energy-efficient
                graviton_patterns = ["6g", "7g", ".g"]
                graviton_instances = [
                    i for i in running_instances
                    if any(g in i.get("InstanceType", "") for g in graviton_patterns)
                ]

                graviton_pct = len(graviton_instances) / len(running_instances)
                if graviton_pct >= 0.3:
                    passed_checks += 1
                elif graviton_pct > 0:
                    passed_checks += 0.5
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue=f"Only {len(graviton_instances)}/{len(running_instances)} instances are Graviton",
                        severity="INFO",
                        recommendation="Migrate more workloads to Graviton for better energy efficiency",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
                else:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue="No Graviton (ARM) instances in use",
                        severity="MEDIUM",
                        recommendation="Graviton instances offer up to 60% less energy per unit compute",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
        except Exception:
            pass

        # Check for over-sized instances (SUS05-BP01)
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            ).get("Reservations", [])

            running_instances = []
            for r in instances:
                running_instances.extend(r.get("Instances", []))

            if running_instances:
                total_checks += 1

                # Check for very large instances
                large_patterns = ["xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge", "16xlarge", "24xlarge"]
                very_large = [
                    i for i in running_instances
                    if any(p in i.get("InstanceType", "") for p in ["8xlarge", "12xlarge", "16xlarge", "24xlarge", "metal"])
                ]

                if len(very_large) > len(running_instances) * 0.2:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue=f"{len(very_large)} very large instances (8xlarge+)",
                        severity="INFO",
                        recommendation="Review if large instances are fully utilized",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check Compute Optimizer enrollment (SUS05-BP01)
        try:
            compute_optimizer = aws_client.get_client("compute-optimizer")
            status = compute_optimizer.get_enrollment_status()
            total_checks += 1

            if status.get("status") == "Active":
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:compute-optimizer::account",
                    issue="AWS Compute Optimizer not enabled",
                    severity="MEDIUM",
                    recommendation="Enable Compute Optimizer to identify right-sizing opportunities",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check managed service usage (SUS05-BP03)
        managed_services = 0

        # Lambda
        lambda_client = aws_client.get_client("lambda")
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            if functions:
                managed_services += 1
        except Exception:
            pass

        # Fargate
        ecs = aws_client.get_client("ecs")
        try:
            clusters = ecs.list_clusters().get("clusterArns", [])
            for cluster in clusters[:5]:
                services = ecs.list_services(cluster=cluster).get("serviceArns", [])
                for svc_arn in services[:3]:
                    svc = ecs.describe_services(cluster=cluster, services=[svc_arn]).get("services", [])
                    if svc and svc[0].get("launchType") == "FARGATE":
                        managed_services += 1
                        break
        except Exception:
            pass

        # RDS
        rds = aws_client.get_client("rds")
        try:
            instances = rds.describe_db_instances().get("DBInstances", [])
            if instances:
                managed_services += 1
        except Exception:
            pass

        # DynamoDB
        dynamodb = aws_client.get_client("dynamodb")
        try:
            tables = dynamodb.list_tables().get("TableNames", [])
            if tables:
                managed_services += 1
        except Exception:
            pass

        total_checks += 1
        if managed_services >= 3:
            passed_checks += 1
        elif managed_services >= 1:
            passed_checks += 0.5
            findings.append(create_finding(
                resource="arn:aws::account",
                issue="Limited managed service adoption",
                severity="INFO",
                recommendation="Use managed services to benefit from AWS infrastructure optimization",
                effort="MEDIUM",
                impact="MEDIUM"
            ))
        else:
            findings.append(create_finding(
                resource="arn:aws::account",
                issue="Minimal managed service usage",
                severity="MEDIUM",
                recommendation="Adopt Lambda, Fargate, RDS, DynamoDB for better resource efficiency",
                effort="HIGH",
                impact="HIGH"
            ))

        # Check Spot instance usage (cost and sustainability)
        try:
            spot_requests = ec2.describe_spot_instance_requests().get("SpotInstanceRequests", [])
            total_checks += 1

            if spot_requests:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue="No Spot instances in use",
                    severity="INFO",
                    recommendation="Use Spot instances for fault-tolerant workloads",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "SUS05: Hardware and Services"}

    return create_check_result(
        pillar=Pillar.SUSTAINABILITY,
        check_name="check_hardware_efficiency",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=int(passed_checks),
        best_practices=[
            "Use the minimum amount of hardware (SUS05-BP01)",
            "Use instance types with least environmental impact (SUS05-BP02)",
            "Use managed services for better efficiency (SUS05-BP03)",
            "Optimize use of hardware accelerators (SUS05-BP04)",
        ]
    )


# =============================================================================
# SUS-06: Process and Culture
# =============================================================================

@tool
def check_sustainability_culture(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check organizational processes for sustainability (SUS06).

    Validates:
    - Sustainability goals communicated (SUS06-BP01)
    - Workloads kept up-to-date (SUS06-BP03)
    - Build environment efficiency (SUS06-BP04)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check for tagging strategy (indicates sustainability tracking) (SUS06-BP01)
        ec2 = aws_client.get_client("ec2")
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            ).get("Reservations", [])

            running_instances = []
            for r in instances:
                running_instances.extend(r.get("Instances", []))

            if running_instances:
                total_checks += 1

                # Check for environment/cost tags
                tagged_instances = 0
                for i in running_instances:
                    tags = {t["Key"]: t["Value"] for t in i.get("Tags", [])}
                    if any(k.lower() in ["environment", "env", "project", "cost-center", "owner"]
                           for k in tags.keys()):
                        tagged_instances += 1

                if tagged_instances >= len(running_instances) * 0.7:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue=f"Only {tagged_instances}/{len(running_instances)} instances properly tagged",
                        severity="MEDIUM",
                        recommendation="Implement tagging strategy for resource tracking and optimization",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check Lambda runtime versions (SUS06-BP03)
        lambda_client = aws_client.get_client("lambda")
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            if functions:
                total_checks += 1

                # Check for current runtimes
                outdated_runtimes = ["python3.7", "python3.6", "nodejs12.x", "nodejs10.x", "ruby2.5", "java8"]
                outdated = [f for f in functions if f.get("Runtime", "") in outdated_runtimes]

                if len(outdated) > len(functions) * 0.1:
                    findings.append(create_finding(
                        resource="arn:aws:lambda::account",
                        issue=f"{len(outdated)} Lambda functions on outdated runtimes",
                        severity="MEDIUM",
                        recommendation="Update to latest runtimes for security and efficiency",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check CodeBuild for build efficiency (SUS06-BP04)
        codebuild = aws_client.get_client("codebuild")
        try:
            projects = codebuild.list_projects().get("projects", [])
            total_checks += 1

            if projects:
                # Check for caching configuration
                cached_projects = 0
                for proj in projects[:10]:
                    try:
                        details = codebuild.batch_get_projects(names=[proj]).get("projects", [])
                        if details and details[0].get("cache", {}).get("type") != "NO_CACHE":
                            cached_projects += 1
                    except Exception:
                        pass

                if cached_projects >= len(projects[:10]) * 0.5:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:codebuild::account",
                        issue="CodeBuild projects not using caching",
                        severity="INFO",
                        recommendation="Enable build caching to reduce build time and resources",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
            else:
                passed_checks += 1  # No CodeBuild is fine
        except Exception:
            pass

        # Check AWS Config for compliance tracking (SUS06-BP02)
        config = aws_client.get_client("config")
        try:
            recorders = config.describe_configuration_recorders().get("ConfigurationRecorders", [])
            total_checks += 1

            if recorders:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:config::account",
                    issue="AWS Config not enabled",
                    severity="MEDIUM",
                    recommendation="Enable AWS Config to track resource configuration and compliance",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for Cost Allocation Tags (SUS06-BP01)
        ce = aws_client.get_client("ce")
        try:
            tags = ce.get_cost_and_usage(
                TimePeriod={
                    "Start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                    "End": datetime.now().strftime("%Y-%m-%d")
                },
                Granularity="MONTHLY",
                Metrics=["BlendedCost"],
                GroupBy=[{"Type": "TAG", "Key": "Environment"}]
            )
            total_checks += 1

            if tags.get("ResultsByTime", [{}])[0].get("Groups"):
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ce::account",
                    issue="Cost allocation tags not effectively used",
                    severity="INFO",
                    recommendation="Enable and use cost allocation tags for tracking",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check Well-Architected Tool usage (SUS06-BP02)
        wa = aws_client.get_client("wellarchitected")
        try:
            workloads = wa.list_workloads().get("WorkloadSummaries", [])
            total_checks += 1

            if workloads:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:wellarchitected::account",
                    issue="No workloads in Well-Architected Tool",
                    severity="INFO",
                    recommendation="Use Well-Architected Tool for sustainability reviews",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "SUS06: Process and Culture"}

    return create_check_result(
        pillar=Pillar.SUSTAINABILITY,
        check_name="check_sustainability_culture",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=int(passed_checks),
        best_practices=[
            "Communicate and cascade sustainability goals (SUS06-BP01)",
            "Adopt methods for rapid sustainability improvements (SUS06-BP02)",
            "Keep workloads up-to-date (SUS06-BP03)",
            "Increase utilization of build environments (SUS06-BP04)",
        ]
    )


# =============================================================================
# Pillar Review
# =============================================================================

@tool
def run_sustainability_pillar_review(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run comprehensive Sustainability pillar review.

    Executes all SUS01-SUS06 checks and aggregates results into a
    pillar-level assessment with prioritized recommendations.

    Returns:
        Complete pillar review with scores, findings, and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    check_functions = [
        ("check_region_sustainability", check_region_sustainability),
        ("check_demand_alignment", check_demand_alignment),
        ("check_software_architecture_efficiency", check_software_architecture_efficiency),
        ("check_data_sustainability", check_data_sustainability),
        ("check_hardware_efficiency", check_hardware_efficiency),
        ("check_sustainability_culture", check_sustainability_culture),
    ]

    check_results = []
    for name, func in check_functions:
        try:
            result = func(aws_client=aws_client)
            check_results.append(result)
        except Exception as e:
            check_results.append({
                "error": str(e),
                "check_area": name
            })

    recommendations = [
        "Use AWS Customer Carbon Footprint Tool to track emissions",
        "Migrate to Graviton instances for up to 60% better energy efficiency",
        "Implement Auto Scaling to match capacity to actual demand",
        "Configure S3 lifecycle policies to tier and expire data",
        "Use managed services (Lambda, Fargate, RDS) for better efficiency",
        "Enable Compute Optimizer for rightsizing recommendations",
        "Adopt event-driven architecture with SQS/SNS/EventBridge",
        "Delete unused resources (stopped instances, unattached volumes)",
        "Use S3 Intelligent-Tiering for automatic storage optimization",
        "Keep workloads and runtimes up-to-date",
    ]

    return create_pillar_review_result(
        pillar=Pillar.SUSTAINABILITY,
        check_results=check_results,
        recommendations=recommendations
    )
