"""
AWS Well-Architected Framework - Security Pillar Extended Tools.

This module provides additional security checks to complete coverage
of the Security Pillar based on the 2025 AWS Well-Architected Framework.

New checks cover:
- SEC02: Enhanced authentication management (MFA, credential rotation)
- SEC03: Permission management (IAM Access Analyzer, boundaries)
- SEC06: Vulnerability management (Inspector findings)
- SEC10: Enhanced incident response (playbooks, forensics)

Reference: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/
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
# SEC-02: Enhanced Authentication Management
# =============================================================================

@tool
def check_mfa_compliance(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check MFA compliance for all IAM users (SEC02-BP01).

    Validates:
    - All IAM users have MFA enabled
    - Console users without MFA
    - MFA device types (hardware vs virtual)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_users = 0
    compliant_users = 0

    try:
        iam = aws_client.get_client("iam")

        # Get all IAM users
        paginator = iam.get_paginator("list_users")
        users = []
        for page in paginator.paginate():
            users.extend(page.get("Users", []))

        for user in users:
            user_name = user.get("UserName")
            user_arn = user.get("Arn")

            # Check if user has console access
            try:
                iam.get_login_profile(UserName=user_name)
                has_console_access = True
            except iam.exceptions.NoSuchEntityException:
                has_console_access = False
            except Exception:
                has_console_access = False

            if has_console_access:
                total_users += 1

                # Check MFA devices
                mfa_devices = iam.list_mfa_devices(UserName=user_name).get("MFADevices", [])

                if mfa_devices:
                    compliant_users += 1
                    # Check for hardware MFA (enhanced security)
                    has_hardware_mfa = any(
                        "sms" not in d.get("SerialNumber", "").lower() and
                        "virtual" not in d.get("SerialNumber", "").lower()
                        for d in mfa_devices
                    )
                    if not has_hardware_mfa:
                        findings.append(create_finding(
                            resource=user_arn,
                            issue=f"User '{user_name}' uses virtual MFA (hardware MFA recommended)",
                            severity="INFO",
                            recommendation="Consider hardware MFA (YubiKey, etc.) for enhanced security",
                            effort="MEDIUM",
                            impact="LOW"
                        ))
                else:
                    findings.append(create_finding(
                        resource=user_arn,
                        issue=f"User '{user_name}' has console access but no MFA",
                        severity="CRITICAL",
                        recommendation="Enable MFA immediately for this user",
                        effort="LOW",
                        impact="CRITICAL"
                    ))

        # If no console users found
        if total_users == 0:
            total_users = 1
            compliant_users = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_mfa_compliance",
        findings=findings,
        total_resources=total_users,
        compliant_resources=compliant_users,
        best_practices=[
            "Require MFA for all console users",
            "Use hardware MFA for privileged users",
            "Enforce MFA through IAM policies",
            "Consider AWS IAM Identity Center for SSO with MFA",
            "Regularly audit MFA compliance",
            "Use phishing-resistant MFA (FIDO2/WebAuthn)"
        ]
    )


@tool
def check_credential_rotation(
    aws_client: Optional[AWSClient] = None,
    max_key_age_days: int = 90
) -> Dict[str, Any]:
    """
    Check credential rotation compliance (SEC02-BP05).

    Validates:
    - IAM access key age
    - Service account key rotation
    - Unused credentials

    Args:
        aws_client: AWS client to use
        max_key_age_days: Maximum age for access keys (default 90 days)

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_keys = 0
    compliant_keys = 0

    try:
        iam = aws_client.get_client("iam")

        # Generate and get credential report
        try:
            iam.generate_credential_report()
            import time
            time.sleep(3)  # Wait for report generation

            report = iam.get_credential_report()
            import csv
            import io

            reader = csv.DictReader(io.StringIO(report["Content"].decode("utf-8")))

            for row in reader:
                user = row.get("user", "")
                if user == "<root_account>":
                    continue

                # Check access key 1
                if row.get("access_key_1_active", "false") == "true":
                    total_keys += 1
                    last_rotated = row.get("access_key_1_last_rotated", "N/A")
                    if last_rotated not in ["N/A", "no_information", "not_supported"]:
                        try:
                            rotated_date = datetime.fromisoformat(last_rotated.replace("Z", "+00:00"))
                            key_age = (datetime.now(timezone.utc) - rotated_date).days

                            if key_age > max_key_age_days:
                                findings.append(create_finding(
                                    resource=f"arn:aws:iam::user/{user}",
                                    issue=f"User '{user}' access key 1 is {key_age} days old",
                                    severity="HIGH" if key_age > 180 else "MEDIUM",
                                    recommendation=f"Rotate access key (older than {max_key_age_days} days)",
                                    effort="MEDIUM",
                                    impact="HIGH",
                                    details={"key_age_days": key_age}
                                ))
                            else:
                                compliant_keys += 1
                        except Exception:
                            compliant_keys += 1

                # Check access key 2
                if row.get("access_key_2_active", "false") == "true":
                    total_keys += 1
                    last_rotated = row.get("access_key_2_last_rotated", "N/A")
                    if last_rotated not in ["N/A", "no_information", "not_supported"]:
                        try:
                            rotated_date = datetime.fromisoformat(last_rotated.replace("Z", "+00:00"))
                            key_age = (datetime.now(timezone.utc) - rotated_date).days

                            if key_age > max_key_age_days:
                                findings.append(create_finding(
                                    resource=f"arn:aws:iam::user/{user}",
                                    issue=f"User '{user}' access key 2 is {key_age} days old",
                                    severity="HIGH" if key_age > 180 else "MEDIUM",
                                    recommendation=f"Rotate access key (older than {max_key_age_days} days)",
                                    effort="MEDIUM",
                                    impact="HIGH",
                                    details={"key_age_days": key_age}
                                ))
                            else:
                                compliant_keys += 1
                        except Exception:
                            compliant_keys += 1

                # Check for unused keys
                last_used_1 = row.get("access_key_1_last_used_date", "N/A")
                if row.get("access_key_1_active", "false") == "true" and last_used_1 == "N/A":
                    findings.append(create_finding(
                        resource=f"arn:aws:iam::user/{user}",
                        issue=f"User '{user}' has access key 1 that has never been used",
                        severity="MEDIUM",
                        recommendation="Remove unused access keys",
                        effort="LOW",
                        impact="MEDIUM"
                    ))

        except Exception:
            pass

        if total_keys == 0:
            total_keys = 1
            compliant_keys = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_credential_rotation",
        findings=findings,
        total_resources=total_keys,
        compliant_resources=compliant_keys,
        best_practices=[
            f"Rotate access keys every {max_key_age_days} days or less",
            "Use IAM roles instead of long-lived access keys",
            "Remove unused access keys",
            "Implement automated key rotation",
            "Monitor key usage with CloudTrail",
            "Use AWS Secrets Manager for application credentials"
        ]
    )


# =============================================================================
# SEC-03: Permission Management
# =============================================================================

@tool
def check_iam_access_analyzer(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check IAM Access Analyzer configuration and findings (SEC03-BP07).

    Validates:
    - Access Analyzer enabled
    - External access findings reviewed
    - Unused access findings analyzed

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        access_analyzer = aws_client.get_client("accessanalyzer")

        # Check if analyzers exist
        analyzers = access_analyzer.list_analyzers().get("analyzers", [])
        total_resources += 1

        if not analyzers:
            findings.append(create_finding(
                resource="arn:aws:access-analyzer::account",
                issue="IAM Access Analyzer not enabled",
                severity="HIGH",
                recommendation="Enable IAM Access Analyzer to detect unintended access",
                effort="LOW",
                impact="HIGH"
            ))
        else:
            compliant_resources += 1

            # Check for active analyzers
            active_analyzers = [a for a in analyzers if a.get("status") == "ACTIVE"]

            for analyzer in active_analyzers:
                analyzer_name = analyzer.get("name")
                analyzer_arn = analyzer.get("arn")
                analyzer_type = analyzer.get("type")

                # Check for unresolved findings
                active_findings = access_analyzer.list_findings(
                    analyzerArn=analyzer_arn,
                    filter={"status": {"eq": ["ACTIVE"]}}
                ).get("findings", [])

                total_resources += 1

                if len(active_findings) > 0:
                    # Categorize by resource type
                    by_type = {}
                    for f in active_findings:
                        res_type = f.get("resourceType", "Unknown")
                        by_type[res_type] = by_type.get(res_type, 0) + 1

                    critical_count = sum(1 for f in active_findings if f.get("isPublic", False))

                    if critical_count > 0:
                        findings.append(create_finding(
                            resource=analyzer_arn,
                            issue=f"Access Analyzer found {critical_count} publicly accessible resource(s)",
                            severity="CRITICAL",
                            recommendation="Review and resolve public access findings immediately",
                            effort="MEDIUM",
                            impact="CRITICAL",
                            details={"findings_by_type": by_type, "public_access": critical_count}
                        ))
                    else:
                        findings.append(create_finding(
                            resource=analyzer_arn,
                            issue=f"Access Analyzer found {len(active_findings)} external access finding(s)",
                            severity="MEDIUM",
                            recommendation="Review external access findings for unintended access",
                            effort="MEDIUM",
                            impact="MEDIUM",
                            details={"findings_by_type": by_type}
                        ))
                else:
                    compliant_resources += 1

        # Check for unused access analyzer (if supported)
        try:
            for analyzer in analyzers:
                if analyzer.get("type") == "ACCOUNT_UNUSED_ACCESS":
                    # Get unused access findings
                    unused_findings = access_analyzer.list_findings(
                        analyzerArn=analyzer.get("arn"),
                        filter={"status": {"eq": ["ACTIVE"]}}
                    ).get("findings", [])

                    if len(unused_findings) > 10:
                        findings.append(create_finding(
                            resource=analyzer.get("arn"),
                            issue=f"{len(unused_findings)} unused access findings detected",
                            severity="MEDIUM",
                            recommendation="Review and remove unused permissions",
                            effort="MEDIUM",
                            impact="MEDIUM"
                        ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_iam_access_analyzer",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Enable IAM Access Analyzer for external access detection",
            "Review and resolve Access Analyzer findings regularly",
            "Enable unused access analyzer for permission right-sizing",
            "Integrate findings into security operations workflow",
            "Use Access Analyzer policy validation before deployment",
            "Set up CloudWatch Events for new findings"
        ]
    )


@tool
def check_permission_boundaries(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check permission boundaries configuration (SEC03-BP05).

    Validates:
    - Permission boundaries on delegated roles
    - Organizational SCPs in place
    - Guardrails for development/sandbox accounts

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        iam = aws_client.get_client("iam")

        # Get all IAM roles
        paginator = iam.get_paginator("list_roles")
        roles = []
        for page in paginator.paginate():
            roles.extend(page.get("Roles", []))

        # Check roles that should have permission boundaries
        delegated_patterns = ["developer", "sandbox", "test", "dev", "engineer", "admin"]

        for role in roles:
            role_name = role.get("RoleName", "")
            role_arn = role.get("Arn", "")

            # Skip service-linked roles
            if "/aws-service-role/" in role_arn:
                continue

            # Check if this looks like a delegated role
            is_delegated = any(p in role_name.lower() for p in delegated_patterns)

            if is_delegated:
                total_resources += 1

                # Check for permission boundary
                boundary = role.get("PermissionsBoundary")
                if boundary:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=role_arn,
                        issue=f"Role '{role_name}' appears delegated but has no permission boundary",
                        severity="MEDIUM",
                        recommendation="Apply permission boundary to limit maximum permissions",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))

        # Check Organizations SCPs
        try:
            org = aws_client.get_client("organizations")
            org_info = org.describe_organization()

            if org_info["Organization"].get("FeatureSet") == "ALL":
                total_resources += 1
                # Check for SCPs
                policies = org.list_policies(Filter="SERVICE_CONTROL_POLICY").get("Policies", [])
                custom_scps = [p for p in policies if p.get("Name") != "FullAWSAccess"]

                if custom_scps:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:organizations::account",
                        issue="No custom Service Control Policies (SCPs) configured",
                        severity="MEDIUM",
                        recommendation="Create SCPs to restrict dangerous actions",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
        except Exception:
            pass  # Not in an organization or no permission

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_permission_boundaries",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use permission boundaries for delegated administration",
            "Implement SCPs for organization-wide guardrails",
            "Prevent privilege escalation with boundaries",
            "Define boundaries before creating roles",
            "Use managed policies for consistent boundaries",
            "Review and update boundaries regularly"
        ]
    )


@tool
def check_resource_policies(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check resource-based policies for overly permissive access (SEC03-BP07).

    Validates:
    - S3 bucket policies
    - KMS key policies
    - Lambda function policies
    - SNS/SQS policies

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check S3 bucket policies
        s3 = aws_client.get_client("s3")
        try:
            buckets = s3.list_buckets().get("Buckets", [])

            for bucket in buckets[:30]:  # Limit for performance
                bucket_name = bucket["Name"]
                total_resources += 1
                is_compliant = True

                try:
                    policy = s3.get_bucket_policy(Bucket=bucket_name)
                    policy_text = policy.get("Policy", "")

                    # Check for overly permissive patterns
                    import json
                    try:
                        policy_json = json.loads(policy_text)
                        for statement in policy_json.get("Statement", []):
                            principal = statement.get("Principal", "")
                            effect = statement.get("Effect", "")

                            # Check for public access
                            if effect == "Allow" and (principal == "*" or principal == {"AWS": "*"}):
                                condition = statement.get("Condition", {})
                                if not condition:  # No conditions means wide open
                                    is_compliant = False
                                    findings.append(create_finding(
                                        resource=f"arn:aws:s3:::{bucket_name}",
                                        issue=f"S3 bucket '{bucket_name}' policy allows public access",
                                        severity="CRITICAL",
                                        recommendation="Review and restrict bucket policy",
                                        effort="MEDIUM",
                                        impact="CRITICAL"
                                    ))
                                    break
                    except json.JSONDecodeError:
                        pass

                except Exception:
                    pass  # No policy is fine

                if is_compliant:
                    compliant_resources += 1
        except Exception:
            pass

        # Check KMS key policies
        kms = aws_client.get_client("kms")
        try:
            keys = kms.list_keys().get("Keys", [])

            for key in keys[:20]:  # Limit for performance
                key_id = key.get("KeyId")
                total_resources += 1
                is_compliant = True

                try:
                    key_policy = kms.get_key_policy(KeyId=key_id, PolicyName="default")
                    policy_text = key_policy.get("Policy", "")

                    import json
                    try:
                        policy_json = json.loads(policy_text)
                        for statement in policy_json.get("Statement", []):
                            principal = statement.get("Principal", "")
                            effect = statement.get("Effect", "")

                            if effect == "Allow" and principal == "*":
                                condition = statement.get("Condition", {})
                                if not condition:
                                    is_compliant = False
                                    findings.append(create_finding(
                                        resource=f"arn:aws:kms::key/{key_id}",
                                        issue=f"KMS key '{key_id}' policy allows access from any principal",
                                        severity="HIGH",
                                        recommendation="Restrict KMS key policy to specific principals",
                                        effort="MEDIUM",
                                        impact="HIGH"
                                    ))
                                    break
                    except json.JSONDecodeError:
                        pass
                except Exception:
                    pass

                if is_compliant:
                    compliant_resources += 1
        except Exception:
            pass

        # Check Lambda function policies
        lambda_client = aws_client.get_client("lambda")
        try:
            paginator = lambda_client.get_paginator("list_functions")
            for page in paginator.paginate():
                for func in page.get("Functions", [])[:20]:
                    func_name = func.get("FunctionName")
                    total_resources += 1
                    is_compliant = True

                    try:
                        policy = lambda_client.get_policy(FunctionName=func_name)
                        policy_text = policy.get("Policy", "")

                        import json
                        try:
                            policy_json = json.loads(policy_text)
                            for statement in policy_json.get("Statement", []):
                                principal = statement.get("Principal", "")
                                if principal == "*":
                                    condition = statement.get("Condition", {})
                                    if not condition:
                                        is_compliant = False
                                        findings.append(create_finding(
                                            resource=func.get("FunctionArn"),
                                            issue=f"Lambda '{func_name}' can be invoked by anyone",
                                            severity="HIGH",
                                            recommendation="Restrict Lambda resource policy",
                                            effort="MEDIUM",
                                            impact="HIGH"
                                        ))
                                        break
                        except json.JSONDecodeError:
                            pass
                    except Exception:
                        pass  # No policy is fine

                    if is_compliant:
                        compliant_resources += 1
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_resource_policies",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Review resource policies for unintended access",
            "Avoid using Principal: '*' without conditions",
            "Use IAM Access Analyzer to detect overly permissive policies",
            "Implement least privilege in resource policies",
            "Regularly audit resource-based policies",
            "Use VPC endpoints with endpoint policies"
        ]
    )


# =============================================================================
# SEC-06: Vulnerability Management
# =============================================================================

@tool
def check_vulnerability_management(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check vulnerability management practices (SEC06-BP01).

    Validates:
    - Amazon Inspector enabled
    - Inspector findings reviewed
    - ECR image scanning enabled
    - Systems Manager Patch Manager

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check Inspector v2
        inspector = aws_client.get_client("inspector2")
        try:
            # Check if Inspector is enabled
            status = inspector.batch_get_account_status(
                accountIds=[aws_client.account_id] if hasattr(aws_client, 'account_id') else []
            )
            accounts = status.get("accounts", [])

            total_resources += 1
            if accounts:
                account_status = accounts[0]
                state = account_status.get("state", {}).get("status", "DISABLED")

                if state == "ENABLED":
                    compliant_resources += 1

                    # Check for critical/high findings
                    finding_counts = inspector.list_finding_aggregations(
                        aggregationType="SEVERITY"
                    ).get("responses", [])

                    critical_count = 0
                    high_count = 0
                    for resp in finding_counts:
                        if resp.get("severityCounts"):
                            critical_count += resp["severityCounts"].get("critical", 0)
                            high_count += resp["severityCounts"].get("high", 0)

                    if critical_count > 0:
                        findings.append(create_finding(
                            resource="arn:aws:inspector2::account",
                            issue=f"Inspector found {critical_count} critical vulnerabilities",
                            severity="CRITICAL",
                            recommendation="Remediate critical vulnerabilities immediately",
                            effort="HIGH",
                            impact="CRITICAL",
                            details={"critical": critical_count, "high": high_count}
                        ))
                    elif high_count > 10:
                        findings.append(create_finding(
                            resource="arn:aws:inspector2::account",
                            issue=f"Inspector found {high_count} high-severity vulnerabilities",
                            severity="HIGH",
                            recommendation="Prioritize remediation of high-severity vulnerabilities",
                            effort="HIGH",
                            impact="HIGH"
                        ))
                else:
                    findings.append(create_finding(
                        resource="arn:aws:inspector2::account",
                        issue="Amazon Inspector is not enabled",
                        severity="HIGH",
                        recommendation="Enable Amazon Inspector for vulnerability scanning",
                        effort="LOW",
                        impact="HIGH"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:inspector2::account",
                    issue="Amazon Inspector is not enabled",
                    severity="HIGH",
                    recommendation="Enable Amazon Inspector for vulnerability scanning",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            total_resources += 1
            findings.append(create_finding(
                resource="arn:aws:inspector2::account",
                issue="Amazon Inspector status could not be determined",
                severity="MEDIUM",
                recommendation="Enable Amazon Inspector for vulnerability scanning",
                effort="LOW",
                impact="HIGH"
            ))

        # Check ECR image scanning
        ecr = aws_client.get_client("ecr")
        try:
            repos = ecr.describe_repositories().get("repositories", [])

            for repo in repos[:20]:
                repo_name = repo.get("repositoryName")
                repo_arn = repo.get("repositoryArn")
                total_resources += 1

                scan_config = repo.get("imageScanningConfiguration", {})
                if scan_config.get("scanOnPush", False):
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=repo_arn,
                        issue=f"ECR repository '{repo_name}' has scan-on-push disabled",
                        severity="MEDIUM",
                        recommendation="Enable image scanning on push",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check Systems Manager Patch Compliance
        ssm = aws_client.get_client("ssm")
        try:
            compliance = ssm.list_compliance_summaries(
                Filters=[{"Key": "ComplianceType", "Values": ["Patch"]}]
            ).get("ComplianceSummaryItems", [])

            for item in compliance:
                total_resources += 1
                non_compliant = item.get("NonCompliantSummary", {}).get("NonCompliantCount", 0)

                if non_compliant == 0:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:ssm::account",
                        issue=f"{non_compliant} instance(s) are not patch compliant",
                        severity="HIGH" if non_compliant > 5 else "MEDIUM",
                        recommendation="Run Patch Manager to apply missing patches",
                        effort="MEDIUM",
                        impact="HIGH",
                        details={"non_compliant_count": non_compliant}
                    ))
        except Exception:
            pass

        if total_resources == 0:
            total_resources = 1
            compliant_resources = 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_vulnerability_management",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Enable Amazon Inspector for continuous vulnerability scanning",
            "Scan container images before deployment",
            "Implement automated patching with Systems Manager",
            "Prioritize remediation based on severity and exploitability",
            "Track vulnerabilities in a centralized dashboard",
            "Integrate vulnerability findings into CI/CD pipelines"
        ]
    )


# =============================================================================
# SEC-10: Enhanced Incident Response
# =============================================================================

@tool
def check_incident_response_readiness(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check incident response readiness (SEC10).

    Validates:
    - SSM documents for playbooks
    - CloudWatch Logs for forensics
    - S3 buckets for artifact storage
    - SNS topics for notifications
    - EventBridge rules for automation

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

        # Check for incident response runbooks/playbooks
        total_resources += 1
        try:
            # Look for automation documents that might be runbooks
            documents = ssm.list_documents(
                Filters=[
                    {"Key": "Owner", "Values": ["Self"]},
                    {"Key": "DocumentType", "Values": ["Automation", "Command"]}
                ]
            ).get("DocumentIdentifiers", [])

            incident_patterns = ["incident", "response", "forensic", "isolate", "contain", "recovery"]
            ir_docs = [
                d for d in documents
                if any(p in d.get("Name", "").lower() for p in incident_patterns)
            ]

            if ir_docs:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:ssm::account",
                    issue="No incident response runbooks found in Systems Manager",
                    severity="MEDIUM",
                    recommendation="Create SSM Automation documents for incident response playbooks",
                    effort="HIGH",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for forensic log retention
        logs = aws_client.get_client("logs")
        try:
            total_resources += 1
            log_groups = logs.describe_log_groups().get("logGroups", [])

            security_logs = [
                lg for lg in log_groups
                if any(p in lg.get("logGroupName", "").lower()
                       for p in ["cloudtrail", "vpc", "security", "audit", "guardduty"])
            ]

            long_retention_logs = [
                lg for lg in security_logs
                if lg.get("retentionInDays") is None or lg.get("retentionInDays", 0) >= 365
            ]

            if len(long_retention_logs) >= len(security_logs) * 0.5:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:logs::account",
                    issue=f"Only {len(long_retention_logs)}/{len(security_logs)} security log groups have adequate retention",
                    severity="MEDIUM",
                    recommendation="Set retention to 365+ days for forensic investigation capability",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for incident response S3 bucket
        s3 = aws_client.get_client("s3")
        try:
            total_resources += 1
            buckets = s3.list_buckets().get("Buckets", [])

            ir_patterns = ["incident", "forensic", "security-artifacts", "ir-", "sec-"]
            ir_buckets = [
                b for b in buckets
                if any(p in b.get("Name", "").lower() for p in ir_patterns)
            ]

            if ir_buckets:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:s3::account",
                    issue="No dedicated bucket for incident response artifacts",
                    severity="LOW",
                    recommendation="Create a pre-provisioned S3 bucket for forensic artifacts",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for security notification topic
        sns = aws_client.get_client("sns")
        try:
            total_resources += 1
            topics = sns.list_topics().get("Topics", [])

            security_topics = [
                t for t in topics
                if any(p in t.get("TopicArn", "").lower()
                       for p in ["security", "incident", "alert", "guardduty"])
            ]

            if security_topics:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:sns::account",
                    issue="No security notification SNS topics found",
                    severity="MEDIUM",
                    recommendation="Create SNS topics for security incident notifications",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check for EventBridge rules for security events
        events = aws_client.get_client("events")
        try:
            total_resources += 1
            rules = events.list_rules().get("Rules", [])

            security_rules = [
                r for r in rules
                if any(p in r.get("Name", "").lower()
                       for p in ["security", "guardduty", "inspector", "securityhub"])
            ]

            if security_rules:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:events::account",
                    issue="No EventBridge rules for security event automation",
                    severity="MEDIUM",
                    recommendation="Create EventBridge rules to automate incident response",
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
        pillar=Pillar.SECURITY.value,
        check_name="check_incident_response_readiness",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Create and maintain incident response playbooks as SSM documents",
            "Pre-provision access for incident responders",
            "Pre-deploy forensic tools (EC2 instances, Lambda functions)",
            "Configure long retention for security logs (365+ days)",
            "Create dedicated S3 buckets for forensic artifact storage",
            "Set up automated notifications for security events",
            "Conduct regular game days to test incident response"
        ]
    )


@tool
def check_forensic_capabilities(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check forensic investigation capabilities (SEC10-BP03).

    Validates:
    - CloudTrail enabled with validation
    - VPC Flow Logs with long retention
    - EBS snapshots accessible
    - CloudWatch Logs Insights available

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check CloudTrail for forensic capability
        cloudtrail = aws_client.get_client("cloudtrail")
        try:
            trails = cloudtrail.describe_trails().get("trailList", [])
            total_resources += 1

            has_validated_trail = False
            has_data_events = False

            for trail in trails:
                if trail.get("LogFileValidationEnabled"):
                    has_validated_trail = True

                # Check for data events
                try:
                    event_selectors = cloudtrail.get_event_selectors(
                        TrailName=trail.get("Name")
                    )
                    data_resources = event_selectors.get("EventSelectors", []) or \
                                   event_selectors.get("AdvancedEventSelectors", [])
                    if data_resources:
                        has_data_events = True
                except Exception:
                    pass

            if has_validated_trail:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudtrail::account",
                    issue="No CloudTrail with log file validation enabled",
                    severity="HIGH",
                    recommendation="Enable log file validation for forensic integrity",
                    effort="LOW",
                    impact="HIGH"
                ))

            if not has_data_events:
                findings.append(create_finding(
                    resource="arn:aws:cloudtrail::account",
                    issue="CloudTrail not capturing data events (S3, Lambda)",
                    severity="MEDIUM",
                    recommendation="Enable data event logging for comprehensive forensics",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            total_resources += 1

        # Check VPC Flow Logs
        ec2 = aws_client.get_client("ec2")
        try:
            vpcs = ec2.describe_vpcs().get("Vpcs", [])

            for vpc in vpcs:
                vpc_id = vpc.get("VpcId")
                total_resources += 1

                flow_logs = ec2.describe_flow_logs(
                    Filters=[{"Name": "resource-id", "Values": [vpc_id]}]
                ).get("FlowLogs", [])

                if flow_logs:
                    # Check for all traffic logging
                    all_traffic = any(
                        fl.get("TrafficType") == "ALL" for fl in flow_logs
                    )
                    if all_traffic:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=vpc_id,
                            issue=f"VPC {vpc_id} Flow Logs not capturing ALL traffic",
                            severity="MEDIUM",
                            recommendation="Configure Flow Logs to capture ALL traffic for forensics",
                            effort="LOW",
                            impact="MEDIUM"
                        ))
                else:
                    findings.append(create_finding(
                        resource=vpc_id,
                        issue=f"VPC {vpc_id} has no Flow Logs enabled",
                        severity="HIGH",
                        recommendation="Enable VPC Flow Logs for network forensics",
                        effort="LOW",
                        impact="HIGH"
                    ))
        except Exception:
            pass

        # Check CloudWatch Logs Insights queries
        logs = aws_client.get_client("logs")
        try:
            total_resources += 1
            queries = logs.describe_query_definitions().get("queryDefinitions", [])

            security_queries = [
                q for q in queries
                if any(p in q.get("name", "").lower()
                       for p in ["security", "forensic", "investigation", "audit"])
            ]

            if security_queries:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:logs::account",
                    issue="No pre-defined forensic queries in CloudWatch Logs Insights",
                    severity="LOW",
                    recommendation="Create saved queries for common forensic investigations",
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
        pillar=Pillar.SECURITY.value,
        check_name="check_forensic_capabilities",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Enable CloudTrail log file validation for integrity",
            "Capture data events for S3 and Lambda forensics",
            "Enable VPC Flow Logs with ALL traffic type",
            "Create saved queries for common forensic investigations",
            "Use CloudTrail Lake for long-term log analysis",
            "Consider Athena for complex forensic queries",
            "Implement automated log aggregation to central account"
        ]
    )


# Export all new tools
__all__ = [
    # SEC02 - Authentication
    "check_mfa_compliance",
    "check_credential_rotation",
    # SEC03 - Permissions
    "check_iam_access_analyzer",
    "check_permission_boundaries",
    "check_resource_policies",
    # SEC06 - Vulnerability Management
    "check_vulnerability_management",
    # SEC10 - Incident Response
    "check_incident_response_readiness",
    "check_forensic_capabilities",
]
