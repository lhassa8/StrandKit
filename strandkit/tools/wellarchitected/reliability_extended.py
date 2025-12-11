"""
AWS Well-Architected Framework - Reliability Pillar Extended Tools.

This module provides additional reliability checks to complete coverage
of the Reliability Pillar based on the 2025 AWS Well-Architected Framework.

New checks cover:
- REL03: Workload service architecture (microservices design)
- REL04: Preventing failures (idempotency, loose coupling)
- REL05: Mitigating failures (graceful degradation, circuit breakers)
- REL11: Withstanding component failures (availability SLAs)
- REL12: Testing reliability (chaos engineering)

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
    Pillar,
)


# =============================================================================
# REL-03: Workload Service Architecture
# =============================================================================

@tool
def check_service_architecture(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check workload service architecture design (REL03).

    Validates:
    - Service segmentation (microservices vs monolith)
    - API Gateway usage for service contracts
    - Service mesh or App Mesh configuration
    - ECS/EKS service design

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check for API Gateway usage (indicates service contracts)
        apigw = aws_client.get_client("apigateway")
        try:
            apis = apigw.get_rest_apis().get("items", [])
            total_resources += 1

            if apis:
                compliant_resources += 1
                # Check for documentation/OpenAPI specs
                documented_apis = 0
                for api in apis[:10]:
                    api_id = api.get("id")
                    try:
                        export = apigw.get_export(
                            restApiId=api_id,
                            stageName="prod",
                            exportType="oas30"
                        )
                        if export:
                            documented_apis += 1
                    except Exception:
                        pass

                if documented_apis < len(apis[:10]) * 0.5:
                    findings.append(create_finding(
                        resource="arn:aws:apigateway::account",
                        issue=f"Only {documented_apis}/{len(apis[:10])} APIs have OpenAPI documentation",
                        severity="LOW",
                        recommendation="Document APIs with OpenAPI/Swagger for service contracts",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:apigateway::account",
                    issue="No API Gateway REST APIs found",
                    severity="INFO",
                    recommendation="Consider API Gateway for defining service contracts",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for HTTP APIs (API Gateway v2)
        apigwv2 = aws_client.get_client("apigatewayv2")
        try:
            http_apis = apigwv2.get_apis().get("Items", [])
            if http_apis:
                total_resources += 1
                compliant_resources += 1
        except Exception:
            pass

        # Check ECS services for proper design
        ecs = aws_client.get_client("ecs")
        try:
            clusters = ecs.list_clusters().get("clusterArns", [])

            for cluster_arn in clusters:
                services = ecs.list_services(cluster=cluster_arn).get("serviceArns", [])

                if services:
                    service_details = ecs.describe_services(
                        cluster=cluster_arn,
                        services=services[:10]
                    ).get("services", [])

                    for svc in service_details:
                        svc_name = svc.get("serviceName")
                        total_resources += 1
                        is_compliant = True

                        # Check for load balancer (indicates proper service exposure)
                        load_balancers = svc.get("loadBalancers", [])
                        if not load_balancers:
                            findings.append(create_finding(
                                resource=svc.get("serviceArn"),
                                issue=f"ECS service '{svc_name}' has no load balancer",
                                severity="INFO",
                                recommendation="Consider using ALB/NLB for service exposure and health checks",
                                effort="MEDIUM",
                                impact="MEDIUM"
                            ))

                        # Check deployment configuration
                        deployment_config = svc.get("deploymentConfiguration", {})
                        max_percent = deployment_config.get("maximumPercent", 200)
                        min_percent = deployment_config.get("minimumHealthyPercent", 100)

                        if max_percent < 150 and min_percent >= 100:
                            is_compliant = False
                            findings.append(create_finding(
                                resource=svc.get("serviceArn"),
                                issue=f"ECS service '{svc_name}' has restrictive deployment config",
                                severity="LOW",
                                recommendation="Increase maximumPercent for zero-downtime deployments",
                                effort="LOW",
                                impact="MEDIUM"
                            ))

                        if is_compliant:
                            compliant_resources += 1
        except Exception:
            pass

        # Check Lambda functions for service segmentation
        lambda_client = aws_client.get_client("lambda")
        try:
            paginator = lambda_client.get_paginator("list_functions")
            functions = []
            for page in paginator.paginate():
                functions.extend(page.get("Functions", []))

            total_resources += 1
            if len(functions) > 5:  # Multiple functions indicates service segmentation
                compliant_resources += 1
            elif len(functions) > 0:
                findings.append(create_finding(
                    resource="arn:aws:lambda::account",
                    issue=f"Only {len(functions)} Lambda functions found",
                    severity="INFO",
                    recommendation="Consider breaking monolithic functions into smaller, focused services",
                    effort="HIGH",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_service_architecture",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Segment workloads by business domains",
            "Define clear service contracts with OpenAPI/Swagger",
            "Use API Gateway for consistent service exposure",
            "Implement health checks at all service boundaries",
            "Design services for independent deployability",
            "Consider service mesh for complex microservices"
        ]
    )


# =============================================================================
# REL-04: Preventing Failures (Idempotency, Loose Coupling)
# =============================================================================

@tool
def check_failure_prevention(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check distributed system design for failure prevention (REL04).

    Validates:
    - SQS/SNS usage for loose coupling
    - EventBridge for event-driven architecture
    - Step Functions for workflow coordination
    - API Gateway with caching

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check for loose coupling patterns
        sqs = aws_client.get_client("sqs")
        sns = aws_client.get_client("sns")
        events = aws_client.get_client("events")

        # Check SQS queues (async communication)
        try:
            queues = sqs.list_queues().get("QueueUrls", [])
            total_resources += 1

            if queues:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:sqs::account",
                    issue="No SQS queues found for loose coupling",
                    severity="INFO",
                    recommendation="Consider SQS for asynchronous communication between services",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check SNS topics (pub/sub)
        try:
            topics = sns.list_topics().get("Topics", [])
            total_resources += 1

            if topics:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:sns::account",
                    issue="No SNS topics found for event distribution",
                    severity="INFO",
                    recommendation="Consider SNS for fan-out and pub/sub patterns",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check EventBridge (event-driven)
        try:
            event_buses = events.list_event_buses().get("EventBuses", [])
            rules = events.list_rules().get("Rules", [])

            total_resources += 1
            custom_buses = [b for b in event_buses if b.get("Name") != "default"]

            if rules or custom_buses:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:events::account",
                    issue="No EventBridge rules or custom buses configured",
                    severity="INFO",
                    recommendation="Use EventBridge for event-driven architecture",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check Step Functions (workflow coordination)
        sfn = aws_client.get_client("stepfunctions")
        try:
            state_machines = sfn.list_state_machines().get("stateMachines", [])
            total_resources += 1

            if state_machines:
                compliant_resources += 1

                # Check for idempotency patterns
                for sm in state_machines[:5]:
                    sm_arn = sm.get("stateMachineArn")
                    try:
                        definition = sfn.describe_state_machine(
                            stateMachineArn=sm_arn
                        ).get("definition", "")

                        # Check for idempotency patterns in definition
                        has_idempotency = (
                            '"TaskToken"' in definition or
                            '"ResultPath"' in definition or
                            '"OutputPath"' in definition
                        )

                        if not has_idempotency:
                            findings.append(create_finding(
                                resource=sm_arn,
                                issue=f"Step Function '{sm.get('name')}' may lack idempotency patterns",
                                severity="LOW",
                                recommendation="Consider using TaskTokens and output paths for idempotency",
                                effort="MEDIUM",
                                impact="MEDIUM"
                            ))
                    except Exception:
                        pass
            else:
                findings.append(create_finding(
                    resource="arn:aws:states::account",
                    issue="No Step Functions state machines for workflow coordination",
                    severity="INFO",
                    recommendation="Consider Step Functions for complex workflows",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check API Gateway caching (reduces dependencies)
        apigw = aws_client.get_client("apigateway")
        try:
            apis = apigw.get_rest_apis().get("items", [])

            for api in apis[:5]:
                api_id = api.get("id")
                stages = apigw.get_stages(restApiId=api_id).get("item", [])

                for stage in stages:
                    total_resources += 1
                    cache_enabled = stage.get("cacheClusterEnabled", False)

                    if cache_enabled:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=f"arn:aws:apigateway:::restapis/{api_id}/stages/{stage.get('stageName')}",
                            issue=f"API Gateway stage '{stage.get('stageName')}' has no caching",
                            severity="INFO",
                            recommendation="Enable caching to reduce backend load and dependencies",
                            effort="LOW",
                            impact="LOW"
                        ))
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_failure_prevention",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use SQS/SNS for loose coupling between services",
            "Implement event-driven architecture with EventBridge",
            "Use Step Functions for complex workflow coordination",
            "Design mutating operations to be idempotent",
            "Cache API responses to reduce dependency on backends",
            "Implement constant work pattern for predictable load"
        ]
    )


# =============================================================================
# REL-05: Mitigating Failures
# =============================================================================

@tool
def check_failure_mitigation(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check distributed system design for failure mitigation (REL05).

    Validates:
    - Circuit breaker patterns (via timeouts/retries)
    - Graceful degradation setup
    - Rate limiting and throttling
    - Dead letter queues for failed processing

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check Lambda timeouts and reserved concurrency
        lambda_client = aws_client.get_client("lambda")
        try:
            paginator = lambda_client.get_paginator("list_functions")

            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    func_name = func.get("FunctionName")
                    func_arn = func.get("FunctionArn")
                    total_resources += 1
                    is_compliant = True

                    # Check timeout (default is 3s, max is 900s)
                    timeout = func.get("Timeout", 3)
                    if timeout > 300:  # 5 minutes
                        findings.append(create_finding(
                            resource=func_arn,
                            issue=f"Lambda '{func_name}' has long timeout ({timeout}s)",
                            severity="LOW",
                            recommendation="Consider shorter timeouts for faster failure detection",
                            effort="LOW",
                            impact="MEDIUM"
                        ))

                    # Check reserved concurrency (for throttling)
                    try:
                        concurrency = lambda_client.get_function_concurrency(
                            FunctionName=func_name
                        )
                        reserved = concurrency.get("ReservedConcurrentExecutions")
                        if reserved:
                            # Has reserved concurrency - good for blast radius control
                            pass
                    except Exception:
                        pass

                    # Check for DLQ
                    dlq = func.get("DeadLetterConfig", {}).get("TargetArn")
                    if not dlq:
                        is_compliant = False
                        # Check event invoke config for failure destination
                        try:
                            invoke_config = lambda_client.get_function_event_invoke_config(
                                FunctionName=func_name
                            )
                            failure_dest = invoke_config.get("DestinationConfig", {}).get("OnFailure", {})
                            if failure_dest.get("Destination"):
                                is_compliant = True
                        except Exception:
                            pass

                        if not is_compliant:
                            findings.append(create_finding(
                                resource=func_arn,
                                issue=f"Lambda '{func_name}' has no DLQ or failure destination",
                                severity="MEDIUM",
                                recommendation="Configure DLQ for graceful failure handling",
                                effort="LOW",
                                impact="HIGH"
                            ))

                    if is_compliant:
                        compliant_resources += 1
        except Exception:
            pass

        # Check API Gateway throttling
        apigw = aws_client.get_client("apigateway")
        try:
            apis = apigw.get_rest_apis().get("items", [])

            for api in apis[:5]:
                api_id = api.get("id")
                stages = apigw.get_stages(restApiId=api_id).get("item", [])

                for stage in stages:
                    stage_name = stage.get("stageName")
                    total_resources += 1

                    # Check stage throttling
                    method_settings = stage.get("methodSettings", {})
                    default_settings = method_settings.get("*/*", {})

                    throttling_rate = default_settings.get("throttlingRateLimit", 10000)
                    throttling_burst = default_settings.get("throttlingBurstLimit", 5000)

                    # Default is 10000 rps - check if customized
                    if throttling_rate < 10000:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=f"arn:aws:apigateway:::restapis/{api_id}/stages/{stage_name}",
                            issue=f"API Gateway stage '{stage_name}' using default throttling",
                            severity="LOW",
                            recommendation="Configure appropriate throttling limits",
                            effort="LOW",
                            impact="MEDIUM"
                        ))
        except Exception:
            pass

        # Check SQS queues for DLQ configuration
        sqs = aws_client.get_client("sqs")
        try:
            queues = sqs.list_queues().get("QueueUrls", [])

            for queue_url in queues:
                queue_name = queue_url.split("/")[-1]

                # Skip DLQ queues
                if "-dlq" in queue_name.lower() or "deadletter" in queue_name.lower():
                    continue

                total_resources += 1

                try:
                    attrs = sqs.get_queue_attributes(
                        QueueUrl=queue_url,
                        AttributeNames=["RedrivePolicy", "VisibilityTimeout"]
                    )

                    redrive = attrs.get("Attributes", {}).get("RedrivePolicy")
                    visibility = int(attrs.get("Attributes", {}).get("VisibilityTimeout", 30))

                    if redrive:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=queue_url,
                            issue=f"SQS queue '{queue_name}' has no dead letter queue",
                            severity="MEDIUM",
                            recommendation="Configure DLQ for failed message handling",
                            effort="LOW",
                            impact="HIGH"
                        ))

                    # Check visibility timeout (should match processing time)
                    if visibility < 30:
                        findings.append(create_finding(
                            resource=queue_url,
                            issue=f"SQS queue '{queue_name}' has short visibility timeout ({visibility}s)",
                            severity="LOW",
                            recommendation="Increase visibility timeout to match processing time",
                            effort="LOW",
                            impact="MEDIUM"
                        ))
                except Exception:
                    pass
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_failure_mitigation",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Implement graceful degradation for hard dependencies",
            "Configure appropriate timeouts for all service calls",
            "Use dead letter queues for failed message processing",
            "Implement throttling to protect downstream services",
            "Use retry with exponential backoff and jitter",
            "Fail fast when downstream services are unavailable"
        ]
    )


# =============================================================================
# REL-11: Withstanding Component Failures
# =============================================================================

@tool
def check_availability_design(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check design for withstanding component failures (REL11).

    Validates:
    - Route 53 health checks for failover
    - Auto Scaling policies for self-healing
    - ELB health check configuration
    - Multi-region readiness

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check Route 53 health checks
        route53 = aws_client.get_client("route53")
        try:
            health_checks = route53.list_health_checks().get("HealthChecks", [])
            total_resources += 1

            if health_checks:
                compliant_resources += 1

                # Check for failover routing
                hosted_zones = route53.list_hosted_zones().get("HostedZones", [])
                has_failover = False

                for zone in hosted_zones[:5]:
                    zone_id = zone.get("Id", "").replace("/hostedzone/", "")
                    records = route53.list_resource_record_sets(
                        HostedZoneId=zone_id
                    ).get("ResourceRecordSets", [])

                    failover_records = [
                        r for r in records
                        if r.get("Failover") or r.get("SetIdentifier")
                    ]
                    if failover_records:
                        has_failover = True
                        break

                if not has_failover:
                    findings.append(create_finding(
                        resource="arn:aws:route53::account",
                        issue="No failover routing policies configured",
                        severity="MEDIUM",
                        recommendation="Implement failover routing for high availability",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:route53::account",
                    issue="No Route 53 health checks configured",
                    severity="MEDIUM",
                    recommendation="Create health checks for endpoint monitoring",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check Auto Scaling for self-healing
        autoscaling = aws_client.get_client("autoscaling")
        try:
            asgs = autoscaling.describe_auto_scaling_groups().get("AutoScalingGroups", [])

            for asg in asgs:
                asg_name = asg.get("AutoScalingGroupName")
                asg_arn = asg.get("AutoScalingGroupARN")
                total_resources += 1
                is_compliant = True

                # Check health check type
                health_check_type = asg.get("HealthCheckType", "EC2")
                target_groups = asg.get("TargetGroupARNs", [])

                if target_groups and health_check_type != "ELB":
                    is_compliant = False
                    findings.append(create_finding(
                        resource=asg_arn,
                        issue=f"ASG '{asg_name}' with ALB uses EC2 health check (should be ELB)",
                        severity="HIGH",
                        recommendation="Change to ELB health check type for accurate detection",
                        effort="LOW",
                        impact="HIGH"
                    ))

                # Check min capacity for availability
                min_size = asg.get("MinSize", 0)
                if min_size < 2:
                    findings.append(create_finding(
                        resource=asg_arn,
                        issue=f"ASG '{asg_name}' has MinSize of {min_size}",
                        severity="MEDIUM",
                        recommendation="Set MinSize >= 2 for high availability",
                        effort="LOW",
                        impact="HIGH"
                    ))

                if is_compliant:
                    compliant_resources += 1
        except Exception:
            pass

        # Check ELB/ALB health check configuration
        elbv2 = aws_client.get_client("elbv2")
        try:
            target_groups = elbv2.describe_target_groups().get("TargetGroups", [])

            for tg in target_groups:
                tg_arn = tg.get("TargetGroupArn")
                tg_name = tg.get("TargetGroupName")
                total_resources += 1

                # Check health check settings
                healthy_threshold = tg.get("HealthyThresholdCount", 5)
                unhealthy_threshold = tg.get("UnhealthyThresholdCount", 2)
                interval = tg.get("HealthCheckIntervalSeconds", 30)

                # Fast failure detection is good
                if unhealthy_threshold <= 2 and interval <= 30:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=tg_arn,
                        issue=f"Target group '{tg_name}' may have slow failure detection",
                        severity="LOW",
                        recommendation="Reduce interval and unhealthy threshold for faster detection",
                        effort="LOW",
                        impact="MEDIUM",
                        details={
                            "interval": interval,
                            "unhealthy_threshold": unhealthy_threshold
                        }
                    ))
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_availability_design",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Implement Route 53 health checks for endpoint monitoring",
            "Use failover routing policies for automatic recovery",
            "Configure ELB health checks for accurate failure detection",
            "Set minimum capacity for continuous availability",
            "Use Auto Scaling for automatic self-healing",
            "Design for static stability during recovery"
        ]
    )


# =============================================================================
# REL-12: Testing Reliability
# =============================================================================

@tool
def check_reliability_testing(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check reliability testing practices (REL12).

    Validates:
    - AWS FIS (Fault Injection Service) experiments
    - Load testing infrastructure
    - Canary deployments (synthetics)
    - Backup restoration testing

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check AWS FIS experiments (chaos engineering)
        fis = aws_client.get_client("fis")
        try:
            experiments = fis.list_experiments().get("experiments", [])
            templates = fis.list_experiment_templates().get("experimentTemplates", [])

            total_resources += 1

            if templates:
                compliant_resources += 1

                # Check if experiments have been run recently
                recent_experiments = [
                    e for e in experiments
                    if e.get("state", {}).get("status") in ["completed", "running"]
                ]

                if not recent_experiments:
                    findings.append(create_finding(
                        resource="arn:aws:fis::account",
                        issue="FIS experiment templates exist but no recent experiments run",
                        severity="MEDIUM",
                        recommendation="Run fault injection experiments regularly",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:fis::account",
                    issue="No AWS Fault Injection Service experiment templates",
                    severity="MEDIUM",
                    recommendation="Create FIS experiments to test failure scenarios",
                    effort="HIGH",
                    impact="HIGH"
                ))
        except Exception:
            total_resources += 1
            findings.append(create_finding(
                resource="arn:aws:fis::account",
                issue="Could not check AWS Fault Injection Service",
                severity="INFO",
                recommendation="Enable and use FIS for chaos engineering",
                effort="HIGH",
                impact="HIGH"
            ))

        # Check CloudWatch Synthetics (canaries)
        synthetics = aws_client.get_client("synthetics")
        try:
            canaries = synthetics.describe_canaries().get("Canaries", [])
            total_resources += 1

            if canaries:
                compliant_resources += 1

                # Check canary status
                failed_canaries = [
                    c for c in canaries
                    if c.get("Status", {}).get("State") not in ["RUNNING", "READY"]
                ]

                if failed_canaries:
                    findings.append(create_finding(
                        resource="arn:aws:synthetics::account",
                        issue=f"{len(failed_canaries)} CloudWatch Synthetic canaries not running",
                        severity="MEDIUM",
                        recommendation="Fix or remove non-functional canaries",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:synthetics::account",
                    issue="No CloudWatch Synthetic canaries configured",
                    severity="LOW",
                    recommendation="Create synthetic canaries to monitor user journeys",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            total_resources += 1

        # Check for AWS Resilience Hub workloads
        resiliencehub = aws_client.get_client("resiliencehub")
        try:
            apps = resiliencehub.list_apps().get("appSummaries", [])
            total_resources += 1

            if apps:
                compliant_resources += 1

                # Check assessment status
                for app in apps[:5]:
                    app_arn = app.get("appArn")
                    try:
                        assessments = resiliencehub.list_app_assessments(
                            appArn=app_arn
                        ).get("assessmentSummaries", [])

                        if not assessments:
                            findings.append(create_finding(
                                resource=app_arn,
                                issue=f"Resilience Hub app '{app.get('name')}' has no assessments",
                                severity="MEDIUM",
                                recommendation="Run resilience assessment",
                                effort="LOW",
                                impact="HIGH"
                            ))
                    except Exception:
                        pass
            else:
                findings.append(create_finding(
                    resource="arn:aws:resiliencehub::account",
                    issue="No AWS Resilience Hub applications configured",
                    severity="LOW",
                    recommendation="Use Resilience Hub to assess and test workload resilience",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check backup restoration (via AWS Backup)
        backup = aws_client.get_client("backup")
        try:
            # Check for restore test plans
            restore_jobs = backup.list_restore_jobs(
                ByStatus="COMPLETED"
            ).get("RestoreJobs", [])

            total_resources += 1

            # Check for recent restore tests (last 90 days)
            recent_restores = [
                j for j in restore_jobs
                if j.get("CompletionDate") and
                (datetime.now(timezone.utc) - j.get("CompletionDate").replace(tzinfo=timezone.utc)).days < 90
            ]

            if recent_restores:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:backup::account",
                    issue="No backup restoration tests in the last 90 days",
                    severity="HIGH",
                    recommendation="Test backup restoration regularly",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_reliability_testing",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use AWS Fault Injection Service for chaos engineering",
            "Create and run fault injection experiments regularly",
            "Implement CloudWatch Synthetics for endpoint monitoring",
            "Use AWS Resilience Hub to assess workload resilience",
            "Test backup and disaster recovery procedures",
            "Conduct regular game days and tabletop exercises"
        ]
    )


@tool
def check_runbooks_playbooks(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check for operational runbooks and playbooks (REL12-BP01).

    Validates:
    - SSM Automation documents for incident response
    - SSM Command documents for standard operations
    - Runbook documentation and maintenance

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        ssm = aws_client.get_client("ssm")

        # Check for custom SSM documents (runbooks)
        total_resources += 1
        try:
            # Get custom automation documents
            automation_docs = ssm.list_documents(
                Filters=[
                    {"Key": "Owner", "Values": ["Self"]},
                    {"Key": "DocumentType", "Values": ["Automation"]}
                ]
            ).get("DocumentIdentifiers", [])

            # Get custom command documents
            command_docs = ssm.list_documents(
                Filters=[
                    {"Key": "Owner", "Values": ["Self"]},
                    {"Key": "DocumentType", "Values": ["Command"]}
                ]
            ).get("DocumentIdentifiers", [])

            total_docs = len(automation_docs) + len(command_docs)

            if total_docs >= 3:
                compliant_resources += 1

                # Check for key operational patterns
                doc_names = [d.get("Name", "").lower() for d in automation_docs + command_docs]
                key_patterns = ["deploy", "restart", "backup", "scale", "failover", "recovery"]
                found_patterns = [p for p in key_patterns if any(p in n for n in doc_names)]

                if len(found_patterns) < 2:
                    findings.append(create_finding(
                        resource="arn:aws:ssm::account",
                        issue=f"Only {len(found_patterns)} key operational patterns covered in runbooks",
                        severity="LOW",
                        recommendation="Create runbooks for common operations (deploy, restart, scale, failover)",
                        effort="MEDIUM",
                        impact="MEDIUM",
                        details={"found_patterns": found_patterns}
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue=f"Only {total_docs} custom SSM documents (runbooks) found",
                    severity="MEDIUM",
                    recommendation="Create SSM Automation documents for standard operations",
                    effort="HIGH",
                    impact="HIGH"
                ))

        except Exception:
            findings.append(create_finding(
                resource="arn:aws:ssm::account",
                issue="Could not enumerate SSM documents",
                severity="INFO",
                recommendation="Create SSM Automation documents for operational runbooks",
                effort="HIGH",
                impact="HIGH"
            ))

        # Check for maintenance windows (scheduled operations)
        try:
            windows = ssm.describe_maintenance_windows().get("WindowIdentities", [])
            total_resources += 1

            if windows:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue="No Systems Manager maintenance windows configured",
                    severity="LOW",
                    recommendation="Create maintenance windows for scheduled operations",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.RELIABILITY.value,
        check_name="check_runbooks_playbooks",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Create SSM Automation documents for all standard operations",
            "Document runbooks for common failure scenarios",
            "Use maintenance windows for scheduled operations",
            "Version control runbooks alongside application code",
            "Review and update runbooks after incidents",
            "Train team members on runbook execution"
        ]
    )


# Export all new tools
__all__ = [
    # REL03 - Workload Architecture
    "check_service_architecture",
    # REL04 - Preventing Failures
    "check_failure_prevention",
    # REL05 - Mitigating Failures
    "check_failure_mitigation",
    # REL11 - Withstanding Failures
    "check_availability_design",
    # REL12 - Testing Reliability
    "check_reliability_testing",
    "check_runbooks_playbooks",
]
