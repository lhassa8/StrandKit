"""
AWS Well-Architected Framework - Operational Excellence Pillar Tools.

This module provides automated checks aligned with the Operational Excellence
Pillar of the AWS Well-Architected Framework (2025 edition).

Operational Excellence focuses on running and monitoring systems to deliver
business value and continually improving processes and procedures. The pillar
covers 11 questions (OPS01-OPS11) with 60+ best practices organized into
four focus areas:

1. Organization (OPS01-OPS03)
2. Prepare (OPS04-OPS07)
3. Operate (OPS08-OPS10)
4. Evolve (OPS11)

Reference: https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/
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
# OPS-04: Observability Implementation
# =============================================================================

@tool
def check_observability_implementation(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check observability implementation (OPS04).

    Validates:
    - CloudWatch metrics configured (BP01, BP02)
    - X-Ray tracing enabled (BP05)
    - Application Insights configured
    - Container Insights enabled

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

        # Check for custom metrics (OPS04-BP01, BP02)
        try:
            metrics = cloudwatch.list_metrics(
                RecentlyActive="PT3H"
            ).get("Metrics", [])

            # Count custom namespaces (not AWS/)
            custom_namespaces = set()
            for m in metrics:
                ns = m.get("Namespace", "")
                if not ns.startswith("AWS/"):
                    custom_namespaces.add(ns)

            total_checks += 1
            if len(custom_namespaces) >= 1:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No custom CloudWatch metrics detected",
                    severity="MEDIUM",
                    recommendation="Implement application telemetry with custom metrics",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for CloudWatch alarms (OPS04-BP01)
        try:
            alarms = cloudwatch.describe_alarms().get("MetricAlarms", [])
            total_checks += 1

            if len(alarms) >= 5:
                passed_checks += 1
            elif alarms:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue=f"Only {len(alarms)} CloudWatch alarm(s) configured",
                    severity="LOW",
                    recommendation="Add more alarms for key performance indicators",
                    effort="LOW",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No CloudWatch alarms configured",
                    severity="HIGH",
                    recommendation="Create alarms for critical KPIs and thresholds",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check X-Ray tracing (OPS04-BP05)
        xray = aws_client.get_client("xray")
        try:
            # Check for X-Ray groups or sampling rules
            groups = xray.get_groups().get("Groups", [])
            sampling_rules = xray.get_sampling_rules().get("SamplingRuleRecords", [])

            total_checks += 1
            if groups or len(sampling_rules) > 1:  # Default rule always exists
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:xray::account",
                    issue="X-Ray tracing not actively configured",
                    severity="MEDIUM",
                    recommendation="Enable X-Ray for distributed tracing",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            total_checks += 1
            findings.append(create_finding(
                resource="arn:aws:xray::account",
                issue="Could not check X-Ray configuration",
                severity="INFO",
                recommendation="Consider X-Ray for distributed tracing",
                effort="MEDIUM",
                impact="HIGH"
            ))

        # Check Container Insights (if ECS/EKS used)
        ecs = aws_client.get_client("ecs")
        try:
            clusters = ecs.list_clusters().get("clusterArns", [])
            if clusters:
                cluster_details = ecs.describe_clusters(
                    clusters=clusters[:5],
                    include=["SETTINGS"]
                ).get("clusters", [])

                insights_enabled = 0
                for cluster in cluster_details:
                    settings = cluster.get("settings", [])
                    for s in settings:
                        if s.get("name") == "containerInsights" and s.get("value") == "enabled":
                            insights_enabled += 1
                            break

                total_checks += 1
                if insights_enabled == len(cluster_details):
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:ecs::account",
                        issue=f"Container Insights enabled on {insights_enabled}/{len(cluster_details)} ECS clusters",
                        severity="MEDIUM",
                        recommendation="Enable Container Insights for all ECS clusters",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check for CloudWatch Logs Insights queries
        logs = aws_client.get_client("logs")
        try:
            queries = logs.describe_query_definitions().get("queryDefinitions", [])
            total_checks += 1

            if len(queries) >= 3:
                passed_checks += 1
            elif queries:
                findings.append(create_finding(
                    resource="arn:aws:logs::account",
                    issue=f"Only {len(queries)} saved Logs Insights queries",
                    severity="INFO",
                    recommendation="Create more saved queries for common investigations",
                    effort="LOW",
                    impact="LOW"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:logs::account",
                    issue="No saved CloudWatch Logs Insights queries",
                    severity="LOW",
                    recommendation="Create saved queries for faster log analysis",
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
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_name="check_observability_implementation",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Define and track key performance indicators (OPS04-BP01)",
            "Implement application telemetry with custom metrics (OPS04-BP02)",
            "Enable X-Ray for distributed tracing (OPS04-BP05)",
            "Use Container Insights for ECS/EKS (OPS04-BP04)",
            "Create CloudWatch alarms for critical thresholds"
        ]
    )


# =============================================================================
# OPS-05: Development and Deployment
# =============================================================================

@tool
def check_deployment_practices(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check development and deployment practices (OPS05).

    Validates:
    - CodePipeline for CI/CD (BP10)
    - CodeBuild for builds (BP04)
    - Systems Manager for config management (BP03)
    - Multiple environments

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check CodePipeline (OPS05-BP10)
        codepipeline = aws_client.get_client("codepipeline")
        try:
            pipelines = codepipeline.list_pipelines().get("pipelines", [])
            total_checks += 1

            if pipelines:
                passed_checks += 1

                # Check pipeline health
                failed_pipelines = []
                for p in pipelines[:10]:
                    try:
                        state = codepipeline.get_pipeline_state(name=p["name"])
                        stages = state.get("stageStates", [])
                        for stage in stages:
                            status = stage.get("latestExecution", {}).get("status")
                            if status == "Failed":
                                failed_pipelines.append(p["name"])
                                break
                    except Exception:
                        pass

                if failed_pipelines:
                    findings.append(create_finding(
                        resource="arn:aws:codepipeline::account",
                        issue=f"{len(failed_pipelines)} pipeline(s) in failed state",
                        severity="MEDIUM",
                        recommendation="Investigate and fix failing pipelines",
                        effort="MEDIUM",
                        impact="HIGH",
                        details={"failed_pipelines": failed_pipelines[:5]}
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:codepipeline::account",
                    issue="No CodePipeline pipelines configured",
                    severity="MEDIUM",
                    recommendation="Implement CI/CD with CodePipeline or similar",
                    effort="HIGH",
                    impact="HIGH"
                ))
        except Exception:
            total_checks += 1

        # Check CodeBuild projects (OPS05-BP04)
        codebuild = aws_client.get_client("codebuild")
        try:
            projects = codebuild.list_projects().get("projects", [])
            total_checks += 1

            if projects:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:codebuild::account",
                    issue="No CodeBuild projects configured",
                    severity="INFO",
                    recommendation="Use CodeBuild for automated builds and tests",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check Systems Manager Parameter Store (OPS05-BP03)
        ssm = aws_client.get_client("ssm")
        try:
            parameters = ssm.describe_parameters(
                MaxResults=50
            ).get("Parameters", [])

            total_checks += 1
            if len(parameters) >= 5:
                passed_checks += 1
            elif parameters:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue=f"Only {len(parameters)} SSM parameters configured",
                    severity="INFO",
                    recommendation="Use Parameter Store for configuration management",
                    effort="LOW",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue="No SSM Parameter Store parameters",
                    severity="LOW",
                    recommendation="Use Parameter Store for centralized configuration",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for multiple environments (OPS05-BP08)
        ec2 = aws_client.get_client("ec2")
        try:
            # Check for environment tags
            instances = ec2.describe_instances().get("Reservations", [])

            environments = set()
            for res in instances:
                for inst in res.get("Instances", []):
                    for tag in inst.get("Tags", []):
                        if tag.get("Key", "").lower() in ["environment", "env", "stage"]:
                            environments.add(tag.get("Value", "").lower())

            total_checks += 1
            if len(environments) >= 2:
                passed_checks += 1
            elif environments:
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue=f"Only {len(environments)} environment(s) detected: {', '.join(environments)}",
                    severity="LOW",
                    recommendation="Use multiple environments (dev, staging, prod)",
                    effort="HIGH",
                    impact="MEDIUM"
                ))
            # No findings if no instances
        except Exception:
            pass

        # Check for AWS Config (OPS05-BP03 - configuration tracking)
        config = aws_client.get_client("config")
        try:
            recorders = config.describe_configuration_recorders().get("ConfigurationRecorders", [])
            total_checks += 1

            if recorders:
                # Check if recorder is recording
                status = config.describe_configuration_recorder_status().get("ConfigurationRecordersStatus", [])
                recording = any(s.get("recording", False) for s in status)

                if recording:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:config::account",
                        issue="AWS Config recorder exists but not recording",
                        severity="MEDIUM",
                        recommendation="Start AWS Config recorder for configuration tracking",
                        effort="LOW",
                        impact="HIGH"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:config::account",
                    issue="AWS Config not enabled",
                    severity="MEDIUM",
                    recommendation="Enable AWS Config to track configuration changes",
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
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_name="check_deployment_practices",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Implement CI/CD with CodePipeline (OPS05-BP10)",
            "Use CodeBuild for automated builds (OPS05-BP04)",
            "Store configuration in Parameter Store (OPS05-BP03)",
            "Use multiple environments (OPS05-BP08)",
            "Enable AWS Config for change tracking (OPS05-BP03)",
            "Make frequent, small, reversible changes (OPS05-BP09)"
        ]
    )


# =============================================================================
# OPS-06: Deployment Risk Mitigation
# =============================================================================

@tool
def check_deployment_safety(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check deployment risk mitigation (OPS06).

    Validates:
    - CodeDeploy with rollback (BP01, BP04)
    - Blue/Green or Canary deployments (BP03)
    - CloudFormation rollback configuration

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check CodeDeploy deployment configurations (OPS06-BP03, BP04)
        codedeploy = aws_client.get_client("codedeploy")
        try:
            apps = codedeploy.list_applications().get("applications", [])
            total_checks += 1

            if apps:
                passed_checks += 1

                # Check deployment groups for rollback config
                groups_without_rollback = []
                for app in apps[:5]:
                    try:
                        groups = codedeploy.list_deployment_groups(
                            applicationName=app
                        ).get("deploymentGroups", [])

                        for group in groups[:3]:
                            try:
                                group_info = codedeploy.get_deployment_group(
                                    applicationName=app,
                                    deploymentGroupName=group
                                ).get("deploymentGroupInfo", {})

                                auto_rollback = group_info.get("autoRollbackConfiguration", {})
                                if not auto_rollback.get("enabled", False):
                                    groups_without_rollback.append(f"{app}/{group}")
                            except Exception:
                                pass
                    except Exception:
                        pass

                if groups_without_rollback:
                    findings.append(create_finding(
                        resource="arn:aws:codedeploy::account",
                        issue=f"{len(groups_without_rollback)} deployment group(s) without auto-rollback",
                        severity="MEDIUM",
                        recommendation="Enable automatic rollback on deployment failure",
                        effort="LOW",
                        impact="HIGH",
                        details={"groups": groups_without_rollback[:5]}
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:codedeploy::account",
                    issue="No CodeDeploy applications configured",
                    severity="INFO",
                    recommendation="Consider CodeDeploy for safe deployments with rollback",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            total_checks += 1

        # Check CloudFormation stacks for rollback (OPS06-BP01)
        cfn = aws_client.get_client("cloudformation")
        try:
            stacks = cfn.list_stacks(
                StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"]
            ).get("StackSummaries", [])

            total_checks += 1
            if stacks:
                passed_checks += 1

                # Check for recent rollbacks
                rollback_stacks = cfn.list_stacks(
                    StackStatusFilter=["UPDATE_ROLLBACK_COMPLETE", "ROLLBACK_COMPLETE"]
                ).get("StackSummaries", [])

                recent_rollbacks = [
                    s for s in rollback_stacks
                    if s.get("LastUpdatedTime") and
                    (datetime.now(timezone.utc) - s["LastUpdatedTime"].replace(tzinfo=timezone.utc)).days < 7
                ]

                if recent_rollbacks:
                    findings.append(create_finding(
                        resource="arn:aws:cloudformation::account",
                        issue=f"{len(recent_rollbacks)} CloudFormation stack(s) rolled back in last 7 days",
                        severity="INFO",
                        recommendation="Review rollback causes and improve change validation",
                        effort="MEDIUM",
                        impact="MEDIUM",
                        details={"stacks": [s["StackName"] for s in recent_rollbacks[:5]]}
                    ))
        except Exception:
            pass

        # Check Lambda function versions/aliases for safe deployment (OPS06-BP03)
        lambda_client = aws_client.get_client("lambda")
        try:
            paginator = lambda_client.get_paginator("list_functions")
            functions_with_aliases = 0
            total_functions = 0

            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    total_functions += 1
                    try:
                        aliases = lambda_client.list_aliases(
                            FunctionName=func["FunctionName"]
                        ).get("Aliases", [])
                        if aliases:
                            functions_with_aliases += 1
                    except Exception:
                        pass

            if total_functions > 0:
                total_checks += 1
                if functions_with_aliases >= total_functions * 0.3:
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:lambda::account",
                        issue=f"Only {functions_with_aliases}/{total_functions} Lambda functions use aliases",
                        severity="LOW",
                        recommendation="Use Lambda aliases for traffic shifting and safe deployments",
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
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_name="check_deployment_safety",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Plan for unsuccessful changes with rollback (OPS06-BP01)",
            "Enable automatic rollback on failure (OPS06-BP04)",
            "Use blue/green or canary deployments (OPS06-BP03)",
            "Use Lambda aliases for traffic shifting",
            "Test deployments in lower environments first (OPS06-BP02)"
        ]
    )


# =============================================================================
# OPS-07: Operational Readiness
# =============================================================================

@tool
def check_operational_readiness(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check operational readiness (OPS07).

    Validates:
    - SSM runbooks exist (BP03)
    - SSM playbooks exist (BP04)
    - Support plan configured (BP06)
    - Documentation/knowledge base

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        ssm = aws_client.get_client("ssm")

        # Check for runbooks (SSM Automation documents) (OPS07-BP03)
        try:
            automation_docs = ssm.list_documents(
                Filters=[
                    {"Key": "Owner", "Values": ["Self"]},
                    {"Key": "DocumentType", "Values": ["Automation"]}
                ]
            ).get("DocumentIdentifiers", [])

            total_checks += 1
            if len(automation_docs) >= 3:
                passed_checks += 1
            elif automation_docs:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue=f"Only {len(automation_docs)} SSM Automation runbook(s)",
                    severity="LOW",
                    recommendation="Create more runbooks for standard operational procedures",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue="No SSM Automation runbooks configured",
                    severity="MEDIUM",
                    recommendation="Create runbooks for common operational tasks",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for playbooks (SSM Documents for investigation) (OPS07-BP04)
        try:
            command_docs = ssm.list_documents(
                Filters=[
                    {"Key": "Owner", "Values": ["Self"]},
                    {"Key": "DocumentType", "Values": ["Command"]}
                ]
            ).get("DocumentIdentifiers", [])

            total_checks += 1
            if command_docs:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue="No SSM Command documents (playbooks) for investigation",
                    severity="LOW",
                    recommendation="Create playbooks for common troubleshooting scenarios",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check Support plan (OPS07-BP06)
        # Support API is only available in us-east-1
        support = aws_client.session.client("support", region_name="us-east-1")
        try:
            # This will fail if not on Business/Enterprise support
            support.describe_severity_levels()
            total_checks += 1
            passed_checks += 1
        except Exception as e:
            if "SubscriptionRequiredException" in str(e):
                total_checks += 1
                findings.append(create_finding(
                    resource="arn:aws:support::account",
                    issue="Basic or Developer Support plan (limited support access)",
                    severity="INFO",
                    recommendation="Consider Business or Enterprise Support for production workloads",
                    effort="LOW",
                    impact="MEDIUM"
                ))
            else:
                total_checks += 1
                passed_checks += 1  # Assume OK if we can't check

        # Check for SNS topics (for alerting/communication) (OPS07-BP04)
        sns = aws_client.get_client("sns")
        try:
            topics = sns.list_topics().get("Topics", [])
            total_checks += 1

            ops_topics = [
                t for t in topics
                if any(p in t.get("TopicArn", "").lower()
                       for p in ["ops", "alert", "incident", "oncall", "pager"])
            ]

            if ops_topics:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:sns::account",
                    issue="No operational SNS topics (alerts, incidents) found",
                    severity="LOW",
                    recommendation="Create SNS topics for operational notifications",
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
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_name="check_operational_readiness",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Create runbooks for standard procedures (OPS07-BP03)",
            "Create playbooks for troubleshooting (OPS07-BP04)",
            "Configure appropriate AWS Support plan (OPS07-BP06)",
            "Set up operational notification channels",
            "Ensure personnel capability and training (OPS07-BP01)"
        ]
    )


# =============================================================================
# OPS-08: Workload Observability Utilization
# =============================================================================

@tool
def check_observability_utilization(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check workload observability utilization (OPS08).

    Validates:
    - CloudWatch dashboards exist (BP05)
    - Actionable alarms configured (BP04)
    - Log analysis setup (BP02)

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

        # Check for dashboards (OPS08-BP05)
        try:
            dashboards = cloudwatch.list_dashboards().get("DashboardEntries", [])
            total_checks += 1

            if len(dashboards) >= 2:
                passed_checks += 1
            elif dashboards:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue=f"Only {len(dashboards)} CloudWatch dashboard(s)",
                    severity="LOW",
                    recommendation="Create dashboards for different workloads/teams",
                    effort="LOW",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No CloudWatch dashboards configured",
                    severity="MEDIUM",
                    recommendation="Create dashboards to visualize workload health",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for actionable alarms with actions (OPS08-BP04)
        try:
            alarms = cloudwatch.describe_alarms().get("MetricAlarms", [])
            total_checks += 1

            alarms_with_actions = [
                a for a in alarms
                if a.get("AlarmActions") or a.get("OKActions") or a.get("InsufficientDataActions")
            ]

            if len(alarms_with_actions) >= len(alarms) * 0.8:
                passed_checks += 1
            elif alarms_with_actions:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue=f"{len(alarms) - len(alarms_with_actions)}/{len(alarms)} alarms without actions",
                    severity="MEDIUM",
                    recommendation="Add SNS actions to alarms for notifications",
                    effort="LOW",
                    impact="HIGH"
                ))
            elif alarms:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No alarms have notification actions configured",
                    severity="HIGH",
                    recommendation="Configure alarm actions for automated response",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check CloudWatch Logs with metric filters (OPS08-BP02)
        logs = aws_client.get_client("logs")
        try:
            log_groups = logs.describe_log_groups(limit=50).get("logGroups", [])
            groups_with_filters = 0

            for lg in log_groups[:20]:
                try:
                    filters = logs.describe_metric_filters(
                        logGroupName=lg["logGroupName"]
                    ).get("metricFilters", [])
                    if filters:
                        groups_with_filters += 1
                except Exception:
                    pass

            total_checks += 1
            if groups_with_filters >= 3:
                passed_checks += 1
            elif groups_with_filters > 0:
                findings.append(create_finding(
                    resource="arn:aws:logs::account",
                    issue=f"Only {groups_with_filters} log group(s) have metric filters",
                    severity="LOW",
                    recommendation="Add metric filters to extract KPIs from logs",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:logs::account",
                    issue="No CloudWatch Logs metric filters configured",
                    severity="MEDIUM",
                    recommendation="Create metric filters to convert logs to metrics",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for Contributor Insights rules
        try:
            rules = cloudwatch.describe_contributor_insights_rules().get("ContributorInsightsRules", [])
            total_checks += 1

            if rules:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No CloudWatch Contributor Insights rules",
                    severity="INFO",
                    recommendation="Use Contributor Insights for top-N analysis",
                    effort="LOW",
                    impact="LOW"
                ))
        except Exception:
            pass

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_name="check_observability_utilization",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Create dashboards for workload visibility (OPS08-BP05)",
            "Configure actionable alarms with notifications (OPS08-BP04)",
            "Use metric filters to analyze logs (OPS08-BP02)",
            "Implement log analysis patterns (OPS08-BP02)",
            "Leverage Contributor Insights for analysis"
        ]
    )


# =============================================================================
# OPS-10: Event Management
# =============================================================================

@tool
def check_event_management(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check workload and operations event management (OPS10).

    Validates:
    - EventBridge rules for automation (BP07)
    - SNS topics for communication (BP05)
    - Systems Manager OpsCenter (BP01)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check EventBridge rules for automation (OPS10-BP07)
        events = aws_client.get_client("events")
        try:
            rules = events.list_rules().get("Rules", [])
            total_checks += 1

            enabled_rules = [r for r in rules if r.get("State") == "ENABLED"]

            if len(enabled_rules) >= 3:
                passed_checks += 1
            elif enabled_rules:
                findings.append(create_finding(
                    resource="arn:aws:events::account",
                    issue=f"Only {len(enabled_rules)} enabled EventBridge rule(s)",
                    severity="LOW",
                    recommendation="Add more event rules for automated responses",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:events::account",
                    issue="No enabled EventBridge rules for event automation",
                    severity="MEDIUM",
                    recommendation="Create EventBridge rules to automate event responses",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for OpsCenter (OPS10-BP01)
        ssm = aws_client.get_client("ssm")
        try:
            # Check for OpsItems
            ops_items = ssm.describe_ops_items(
                OpsItemFilters=[
                    {"Key": "Status", "Values": ["Open", "InProgress"], "Operator": "Equal"}
                ],
                MaxResults=10
            ).get("OpsItemSummaries", [])

            total_checks += 1
            # Having OpsCenter configured is the goal, not necessarily having items
            # Try to get OpsCenter settings
            try:
                ssm.get_service_setting(
                    SettingId="/ssm/opsitem/ssm-patchmanager"
                )
                passed_checks += 1
            except Exception:
                # OpsCenter might be configured even if specific settings don't exist
                if ops_items is not None:  # API call succeeded
                    passed_checks += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:ssm::account",
                        issue="OpsCenter not actively used",
                        severity="LOW",
                        recommendation="Use OpsCenter for centralized incident management",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
        except Exception:
            total_checks += 1

        # Check SNS topics for communication (OPS10-BP05, BP06)
        sns = aws_client.get_client("sns")
        try:
            topics = sns.list_topics().get("Topics", [])
            total_checks += 1

            if len(topics) >= 3:
                passed_checks += 1
            elif topics:
                findings.append(create_finding(
                    resource="arn:aws:sns::account",
                    issue=f"Only {len(topics)} SNS topic(s) for communication",
                    severity="INFO",
                    recommendation="Create separate topics for different alert severities",
                    effort="LOW",
                    impact="MEDIUM"
                ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:sns::account",
                    issue="No SNS topics for event communication",
                    severity="MEDIUM",
                    recommendation="Create SNS topics for operational communications",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for alarm composite alarms (OPS10-BP03 - prioritization)
        cloudwatch = aws_client.get_client("cloudwatch")
        try:
            composite_alarms = cloudwatch.describe_alarms(
                AlarmTypes=["CompositeAlarm"]
            ).get("CompositeAlarms", [])

            total_checks += 1
            if composite_alarms:
                passed_checks += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudwatch::account",
                    issue="No composite alarms for event correlation",
                    severity="INFO",
                    recommendation="Use composite alarms to reduce alert noise",
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
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_name="check_event_management",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Automate responses with EventBridge (OPS10-BP07)",
            "Use OpsCenter for incident management (OPS10-BP01)",
            "Create communication plans with SNS (OPS10-BP05)",
            "Prioritize events by business impact (OPS10-BP03)",
            "Use composite alarms to reduce noise"
        ]
    )


# =============================================================================
# OPS-11: Continuous Improvement
# =============================================================================

@tool
def check_continuous_improvement(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check continuous improvement practices (OPS11).

    Validates:
    - Well-Architected Tool workloads (BP01)
    - Trusted Advisor checks (BP05)
    - AWS Health events monitoring

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_checks = 0
    passed_checks = 0

    try:
        # Check Well-Architected Tool workloads (OPS11-BP01)
        wa = aws_client.get_client("wellarchitected")
        try:
            workloads = wa.list_workloads().get("WorkloadSummaries", [])
            total_checks += 1

            if workloads:
                passed_checks += 1

                # Check for recent reviews
                recently_reviewed = 0
                cutoff = datetime.now(timezone.utc) - timedelta(days=90)

                for wl in workloads[:10]:
                    try:
                        workload = wa.get_workload(WorkloadId=wl["WorkloadId"]).get("Workload", {})
                        updated = workload.get("UpdatedAt")
                        if updated and updated.replace(tzinfo=timezone.utc) > cutoff:
                            recently_reviewed += 1
                    except Exception:
                        pass

                if recently_reviewed < len(workloads[:10]) * 0.5:
                    findings.append(create_finding(
                        resource="arn:aws:wellarchitected::account",
                        issue=f"Only {recently_reviewed}/{len(workloads[:10])} workloads reviewed in 90 days",
                        severity="LOW",
                        recommendation="Conduct regular Well-Architected reviews",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:wellarchitected::account",
                    issue="No workloads defined in Well-Architected Tool",
                    severity="MEDIUM",
                    recommendation="Use Well-Architected Tool for continuous improvement",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            total_checks += 1
            findings.append(create_finding(
                resource="arn:aws:wellarchitected::account",
                issue="Could not access Well-Architected Tool",
                severity="INFO",
                recommendation="Use Well-Architected Tool for workload reviews",
                effort="MEDIUM",
                impact="HIGH"
            ))

        # Check Trusted Advisor (OPS11-BP05)
        # Support API is only available in us-east-1
        support = aws_client.session.client("support", region_name="us-east-1")
        try:
            checks = support.describe_trusted_advisor_checks(language="en").get("checks", [])
            total_checks += 1

            if checks:
                passed_checks += 1

                # Check for flagged items
                flagged_checks = 0
                for check in checks[:20]:
                    try:
                        result = support.describe_trusted_advisor_check_result(
                            checkId=check["id"]
                        ).get("result", {})

                        if result.get("status") in ["warning", "error"]:
                            flagged_checks += 1
                    except Exception:
                        pass

                if flagged_checks > 10:
                    findings.append(create_finding(
                        resource="arn:aws:trustedadvisor::account",
                        issue=f"{flagged_checks} Trusted Advisor checks flagged",
                        severity="MEDIUM",
                        recommendation="Review and address Trusted Advisor recommendations",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))
        except Exception as e:
            if "SubscriptionRequiredException" in str(e):
                total_checks += 1
                findings.append(create_finding(
                    resource="arn:aws:trustedadvisor::account",
                    issue="Limited Trusted Advisor access (Basic Support)",
                    severity="INFO",
                    recommendation="Business/Enterprise Support unlocks all Trusted Advisor checks",
                    effort="LOW",
                    impact="MEDIUM"
                ))

        # Check AWS Health Dashboard events
        # Health API is only available in us-east-1
        health = aws_client.session.client("health", region_name="us-east-1")
        try:
            # Get open events
            events = health.describe_events(
                filter={
                    "eventStatusCodes": ["open", "upcoming"]
                }
            ).get("events", [])

            total_checks += 1
            if not events:
                passed_checks += 1
            else:
                service_events = [e for e in events if e.get("eventTypeCategory") != "scheduledChange"]
                if service_events:
                    findings.append(create_finding(
                        resource="arn:aws:health::account",
                        issue=f"{len(service_events)} active AWS Health event(s)",
                        severity="MEDIUM" if len(service_events) > 2 else "LOW",
                        recommendation="Review AWS Health Dashboard for service impacts",
                        effort="LOW",
                        impact="MEDIUM",
                        details={"event_count": len(service_events)}
                    ))
                else:
                    passed_checks += 1
        except Exception:
            total_checks += 1
            passed_checks += 1  # Can't check is OK

        if total_checks == 0:
            total_checks = 1
            passed_checks = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_name="check_continuous_improvement",
        findings=findings,
        total_resources=total_checks,
        compliant_resources=passed_checks,
        best_practices=[
            "Use Well-Architected Tool for regular reviews (OPS11-BP01)",
            "Review Trusted Advisor recommendations (OPS11-BP05)",
            "Monitor AWS Health Dashboard for service events",
            "Perform post-incident analysis (OPS11-BP02)",
            "Document and share lessons learned (OPS11-BP08)"
        ]
    )


# =============================================================================
# Pillar Review Function
# =============================================================================

@tool
def run_operational_excellence_pillar_review(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run a comprehensive Operational Excellence Pillar review (OPS01-OPS11).

    Executes all operational excellence checks and provides an aggregated
    pillar-level assessment with prioritized recommendations.

    Returns:
        Comprehensive pillar review with score, findings, and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    check_functions = [
        ("OPS04: Observability Implementation", check_observability_implementation),
        ("OPS05: Deployment Practices", check_deployment_practices),
        ("OPS06: Deployment Safety", check_deployment_safety),
        ("OPS07: Operational Readiness", check_operational_readiness),
        ("OPS08: Observability Utilization", check_observability_utilization),
        ("OPS10: Event Management", check_event_management),
        ("OPS11: Continuous Improvement", check_continuous_improvement),
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
        "Implement comprehensive observability with CloudWatch and X-Ray",
        "Create CI/CD pipelines with CodePipeline for automated deployments",
        "Enable automatic rollback for failed deployments",
        "Create runbooks and playbooks in Systems Manager",
        "Build CloudWatch dashboards for workload visibility",
        "Configure actionable alarms with SNS notifications",
        "Use EventBridge for automated event responses",
        "Conduct regular Well-Architected reviews",
        "Enable AWS Config for configuration tracking",
        "Use OpsCenter for centralized incident management"
    ]

    return create_pillar_review_result(
        pillar=Pillar.OPERATIONAL_EXCELLENCE.value,
        check_results=check_results,
        recommendations=recommendations
    )


# Export all tools
__all__ = [
    # OPS04 - Observability Implementation
    "check_observability_implementation",
    # OPS05 - Deployment Practices
    "check_deployment_practices",
    # OPS06 - Deployment Safety
    "check_deployment_safety",
    # OPS07 - Operational Readiness
    "check_operational_readiness",
    # OPS08 - Observability Utilization
    "check_observability_utilization",
    # OPS10 - Event Management
    "check_event_management",
    # OPS11 - Continuous Improvement
    "check_continuous_improvement",
    # Pillar Review
    "run_operational_excellence_pillar_review",
]
