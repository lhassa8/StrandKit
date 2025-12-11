"""
AWS Well-Architected Framework - Performance Efficiency Pillar Tools.

This module provides automated checks aligned with the Performance Efficiency
Pillar of the AWS Well-Architected Framework (2025 edition).

Performance Efficiency focuses on using cloud resources efficiently to meet
requirements and maintaining that efficiency as demand changes. The pillar
covers 5 questions (PERF01-PERF05) organized into focus areas:

1. Architecture Selection (PERF01)
2. Compute Selection (PERF02)
3. Data Management (PERF03)
4. Network Selection (PERF04)
5. Process and Culture (PERF05)

Reference: https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/
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
# PERF-01: Architecture Selection
# =============================================================================

@tool
def check_architecture_selection(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check architecture selection practices (PERF01).

    Validates:
    - Use of managed services (PERF01-BP01, BP02)
    - Cost-performance optimization (PERF01-BP03)
    - Reference architectures followed (PERF01-BP05)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check for managed service adoption (PERF01-BP01)
        # Lambda (serverless compute)
        lambda_client = aws_client.get_client("lambda")
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            total_checks += 1
            if functions:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:lambda::account",
                    issue="No Lambda functions - consider serverless for event-driven workloads",
                    severity="INFO",
                    recommendation="Evaluate serverless compute for appropriate workloads",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for DynamoDB usage (managed NoSQL)
        dynamodb = aws_client.get_client("dynamodb")
        try:
            tables = dynamodb.list_tables().get("TableNames", [])
            total_checks += 1
            if tables:
                passed_checks += 1
        except Exception:
            pass

        # Check for ElastiCache usage (managed caching)
        elasticache = aws_client.get_client("elasticache")
        try:
            clusters = elasticache.describe_cache_clusters().get("CacheClusters", [])
            total_checks += 1
            if clusters:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:elasticache::account",
                    issue="No ElastiCache clusters configured",
                    severity="INFO",
                    recommendation="Consider caching for frequently accessed data",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for SQS usage (managed queuing)
        sqs = aws_client.get_client("sqs")
        try:
            queues = sqs.list_queues().get("QueueUrls", [])
            total_checks += 1
            if queues:
                passed_checks += 1
        except Exception:
            pass

        # Check CloudWatch for performance metrics (PERF01-BP06, BP07)
        cloudwatch = aws_client.get_client("cloudwatch")
        try:
            alarms = cloudwatch.describe_alarms().get("MetricAlarms", [])
            perf_alarms = [
                a for a in alarms
                if any(m in a.get("MetricName", "").lower()
                       for m in ["latency", "duration", "response", "throughput"])
            ]
            total_checks += 1
            if perf_alarms:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No performance-focused CloudWatch alarms",
                    severity="MEDIUM",
                    recommendation="Create alarms for latency, throughput, and response time",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "PERF01: Architecture Selection"}

    return create_check_result(
        pillar=Pillar.PERFORMANCE_EFFICIENCY,
        check_name="check_architecture_selection",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Learn about available cloud services and features (PERF01-BP01)",
            "Use cloud provider guidance for architecture patterns (PERF01-BP02)",
            "Factor cost into architectural decisions (PERF01-BP03)",
            "Use benchmarking to drive decisions (PERF01-BP06)",
            "Use a data-driven approach for choices (PERF01-BP07)",
        ]
    )


# =============================================================================
# PERF-02: Compute Selection
# =============================================================================

@tool
def check_compute_selection(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check compute resource selection and usage (PERF02).

    Validates:
    - Right-sized instances (PERF02-BP04)
    - Dynamic scaling configured (PERF02-BP05)
    - GPU/accelerator usage where appropriate (PERF02-BP06)
    - Compute metrics collected (PERF02-BP03)

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

        # Check EC2 instance types and utilization (PERF02-BP01, BP04)
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            ).get("Reservations", [])

            running_instances = []
            for r in instances:
                running_instances.extend(r.get("Instances", []))

            if running_instances:
                total_checks += 1

                # Check for older generation instances
                old_gen_types = ["t2.", "m4.", "c4.", "r4.", "i2.", "d2."]
                old_instances = [
                    i for i in running_instances
                    if any(i.get("InstanceType", "").startswith(t) for t in old_gen_types)
                ]

                if old_instances:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue=f"{len(old_instances)} instances using older generation types",
                        severity="MEDIUM",
                        recommendation="Upgrade to current generation instances (t3/m5/c5/r5) for better performance/cost",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
                else:
                    passed_checks += 1

                # Check for Graviton/ARM instances (PERF02-BP06)
                total_checks += 1
                graviton_types = [".g", "6g", "7g"]
                graviton_instances = [
                    i for i in running_instances
                    if any(g in i.get("InstanceType", "") for g in graviton_types)
                ]

                if graviton_instances:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue="No Graviton (ARM) instances in use",
                        severity="INFO",
                        recommendation="Consider Graviton instances for up to 40% better price-performance",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
        except Exception:
            pass

        # Check Auto Scaling configuration (PERF02-BP05)
        autoscaling = aws_client.get_client("autoscaling")
        try:
            asgs = autoscaling.describe_auto_scaling_groups().get("AutoScalingGroups", [])
            total_checks += 1

            if asgs:
                # Check for scaling policies
                has_scaling_policies = False
                for asg in asgs:
                    policies = autoscaling.describe_policies(
                        AutoScalingGroupName=asg["AutoScalingGroupName"]
                    ).get("ScalingPolicies", [])
                    if policies:
                        has_scaling_policies = True
                        break

                if has_scaling_policies:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:autoscaling::account",
                        issue="Auto Scaling groups without scaling policies",
                        severity="MEDIUM",
                        recommendation="Configure target tracking or step scaling policies",
                        effort="LOW",
                        impact="HIGH"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:autoscaling::account",
                    issue="No Auto Scaling groups configured",
                    severity="MEDIUM",
                    recommendation="Use Auto Scaling for dynamic capacity management",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check Lambda configuration (PERF02-BP04)
        lambda_client = aws_client.get_client("lambda")
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            if functions:
                total_checks += 1

                # Check for functions with default memory
                default_memory_funcs = [
                    f for f in functions
                    if f.get("MemorySize") == 128
                ]

                if len(default_memory_funcs) > len(functions) * 0.5:
                    findings.append(create_finding(
                        resource="arn:aws:lambda::account",
                        issue=f"{len(default_memory_funcs)}/{len(functions)} Lambda functions use default 128MB memory",
                        severity="MEDIUM",
                        recommendation="Right-size Lambda memory using AWS Lambda Power Tuning",
                        effort="LOW",
                        impact="HIGH"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check for Compute Optimizer recommendations
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
                    recommendation="Enable Compute Optimizer for rightsizing recommendations",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "PERF02: Compute Selection"}

    return create_check_result(
        pillar=Pillar.PERFORMANCE_EFFICIENCY,
        check_name="check_compute_selection",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Select the best compute options for your workload (PERF02-BP01)",
            "Understand available compute configuration options (PERF02-BP02)",
            "Collect compute-related metrics (PERF02-BP03)",
            "Configure and right-size compute resources (PERF02-BP04)",
            "Scale compute resources dynamically (PERF02-BP05)",
            "Use hardware-based compute accelerators (PERF02-BP06)",
        ]
    )


# =============================================================================
# PERF-03: Data Management
# =============================================================================

@tool
def check_data_store_performance(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check data store performance configuration (PERF03).

    Validates:
    - Purpose-built data stores used (PERF03-BP01)
    - Data store configuration optimized (PERF03-BP02)
    - Performance metrics collected (PERF03-BP03)
    - Caching implemented (PERF03-BP05)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check RDS configuration (PERF03-BP01, BP02)
        rds = aws_client.get_client("rds")
        try:
            instances = rds.describe_db_instances().get("DBInstances", [])
            if instances:
                total_checks += 1

                # Check for Performance Insights (PERF03-BP03)
                pi_disabled = [
                    i for i in instances
                    if not i.get("PerformanceInsightsEnabled", False)
                ]

                if pi_disabled:
                    findings.append(create_finding(
                        resource="arn:aws:rds::account",
                        issue=f"{len(pi_disabled)}/{len(instances)} RDS instances without Performance Insights",
                        severity="MEDIUM",
                        recommendation="Enable Performance Insights for database performance analysis",
                        effort="LOW",
                        impact="HIGH"
                    ))
                else:
                    passed_checks += 1

                # Check storage type
                total_checks += 1
                gp2_instances = [
                    i for i in instances
                    if i.get("StorageType") == "gp2"
                ]

                if gp2_instances:
                    findings.append(create_finding(
                        resource="arn:aws:rds::account",
                        issue=f"{len(gp2_instances)} RDS instances using gp2 storage",
                        severity="MEDIUM",
                        recommendation="Upgrade to gp3 storage for better performance and lower cost",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
                else:
                    passed_checks += 1

                # Check for Multi-AZ
                total_checks += 1
                single_az = [
                    i for i in instances
                    if not i.get("MultiAZ", False) and "prod" in i.get("DBInstanceIdentifier", "").lower()
                ]

                if single_az:
                    findings.append(create_finding(
                        resource="arn:aws:rds::account",
                        issue=f"{len(single_az)} production RDS instances without Multi-AZ",
                        severity="MEDIUM",
                        recommendation="Enable Multi-AZ for production databases",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check DynamoDB configuration (PERF03-BP01, BP02)
        dynamodb = aws_client.get_client("dynamodb")
        try:
            tables = dynamodb.list_tables().get("TableNames", [])
            if tables:
                total_checks += 1
                on_demand_tables = 0

                for table_name in tables[:10]:  # Check first 10
                    try:
                        table = dynamodb.describe_table(TableName=table_name).get("Table", {})
                        if table.get("BillingModeSummary", {}).get("BillingMode") == "PAY_PER_REQUEST":
                            on_demand_tables += 1
                    except Exception:
                        pass

                # On-demand is often better for variable workloads
                if on_demand_tables > 0 or len(tables) == 0:
                    passed_checks += 1
        except Exception:
            pass

        # Check S3 configuration (PERF03-BP02)
        s3 = aws_client.get_client("s3")
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            if buckets:
                total_checks += 1

                # Check for Transfer Acceleration on large buckets
                accel_enabled = 0
                for bucket in buckets[:10]:
                    try:
                        accel = s3.get_bucket_accelerate_configuration(Bucket=bucket["Name"])
                        if accel.get("Status") == "Enabled":
                            accel_enabled += 1
                    except Exception:
                        pass

                # This is informational - not all buckets need acceleration
                passed_checks += 1
        except Exception:
            pass

        # Check ElastiCache for caching (PERF03-BP05)
        elasticache = aws_client.get_client("elasticache")
        try:
            clusters = elasticache.describe_cache_clusters().get("CacheClusters", [])
            total_checks += 1

            if clusters:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:elasticache::account",
                    issue="No caching layer configured",
                    severity="MEDIUM",
                    recommendation="Implement ElastiCache for frequently accessed data",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check CloudFront for content caching
        cloudfront = aws_client.get_client("cloudfront")
        try:
            distributions = cloudfront.list_distributions().get("DistributionList", {}).get("Items", [])
            total_checks += 1

            if distributions:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudfront::account",
                    issue="No CloudFront distributions configured",
                    severity="INFO",
                    recommendation="Consider CloudFront for content delivery and edge caching",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "PERF03: Data Management"}

    return create_check_result(
        pillar=Pillar.PERFORMANCE_EFFICIENCY,
        check_name="check_data_store_performance",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Use purpose-built data stores (PERF03-BP01)",
            "Evaluate and optimize data store configuration (PERF03-BP02)",
            "Collect and record data store performance metrics (PERF03-BP03)",
            "Implement strategies to improve query performance (PERF03-BP04)",
            "Implement caching for frequently accessed data (PERF03-BP05)",
        ]
    )


# =============================================================================
# PERF-04: Network Selection
# =============================================================================

@tool
def check_network_performance(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check network performance configuration (PERF04).

    Validates:
    - Network optimization features used (PERF04-BP02)
    - Load balancing configured (PERF04-BP04)
    - Network metrics monitored (PERF04-BP07)
    - Workload placement optimized (PERF04-BP06)

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

        # Check VPC configuration (PERF04-BP01)
        try:
            vpcs = ec2.describe_vpcs().get("Vpcs", [])
            total_checks += 1

            if vpcs:
                passed_checks += 1

                # Check for VPC Endpoints (reduce data transfer)
                endpoints = ec2.describe_vpc_endpoints().get("VpcEndpoints", [])
                total_checks += 1

                if endpoints:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue="No VPC Endpoints configured",
                        severity="MEDIUM",
                        recommendation="Use VPC Endpoints for AWS service access to reduce latency",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check Enhanced Networking (PERF04-BP02)
        try:
            instances = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            ).get("Reservations", [])

            running_instances = []
            for r in instances:
                running_instances.extend(r.get("Instances", []))

            if running_instances:
                total_checks += 1

                # Check for ENA support
                ena_disabled = [
                    i for i in running_instances
                    if not i.get("EnaSupport", False)
                ]

                if len(ena_disabled) > len(running_instances) * 0.2:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue=f"{len(ena_disabled)} instances without Enhanced Networking (ENA)",
                        severity="MEDIUM",
                        recommendation="Enable Enhanced Networking for better network performance",
                        effort="LOW",
                        impact="HIGH"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check Load Balancers (PERF04-BP04)
        elbv2 = aws_client.get_client("elbv2")
        try:
            lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])
            total_checks += 1

            if lbs:
                passed_checks += 1

                # Check for ALB vs CLB (ALB is more performant)
                albs = [lb for lb in lbs if lb.get("Type") == "application"]
                nlbs = [lb for lb in lbs if lb.get("Type") == "network"]

                if albs or nlbs:
                    total_checks += 1
                    passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:elasticloadbalancing::account",
                    issue="No load balancers configured",
                    severity="INFO",
                    recommendation="Use load balancing for distributing traffic across resources",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check CloudFront for edge optimization (PERF04-BP06)
        cloudfront = aws_client.get_client("cloudfront")
        try:
            distributions = cloudfront.list_distributions().get("DistributionList", {}).get("Items", [])
            total_checks += 1

            if distributions:
                passed_checks += 1

                # Check for optimized caching
                optimized = 0
                for dist in distributions:
                    if dist.get("DefaultCacheBehavior", {}).get("Compress", False):
                        optimized += 1

                if optimized < len(distributions):
                    findings.append(create_finding(
                        resource="arn:aws:cloudfront::account",
                        issue=f"{len(distributions) - optimized} CloudFront distributions without compression",
                        severity="LOW",
                        recommendation="Enable compression in CloudFront for faster content delivery",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check Global Accelerator
        try:
            global_accel = aws_client.get_client("globalaccelerator")
            accelerators = global_accel.list_accelerators().get("Accelerators", [])
            total_checks += 1

            if accelerators:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:globalaccelerator::account",
                    issue="No Global Accelerator configured",
                    severity="INFO",
                    recommendation="Consider Global Accelerator for global applications",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e), "check_area": "PERF04: Network Selection"}

    return create_check_result(
        pillar=Pillar.PERFORMANCE_EFFICIENCY,
        check_name="check_network_performance",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Understand networking impact on performance (PERF04-BP01)",
            "Evaluate available networking features (PERF04-BP02)",
            "Use load balancing to distribute traffic (PERF04-BP04)",
            "Choose network protocols to improve performance (PERF04-BP05)",
            "Choose workload location based on network requirements (PERF04-BP06)",
            "Optimize network configuration based on metrics (PERF04-BP07)",
        ]
    )


# =============================================================================
# PERF-05: Process and Culture
# =============================================================================

@tool
def check_performance_process(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check performance management processes (PERF05).

    Validates:
    - KPIs established (PERF05-BP01)
    - Monitoring solutions in place (PERF05-BP02)
    - Workloads kept up-to-date (PERF05-BP06)
    - Metrics reviewed regularly (PERF05-BP07)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        cloudwatch = aws_client.get_client("cloudwatch")

        # Check for performance dashboards (PERF05-BP01, BP02)
        try:
            dashboards = cloudwatch.list_dashboards().get("DashboardEntries", [])
            total_checks += 1

            perf_dashboards = [
                d for d in dashboards
                if any(p in d.get("DashboardName", "").lower()
                       for p in ["perf", "performance", "latency", "monitor"])
            ]

            if perf_dashboards:
                passed_checks += 1
            elif dashboards:
                passed_checks += 0.5  # Partial credit
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No performance-focused dashboards found",
                    severity="LOW",
                    recommendation="Create dashboards focused on performance KPIs",
                    effort="LOW",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No CloudWatch dashboards configured",
                    severity="MEDIUM",
                    recommendation="Create dashboards to monitor performance metrics",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for performance alarms (PERF05-BP02)
        try:
            alarms = cloudwatch.describe_alarms().get("MetricAlarms", [])
            total_checks += 1

            perf_metrics = ["latency", "duration", "responsetime", "throughput", "cpu", "memory"]
            perf_alarms = [
                a for a in alarms
                if any(m in a.get("MetricName", "").lower() for m in perf_metrics)
            ]

            if len(perf_alarms) >= 5:
                passed_checks += 1
            elif perf_alarms:
                passed_checks += 0.5
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue=f"Only {len(perf_alarms)} performance alarms configured",
                    severity="MEDIUM",
                    recommendation="Create more alarms for key performance metrics",
                    effort="LOW",
                    impact="HIGH"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No performance-focused alarms",
                    severity="MEDIUM",
                    recommendation="Create alarms for latency, throughput, and resource utilization",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check X-Ray for tracing (PERF05-BP02)
        xray = aws_client.get_client("xray")
        try:
            # Check for sampling rules (indicates X-Ray usage)
            rules = xray.get_sampling_rules().get("SamplingRuleRecords", [])
            total_checks += 1

            if len(rules) > 1:  # More than just default rule
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:xray::account",
                    issue="X-Ray tracing not extensively configured",
                    severity="MEDIUM",
                    recommendation="Enable X-Ray for distributed tracing and performance analysis",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for Lambda runtime versions (PERF05-BP06)
        lambda_client = aws_client.get_client("lambda")
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            if functions:
                total_checks += 1

                # Check for deprecated runtimes
                deprecated_runtimes = ["python3.7", "python3.6", "nodejs12.x", "nodejs10.x", "ruby2.5"]
                outdated_funcs = [
                    f for f in functions
                    if f.get("Runtime", "") in deprecated_runtimes
                ]

                if outdated_funcs:
                    findings.append(create_finding(
                        resource="arn:aws:lambda::account",
                        issue=f"{len(outdated_funcs)} Lambda functions using deprecated runtimes",
                        severity="MEDIUM",
                        recommendation="Update Lambda functions to supported runtimes",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check EC2 instance age (PERF05-BP06)
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
                old_threshold = datetime.now(timezone.utc) - timedelta(days=365)

                old_instances = [
                    i for i in running_instances
                    if i.get("LaunchTime", datetime.now(timezone.utc)) < old_threshold
                ]

                if len(old_instances) > len(running_instances) * 0.3:
                    findings.append(create_finding(
                        resource="arn:aws:ec2::account",
                        issue=f"{len(old_instances)} instances running for over 1 year",
                        severity="LOW",
                        recommendation="Review long-running instances for refresh opportunities",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
                else:
                    passed_checks += 1
        except Exception:
            pass

        # Check DevOps Guru (PERF05-BP05)
        try:
            devops_guru = aws_client.get_client("devops-guru")
            status = devops_guru.describe_account_health()
            total_checks += 1

            # If we can call this, DevOps Guru is enabled
            passed_checks += 1
        except Exception as e:
            if "not enabled" in str(e).lower() or "AccessDenied" in str(e):
                total_checks += 1
                findings.append(create_finding(
                    resource="arn:aws:devops-guru::account",
                    issue="Amazon DevOps Guru not enabled",
                    severity="INFO",
                    recommendation="Enable DevOps Guru for ML-powered performance insights",
                    effort="LOW",
                    impact="MEDIUM"
                ))

    except Exception as e:
        return {"error": str(e), "check_area": "PERF05: Process and Culture"}

    return create_check_result(
        pillar=Pillar.PERFORMANCE_EFFICIENCY,
        check_name="check_performance_process",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=int(passed_checks),
        best_practices=[
            "Establish KPIs to measure workload performance (PERF05-BP01)",
            "Use monitoring solutions for critical performance areas (PERF05-BP02)",
            "Define a process to improve workload performance (PERF05-BP03)",
            "Load test your workload (PERF05-BP04)",
            "Use automation to remediate performance issues (PERF05-BP05)",
            "Keep workloads and services up-to-date (PERF05-BP06)",
            "Review metrics at regular intervals (PERF05-BP07)",
        ]
    )


# =============================================================================
# Pillar Review
# =============================================================================

@tool
def run_performance_efficiency_pillar_review(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run comprehensive Performance Efficiency pillar review.

    Executes all PERF01-PERF05 checks and aggregates results into a
    pillar-level assessment with prioritized recommendations.

    Returns:
        Complete pillar review with scores, findings, and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    check_functions = [
        ("check_architecture_selection", check_architecture_selection),
        ("check_compute_selection", check_compute_selection),
        ("check_data_store_performance", check_data_store_performance),
        ("check_network_performance", check_network_performance),
        ("check_performance_process", check_performance_process),
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
        "Enable AWS Compute Optimizer for rightsizing recommendations",
        "Use current generation instances (Graviton/ARM for cost-performance)",
        "Implement caching with ElastiCache or CloudFront",
        "Enable Performance Insights for RDS databases",
        "Configure Auto Scaling with appropriate policies",
        "Use VPC Endpoints to reduce network latency",
        "Enable Enhanced Networking (ENA) on EC2 instances",
        "Create CloudWatch dashboards for performance KPIs",
        "Enable X-Ray for distributed tracing",
        "Keep runtimes and services up-to-date",
    ]

    return create_pillar_review_result(
        pillar=Pillar.PERFORMANCE_EFFICIENCY,
        check_results=check_results,
        recommendations=recommendations
    )
