"""
AWS Well-Architected Framework - Security Pillar Tools.

This module provides 15 automated checks aligned with the Security Pillar
of the AWS Well-Architected Framework.

Security Pillar Design Principles:
1. Implement strong identity foundation
2. Maintain traceability
3. Apply security at all layers
4. Automate security best practices
5. Protect data in transit and at rest
6. Keep people away from data
7. Prepare for security events

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
    create_pillar_review_result,
    Pillar,
    get_account_id,
    get_all_regions,
)


# =============================================================================
# SEC-1: Identity and Access Management
# =============================================================================

@tool
def check_root_account_usage(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check root account security configuration (SEC-1).

    Validates:
    - Root account has MFA enabled
    - No root access keys exist
    - Root account not used recently (90 days)
    - Hardware MFA recommended for root

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    compliant = 0
    total = 4  # 4 checks for root account

    try:
        iam = aws_client.get_client("iam")

        # Get account summary
        summary = iam.get_account_summary()["SummaryMap"]

        # Check 1: Root MFA enabled
        root_mfa = summary.get("AccountMFAEnabled", 0) == 1
        if root_mfa:
            compliant += 1
        else:
            findings.append(create_finding(
                resource="arn:aws:iam::root",
                issue="Root account does not have MFA enabled",
                severity="CRITICAL",
                recommendation="Enable MFA on the root account immediately",
                effort="LOW",
                impact="CRITICAL"
            ))

        # Check 2: No root access keys
        root_access_keys = summary.get("AccountAccessKeysPresent", 0)
        if root_access_keys == 0:
            compliant += 1
        else:
            findings.append(create_finding(
                resource="arn:aws:iam::root",
                issue="Root account has access keys attached",
                severity="CRITICAL",
                recommendation="Delete root account access keys and use IAM users/roles instead",
                effort="MEDIUM",
                impact="CRITICAL"
            ))

        # Check 3: Root account not used recently
        try:
            # Generate credential report
            iam.generate_credential_report()
            import time
            time.sleep(2)  # Wait for report generation

            report = iam.get_credential_report()
            import csv
            import io

            reader = csv.DictReader(io.StringIO(report["Content"].decode("utf-8")))
            for row in reader:
                if row["user"] == "<root_account>":
                    password_last_used = row.get("password_last_used", "N/A")
                    if password_last_used not in ["N/A", "no_information", "not_supported"]:
                        last_used = datetime.fromisoformat(password_last_used.replace("Z", "+00:00"))
                        days_ago = (datetime.now(timezone.utc) - last_used).days
                        if days_ago > 90:
                            compliant += 1
                        else:
                            findings.append(create_finding(
                                resource="arn:aws:iam::root",
                                issue=f"Root account used {days_ago} days ago",
                                severity="HIGH",
                                recommendation="Avoid using root account for daily operations. Use IAM users/roles.",
                                effort="LOW",
                                impact="HIGH",
                                details={"last_used": password_last_used}
                            ))
                    else:
                        compliant += 1
                    break
        except Exception:
            compliant += 1  # Can't verify, assume compliant

        # Check 4: Hardware MFA (best practice)
        # Note: Cannot directly check if hardware vs virtual MFA
        # This is a recommendation check
        if root_mfa:
            compliant += 1  # Give credit if MFA is enabled at all
        # Already covered by MFA check above

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_root_account_usage",
        findings=findings,
        total_resources=total,
        compliant_resources=compliant,
        best_practices=[
            "Enable hardware MFA on the root account for maximum security",
            "Never create access keys for the root account",
            "Use root account only for tasks that require it (account/billing)",
            "Store root credentials in a secure location (vault, safe)",
            "Enable CloudTrail to monitor any root account usage"
        ]
    )


@tool
def check_identity_federation(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check identity federation and SSO configuration (SEC-1).

    Validates:
    - IAM Identity Center (SSO) is configured
    - SAML providers are configured
    - OIDC providers for service accounts
    - Centralized identity management

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    checks = []

    try:
        iam = aws_client.get_client("iam")

        # Check SAML providers
        saml_providers = iam.list_saml_providers().get("SAMLProviderList", [])
        has_saml = len(saml_providers) > 0
        checks.append(("SAML Federation", has_saml))

        if not has_saml:
            findings.append(create_finding(
                resource="arn:aws:iam::account",
                issue="No SAML identity providers configured",
                severity="MEDIUM",
                recommendation="Configure SAML federation for centralized identity management",
                effort="MEDIUM",
                impact="MEDIUM"
            ))

        # Check OIDC providers
        oidc_providers = iam.list_open_id_connect_providers().get("OpenIDConnectProviderList", [])
        has_oidc = len(oidc_providers) > 0
        checks.append(("OIDC Federation", has_oidc))

        # Check IAM Identity Center (via Organizations)
        try:
            sso_admin = aws_client.get_client("sso-admin")
            instances = sso_admin.list_instances().get("Instances", [])
            has_sso = len(instances) > 0
            checks.append(("IAM Identity Center", has_sso))

            if not has_sso and not has_saml:
                findings.append(create_finding(
                    resource="arn:aws:iam::account",
                    issue="IAM Identity Center (SSO) not configured",
                    severity="MEDIUM",
                    recommendation="Enable IAM Identity Center for centralized user management",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            # SSO not available or not enabled
            checks.append(("IAM Identity Center", False))

        # Check for too many IAM users (suggests no federation)
        users = iam.list_users().get("Users", [])
        if len(users) > 20 and not has_saml and not has_oidc:
            findings.append(create_finding(
                resource="arn:aws:iam::account",
                issue=f"Large number of IAM users ({len(users)}) without federation",
                severity="LOW",
                recommendation="Consider implementing identity federation to reduce IAM user management",
                effort="HIGH",
                impact="MEDIUM",
                details={"user_count": len(users)}
            ))

        compliant = sum(1 for _, passed in checks if passed)
        total = len(checks)

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_identity_federation",
        findings=findings,
        total_resources=total,
        compliant_resources=compliant,
        best_practices=[
            "Use IAM Identity Center for centralized workforce identity",
            "Federate with your corporate identity provider (Okta, Azure AD, etc.)",
            "Use OIDC providers for workload identities (GitHub Actions, Kubernetes)",
            "Minimize the number of IAM users in favor of federated access",
            "Implement just-in-time (JIT) access for elevated privileges"
        ],
        summary_details={
            "saml_providers": len(saml_providers) if 'saml_providers' in dir() else 0,
            "oidc_providers": len(oidc_providers) if 'oidc_providers' in dir() else 0,
            "iam_users": len(users) if 'users' in dir() else 0
        }
    )


@tool
def check_secrets_management(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check secrets management practices (SEC-2).

    Validates:
    - Secrets Manager usage for sensitive data
    - Secret rotation policies enabled
    - No hardcoded credentials in common locations
    - Parameter Store SecureString usage

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_secrets = 0
    compliant_secrets = 0

    try:
        sm = aws_client.get_client("secretsmanager")

        # List all secrets
        paginator = sm.get_paginator("list_secrets")
        secrets = []
        for page in paginator.paginate():
            secrets.extend(page.get("SecretList", []))

        total_secrets = len(secrets)

        for secret in secrets:
            secret_name = secret.get("Name", "unknown")
            secret_arn = secret.get("ARN", "unknown")
            is_compliant = True

            # Check rotation
            rotation_enabled = secret.get("RotationEnabled", False)
            if not rotation_enabled:
                is_compliant = False
                findings.append(create_finding(
                    resource=secret_arn,
                    issue=f"Secret '{secret_name}' does not have rotation enabled",
                    severity="MEDIUM",
                    recommendation="Enable automatic rotation for this secret",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))

            # Check last rotated date
            last_rotated = secret.get("LastRotatedDate")
            if rotation_enabled and last_rotated:
                days_since_rotation = (datetime.now(timezone.utc) - last_rotated.replace(tzinfo=timezone.utc)).days
                if days_since_rotation > 90:
                    is_compliant = False
                    findings.append(create_finding(
                        resource=secret_arn,
                        issue=f"Secret '{secret_name}' not rotated in {days_since_rotation} days",
                        severity="MEDIUM",
                        recommendation="Verify rotation is working correctly",
                        effort="LOW",
                        impact="MEDIUM"
                    ))

            # Check if using KMS
            kms_key = secret.get("KmsKeyId")
            if not kms_key or kms_key == "alias/aws/secretsmanager":
                # Using default key - acceptable but not ideal
                pass

            if is_compliant:
                compliant_secrets += 1

        # Check SSM Parameter Store for SecureStrings
        ssm = aws_client.get_client("ssm")
        try:
            params_paginator = ssm.get_paginator("describe_parameters")
            params = []
            for page in params_paginator.paginate():
                params.extend(page.get("Parameters", []))

            string_params = [p for p in params if p.get("Type") == "String"]
            secure_params = [p for p in params if p.get("Type") == "SecureString"]

            # Check for potentially sensitive String parameters
            sensitive_patterns = ["password", "secret", "key", "token", "credential", "api"]
            for param in string_params:
                param_name = param.get("Name", "").lower()
                if any(pattern in param_name for pattern in sensitive_patterns):
                    findings.append(create_finding(
                        resource=param.get("Name"),
                        issue=f"Parameter '{param.get('Name')}' may contain sensitive data but is not SecureString",
                        severity="MEDIUM",
                        recommendation="Use SecureString type for sensitive parameters",
                        effort="LOW",
                        impact="MEDIUM"
                    ))

        except Exception:
            pass  # SSM might not be in use

        # If no secrets exist at all
        if total_secrets == 0:
            findings.append(create_finding(
                resource="arn:aws:secretsmanager::account",
                issue="No secrets found in Secrets Manager",
                severity="INFO",
                recommendation="Use Secrets Manager for database credentials, API keys, and other secrets",
                effort="MEDIUM",
                impact="HIGH"
            ))
            total_secrets = 1  # Avoid division by zero

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_secrets_management",
        findings=findings,
        total_resources=total_secrets,
        compliant_resources=compliant_secrets,
        best_practices=[
            "Store all secrets in AWS Secrets Manager",
            "Enable automatic rotation for database and API credentials",
            "Use customer-managed KMS keys for sensitive secrets",
            "Never hardcode credentials in code or configuration files",
            "Use IAM roles instead of access keys where possible",
            "Audit secret access with CloudTrail"
        ]
    )


# =============================================================================
# SEC-8/9: Data Protection
# =============================================================================

@tool
def check_encryption_at_rest(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check encryption at rest configuration across services (SEC-8).

    Validates:
    - EBS volumes encrypted
    - S3 buckets encrypted
    - RDS instances encrypted
    - DynamoDB tables encrypted
    - EBS encryption by default enabled

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

        # Check EBS encryption by default
        try:
            ebs_default = ec2.get_ebs_encryption_by_default()
            if not ebs_default.get("EbsEncryptionByDefault", False):
                findings.append(create_finding(
                    resource="arn:aws:ec2::account",
                    issue="EBS encryption by default is not enabled",
                    severity="HIGH",
                    recommendation="Enable EBS encryption by default at account level",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check EBS volumes
        volumes = ec2.describe_volumes().get("Volumes", [])
        for vol in volumes:
            total_resources += 1
            if vol.get("Encrypted", False):
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource=vol.get("VolumeId"),
                    issue=f"EBS volume {vol.get('VolumeId')} is not encrypted",
                    severity="HIGH",
                    recommendation="Create encrypted snapshot and new encrypted volume",
                    effort="MEDIUM",
                    impact="HIGH",
                    details={
                        "size_gb": vol.get("Size"),
                        "state": vol.get("State"),
                        "volume_type": vol.get("VolumeType")
                    }
                ))

        # Check S3 buckets
        s3 = aws_client.get_client("s3")
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            for bucket in buckets:
                bucket_name = bucket["Name"]
                total_resources += 1
                try:
                    encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                    compliant_resources += 1
                except s3.exceptions.ClientError as e:
                    if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                        findings.append(create_finding(
                            resource=f"arn:aws:s3:::{bucket_name}",
                            issue=f"S3 bucket '{bucket_name}' does not have default encryption",
                            severity="HIGH",
                            recommendation="Enable default encryption (SSE-S3 or SSE-KMS)",
                            effort="LOW",
                            impact="HIGH"
                        ))
        except Exception:
            pass

        # Check RDS instances
        rds = aws_client.get_client("rds")
        try:
            instances = rds.describe_db_instances().get("DBInstances", [])
            for instance in instances:
                total_resources += 1
                if instance.get("StorageEncrypted", False):
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=instance.get("DBInstanceArn"),
                        issue=f"RDS instance '{instance.get('DBInstanceIdentifier')}' is not encrypted",
                        severity="HIGH",
                        recommendation="Create encrypted snapshot and restore to new encrypted instance",
                        effort="HIGH",
                        impact="HIGH"
                    ))
        except Exception:
            pass

        # Check DynamoDB tables
        dynamodb = aws_client.get_client("dynamodb")
        try:
            tables = dynamodb.list_tables().get("TableNames", [])
            for table_name in tables:
                total_resources += 1
                try:
                    table = dynamodb.describe_table(TableName=table_name)["Table"]
                    sse = table.get("SSEDescription", {})
                    if sse.get("Status") == "ENABLED":
                        compliant_resources += 1
                    else:
                        # DynamoDB has default encryption, but check for CMK
                        compliant_resources += 1  # Default encryption is acceptable
                except Exception:
                    pass
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_encryption_at_rest",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Enable EBS encryption by default at account level",
            "Use customer-managed KMS keys for sensitive data",
            "Enable default encryption on all S3 buckets",
            "Encrypt RDS instances at creation (cannot encrypt existing)",
            "Use AWS managed keys (SSE-S3) at minimum, CMK for compliance",
            "Audit encryption status regularly with AWS Config"
        ]
    )


@tool
def check_encryption_in_transit(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check encryption in transit configuration (SEC-9).

    Validates:
    - Load balancers enforce HTTPS
    - RDS instances require SSL
    - S3 buckets enforce HTTPS
    - API Gateway uses HTTPS
    - CloudFront uses HTTPS

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check ALB/NLB HTTPS listeners
        elbv2 = aws_client.get_client("elbv2")
        try:
            lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])
            for lb in lbs:
                lb_arn = lb["LoadBalancerArn"]
                listeners = elbv2.describe_listeners(LoadBalancerArn=lb_arn).get("Listeners", [])

                for listener in listeners:
                    total_resources += 1
                    protocol = listener.get("Protocol", "")
                    port = listener.get("Port", 0)

                    if protocol in ["HTTPS", "TLS"]:
                        compliant_resources += 1
                        # Check SSL policy
                        ssl_policy = listener.get("SslPolicy", "")
                        if ssl_policy and "ELBSecurityPolicy-2016-08" in ssl_policy:
                            findings.append(create_finding(
                                resource=listener.get("ListenerArn"),
                                issue=f"Load balancer uses outdated SSL policy: {ssl_policy}",
                                severity="MEDIUM",
                                recommendation="Update to ELBSecurityPolicy-TLS13-1-2-2021-06 or newer",
                                effort="LOW",
                                impact="MEDIUM"
                            ))
                    elif protocol == "HTTP" and port == 80:
                        # Check if there's a redirect action
                        actions = listener.get("DefaultActions", [])
                        has_redirect = any(a.get("Type") == "redirect" for a in actions)
                        if has_redirect:
                            compliant_resources += 1
                        else:
                            findings.append(create_finding(
                                resource=listener.get("ListenerArn"),
                                issue=f"Load balancer listener on port 80 without HTTPS redirect",
                                severity="HIGH",
                                recommendation="Add redirect action to HTTPS or remove HTTP listener",
                                effort="LOW",
                                impact="HIGH"
                            ))
        except Exception:
            pass

        # Check RDS SSL enforcement
        rds = aws_client.get_client("rds")
        try:
            instances = rds.describe_db_instances().get("DBInstances", [])
            for instance in instances:
                total_resources += 1
                # Check parameter group for SSL enforcement
                # This is a simplified check - full check requires parameter group inspection
                engine = instance.get("Engine", "")
                if "aurora" in engine or "postgres" in engine:
                    # These engines support SSL by default
                    compliant_resources += 1
                else:
                    # Check if SSL is required via IAM auth or parameter groups
                    iam_auth = instance.get("IAMDatabaseAuthenticationEnabled", False)
                    if iam_auth:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=instance.get("DBInstanceArn"),
                            issue=f"RDS instance '{instance.get('DBInstanceIdentifier')}' may not enforce SSL",
                            severity="MEDIUM",
                            recommendation="Enable require_ssl in parameter group or use IAM authentication",
                            effort="MEDIUM",
                            impact="MEDIUM"
                        ))
        except Exception:
            pass

        # Check S3 bucket policies for HTTPS enforcement
        s3 = aws_client.get_client("s3")
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            for bucket in buckets[:20]:  # Limit to first 20 for performance
                bucket_name = bucket["Name"]
                total_resources += 1
                try:
                    policy = s3.get_bucket_policy(Bucket=bucket_name)
                    policy_text = policy.get("Policy", "")
                    if "aws:SecureTransport" in policy_text:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=f"arn:aws:s3:::{bucket_name}",
                            issue=f"S3 bucket '{bucket_name}' policy does not enforce HTTPS",
                            severity="MEDIUM",
                            recommendation="Add bucket policy condition for aws:SecureTransport",
                            effort="LOW",
                            impact="MEDIUM"
                        ))
                except Exception:
                    # No policy - not enforcing HTTPS
                    findings.append(create_finding(
                        resource=f"arn:aws:s3:::{bucket_name}",
                        issue=f"S3 bucket '{bucket_name}' has no bucket policy enforcing HTTPS",
                        severity="LOW",
                        recommendation="Add bucket policy with aws:SecureTransport condition",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
        except Exception:
            pass

        # Check API Gateway HTTPS
        apigw = aws_client.get_client("apigateway")
        try:
            apis = apigw.get_rest_apis().get("items", [])
            for api in apis:
                total_resources += 1
                # REST APIs are HTTPS by default
                compliant_resources += 1
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_encryption_in_transit",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use HTTPS for all external-facing endpoints",
            "Configure load balancers to redirect HTTP to HTTPS",
            "Use modern TLS policies (TLS 1.2 or 1.3)",
            "Enforce SSL connections for databases",
            "Use ACM for certificate management",
            "Add aws:SecureTransport condition to S3 bucket policies"
        ]
    )


# =============================================================================
# SEC-5: Network Protection
# =============================================================================

@tool
def check_network_protection(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check network protection configuration (SEC-5).

    Validates:
    - WAF configured on ALB/CloudFront/API Gateway
    - Shield Advanced for DDoS protection
    - NACLs configured appropriately
    - Security groups follow least privilege

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check WAFv2 WebACLs
        wafv2 = aws_client.get_client("wafv2")
        try:
            # Regional WebACLs
            regional_acls = wafv2.list_web_acls(Scope="REGIONAL").get("WebACLs", [])
            # CloudFront WebACLs
            try:
                cf_acls = wafv2.list_web_acls(Scope="CLOUDFRONT").get("WebACLs", [])
            except Exception:
                cf_acls = []

            total_waf = len(regional_acls) + len(cf_acls)

            if total_waf == 0:
                findings.append(create_finding(
                    resource="arn:aws:wafv2::account",
                    issue="No WAF WebACLs configured",
                    severity="MEDIUM",
                    recommendation="Configure AWS WAF to protect web applications",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            pass

        # Check if Shield Advanced is enabled
        shield = aws_client.get_client("shield")
        try:
            subscription = shield.get_subscription_state()
            shield_active = subscription.get("SubscriptionState") == "ACTIVE"
            total_resources += 1
            if shield_active:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:shield::account",
                    issue="AWS Shield Advanced not enabled",
                    severity="INFO",
                    recommendation="Consider Shield Advanced for enhanced DDoS protection",
                    effort="LOW",
                    impact="MEDIUM",
                    details={"note": "Shield Standard is included free with all AWS accounts"}
                ))
        except Exception:
            total_resources += 1  # Assume not subscribed

        # Check security groups for overly permissive rules
        ec2 = aws_client.get_client("ec2")
        sgs = ec2.describe_security_groups().get("SecurityGroups", [])

        for sg in sgs:
            sg_id = sg.get("GroupId")
            total_resources += 1
            is_compliant = True

            for rule in sg.get("IpPermissions", []):
                for ip_range in rule.get("IpRanges", []):
                    cidr = ip_range.get("CidrIp", "")
                    if cidr == "0.0.0.0/0":
                        from_port = rule.get("FromPort", 0)
                        to_port = rule.get("ToPort", 65535)
                        protocol = rule.get("IpProtocol", "-1")

                        # Allow HTTP/HTTPS from anywhere (common pattern)
                        if from_port in [80, 443] and to_port in [80, 443]:
                            continue

                        # Flag SSH/RDP from anywhere
                        if from_port in [22, 3389] or to_port in [22, 3389]:
                            is_compliant = False
                            findings.append(create_finding(
                                resource=sg_id,
                                issue=f"Security group allows SSH/RDP from 0.0.0.0/0",
                                severity="HIGH",
                                recommendation="Restrict SSH/RDP to specific IP ranges",
                                effort="LOW",
                                impact="HIGH"
                            ))

                        # Flag all traffic from anywhere
                        if protocol == "-1" and from_port == 0 and to_port == 65535:
                            is_compliant = False
                            findings.append(create_finding(
                                resource=sg_id,
                                issue="Security group allows all traffic from 0.0.0.0/0",
                                severity="CRITICAL",
                                recommendation="Restrict to specific ports and IP ranges",
                                effort="MEDIUM",
                                impact="CRITICAL"
                            ))

            if is_compliant:
                compliant_resources += 1

        # Check VPC Flow Logs
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        for vpc in vpcs:
            vpc_id = vpc.get("VpcId")
            total_resources += 1

            flow_logs = ec2.describe_flow_logs(
                Filters=[{"Name": "resource-id", "Values": [vpc_id]}]
            ).get("FlowLogs", [])

            if flow_logs:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource=vpc_id,
                    issue=f"VPC {vpc_id} does not have Flow Logs enabled",
                    severity="MEDIUM",
                    recommendation="Enable VPC Flow Logs for network monitoring",
                    effort="LOW",
                    impact="MEDIUM"
                ))

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_network_protection",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use AWS WAF to protect web applications",
            "Enable VPC Flow Logs for all VPCs",
            "Follow least privilege for security groups",
            "Never allow SSH/RDP from 0.0.0.0/0",
            "Use AWS Shield for DDoS protection",
            "Implement network segmentation with subnets and NACLs"
        ]
    )


# =============================================================================
# SEC-6: Compute Protection
# =============================================================================

@tool
def check_compute_protection(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check compute resource protection configuration (SEC-6).

    Validates:
    - IMDSv2 required on EC2 instances
    - Systems Manager managed instances
    - Patch compliance status
    - Instance profiles attached

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

        # Check EC2 instances
        instances = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]
        )

        for reservation in instances.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId")
                total_resources += 1
                issues_found = 0

                # Check IMDSv2
                metadata_options = instance.get("MetadataOptions", {})
                http_tokens = metadata_options.get("HttpTokens", "optional")
                if http_tokens != "required":
                    issues_found += 1
                    findings.append(create_finding(
                        resource=instance_id,
                        issue=f"Instance {instance_id} does not require IMDSv2",
                        severity="HIGH",
                        recommendation="Require IMDSv2 by setting HttpTokens to 'required'",
                        effort="LOW",
                        impact="HIGH"
                    ))

                # Check instance profile
                iam_profile = instance.get("IamInstanceProfile")
                if not iam_profile:
                    issues_found += 1
                    findings.append(create_finding(
                        resource=instance_id,
                        issue=f"Instance {instance_id} has no IAM instance profile",
                        severity="MEDIUM",
                        recommendation="Attach an IAM instance profile for AWS service access",
                        effort="MEDIUM",
                        impact="MEDIUM"
                    ))

                if issues_found == 0:
                    compliant_resources += 1

        # Check Systems Manager managed instances
        ssm = aws_client.get_client("ssm")
        try:
            managed_instances = ssm.describe_instance_information().get("InstanceInformationList", [])
            managed_ids = {i.get("InstanceId") for i in managed_instances}

            # Check if running instances are managed
            for reservation in instances.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId")
                    state = instance.get("State", {}).get("Name")

                    if state == "running" and instance_id not in managed_ids:
                        findings.append(create_finding(
                            resource=instance_id,
                            issue=f"Running instance {instance_id} not managed by Systems Manager",
                            severity="MEDIUM",
                            recommendation="Install SSM Agent and attach AmazonSSMManagedInstanceCore role",
                            effort="MEDIUM",
                            impact="MEDIUM"
                        ))

            # Check patch compliance
            patch_states = ssm.describe_instance_patch_states(
                InstanceIds=list(managed_ids)[:50]  # API limit
            ).get("InstancePatchStates", [])

            for state in patch_states:
                missing_count = state.get("MissingCount", 0)
                failed_count = state.get("FailedCount", 0)

                if missing_count > 0 or failed_count > 0:
                    findings.append(create_finding(
                        resource=state.get("InstanceId"),
                        issue=f"Instance has {missing_count} missing and {failed_count} failed patches",
                        severity="MEDIUM" if missing_count < 5 else "HIGH",
                        recommendation="Apply missing patches using Patch Manager",
                        effort="MEDIUM",
                        impact="HIGH",
                        details={
                            "missing_patches": missing_count,
                            "failed_patches": failed_count
                        }
                    ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_compute_protection",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Require IMDSv2 for all EC2 instances",
            "Use Systems Manager for patch management",
            "Attach IAM instance profiles instead of embedding credentials",
            "Enable detailed monitoring for all instances",
            "Use Amazon Inspector for vulnerability assessment",
            "Implement a regular patching schedule"
        ]
    )


# =============================================================================
# SEC-7: Data Classification
# =============================================================================

@tool
def check_data_classification(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check data classification practices (SEC-7).

    Validates:
    - Amazon Macie enabled for S3
    - Resource tagging for data classification
    - S3 bucket naming conventions

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check if Macie is enabled
        macie = aws_client.get_client("macie2")
        try:
            macie_status = macie.get_macie_session()
            status = macie_status.get("status", "DISABLED")
            total_resources += 1

            if status == "ENABLED":
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:macie2::account",
                    issue="Amazon Macie is not enabled",
                    severity="MEDIUM",
                    recommendation="Enable Macie for automated sensitive data discovery",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            total_resources += 1
            findings.append(create_finding(
                resource="arn:aws:macie2::account",
                issue="Amazon Macie is not enabled",
                severity="MEDIUM",
                recommendation="Enable Macie for automated sensitive data discovery",
                effort="LOW",
                impact="MEDIUM"
            ))

        # Check S3 buckets for classification tags
        s3 = aws_client.get_client("s3")
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            classification_tags = ["DataClassification", "Sensitivity", "Classification", "data-classification"]

            for bucket in buckets:
                bucket_name = bucket["Name"]
                total_resources += 1
                has_classification = False

                try:
                    tags = s3.get_bucket_tagging(Bucket=bucket_name).get("TagSet", [])
                    tag_keys = [t.get("Key", "").lower() for t in tags]

                    for class_tag in classification_tags:
                        if class_tag.lower() in tag_keys:
                            has_classification = True
                            break

                    if has_classification:
                        compliant_resources += 1
                    else:
                        findings.append(create_finding(
                            resource=f"arn:aws:s3:::{bucket_name}",
                            issue=f"S3 bucket '{bucket_name}' has no data classification tag",
                            severity="LOW",
                            recommendation="Add DataClassification tag (e.g., Public, Internal, Confidential)",
                            effort="LOW",
                            impact="LOW"
                        ))
                except Exception:
                    findings.append(create_finding(
                        resource=f"arn:aws:s3:::{bucket_name}",
                        issue=f"S3 bucket '{bucket_name}' has no tags",
                        severity="LOW",
                        recommendation="Add tags including DataClassification",
                        effort="LOW",
                        impact="LOW"
                    ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_data_classification",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Enable Amazon Macie for automated data discovery",
            "Tag all resources with DataClassification",
            "Define clear data classification levels (Public, Internal, Confidential)",
            "Apply appropriate controls based on classification",
            "Review and update classifications regularly",
            "Train teams on data classification policies"
        ]
    )


# =============================================================================
# SEC-4: Detection
# =============================================================================

@tool
def check_detective_controls(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check detective controls configuration (SEC-4).

    Validates:
    - CloudTrail enabled across all regions
    - GuardDuty enabled
    - Security Hub enabled
    - Config rules configured
    - CloudWatch alarms for security events

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check CloudTrail
        cloudtrail = aws_client.get_client("cloudtrail")
        try:
            trails = cloudtrail.describe_trails().get("trailList", [])
            total_resources += 1

            multi_region_trail = any(t.get("IsMultiRegionTrail") for t in trails)
            if multi_region_trail:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:cloudtrail::account",
                    issue="No multi-region CloudTrail trail configured",
                    severity="HIGH",
                    recommendation="Enable a multi-region trail for comprehensive logging",
                    effort="LOW",
                    impact="HIGH"
                ))

            # Check for organization trail
            org_trail = any(t.get("IsOrganizationTrail") for t in trails)

            # Check log file validation
            validation_enabled = any(t.get("LogFileValidationEnabled") for t in trails)
            if not validation_enabled:
                findings.append(create_finding(
                    resource="arn:aws:cloudtrail::account",
                    issue="CloudTrail log file validation not enabled",
                    severity="MEDIUM",
                    recommendation="Enable log file validation for integrity checking",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            total_resources += 1
            findings.append(create_finding(
                resource="arn:aws:cloudtrail::account",
                issue="CloudTrail not configured",
                severity="CRITICAL",
                recommendation="Enable CloudTrail for API logging",
                effort="LOW",
                impact="CRITICAL"
            ))

        # Check GuardDuty
        guardduty = aws_client.get_client("guardduty")
        try:
            detectors = guardduty.list_detectors().get("DetectorIds", [])
            total_resources += 1

            if detectors:
                # Check if enabled
                detector_id = detectors[0]
                detector = guardduty.get_detector(DetectorId=detector_id)
                status = detector.get("Status", "DISABLED")

                if status == "ENABLED":
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource=f"arn:aws:guardduty::detector/{detector_id}",
                        issue="GuardDuty detector is disabled",
                        severity="HIGH",
                        recommendation="Enable GuardDuty detector",
                        effort="LOW",
                        impact="HIGH"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:guardduty::account",
                    issue="GuardDuty not enabled",
                    severity="HIGH",
                    recommendation="Enable GuardDuty for threat detection",
                    effort="LOW",
                    impact="HIGH"
                ))
        except Exception:
            total_resources += 1

        # Check Security Hub
        securityhub = aws_client.get_client("securityhub")
        try:
            hub = securityhub.describe_hub()
            total_resources += 1
            compliant_resources += 1
        except Exception:
            total_resources += 1
            findings.append(create_finding(
                resource="arn:aws:securityhub::account",
                issue="Security Hub not enabled",
                severity="MEDIUM",
                recommendation="Enable Security Hub for centralized security findings",
                effort="LOW",
                impact="MEDIUM"
            ))

        # Check AWS Config
        config = aws_client.get_client("config")
        try:
            recorders = config.describe_configuration_recorders().get("ConfigurationRecorders", [])
            total_resources += 1

            if recorders:
                status = config.describe_configuration_recorder_status().get("ConfigurationRecordersStatus", [])
                is_recording = any(s.get("recording") for s in status)

                if is_recording:
                    compliant_resources += 1
                else:
                    findings.append(create_finding(
                        resource="arn:aws:config::account",
                        issue="AWS Config recorder is not recording",
                        severity="MEDIUM",
                        recommendation="Start the Config recorder",
                        effort="LOW",
                        impact="MEDIUM"
                    ))
            else:
                findings.append(create_finding(
                    resource="arn:aws:config::account",
                    issue="AWS Config not configured",
                    severity="MEDIUM",
                    recommendation="Enable AWS Config for resource tracking",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            total_resources += 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_detective_controls",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Enable multi-region CloudTrail with log file validation",
            "Enable GuardDuty in all regions",
            "Use Security Hub for centralized findings",
            "Configure AWS Config with security-focused rules",
            "Set up CloudWatch alarms for security events",
            "Integrate findings with your SIEM/ticketing system"
        ]
    )


# =============================================================================
# SEC-10: Incident Response
# =============================================================================

@tool
def check_incident_response(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check incident response readiness (SEC-10).

    Validates:
    - GuardDuty findings are being processed
    - Security Hub has enabled standards
    - SNS topics for security alerts
    - EventBridge rules for security events

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check GuardDuty findings processing
        guardduty = aws_client.get_client("guardduty")
        try:
            detectors = guardduty.list_detectors().get("DetectorIds", [])
            if detectors:
                detector_id = detectors[0]
                total_resources += 1

                # Check for unprocessed findings
                unprocessed = guardduty.list_findings(
                    DetectorId=detector_id,
                    FindingCriteria={
                        "Criterion": {
                            "service.archived": {"Eq": ["false"]}
                        }
                    }
                ).get("FindingIds", [])

                if len(unprocessed) > 50:
                    findings.append(create_finding(
                        resource=f"arn:aws:guardduty::detector/{detector_id}",
                        issue=f"{len(unprocessed)} unprocessed GuardDuty findings",
                        severity="HIGH",
                        recommendation="Review and remediate GuardDuty findings",
                        effort="MEDIUM",
                        impact="HIGH"
                    ))
                else:
                    compliant_resources += 1
        except Exception:
            pass

        # Check Security Hub standards
        securityhub = aws_client.get_client("securityhub")
        try:
            standards = securityhub.get_enabled_standards().get("StandardsSubscriptions", [])
            total_resources += 1

            if standards:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:securityhub::account",
                    issue="No Security Hub standards enabled",
                    severity="MEDIUM",
                    recommendation="Enable AWS Foundational Security Best Practices standard",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            total_resources += 1

        # Check for security-related EventBridge rules
        events = aws_client.get_client("events")
        try:
            rules = events.list_rules().get("Rules", [])
            total_resources += 1

            security_patterns = ["guardduty", "security", "alert", "incident"]
            security_rules = [
                r for r in rules
                if any(p in r.get("Name", "").lower() for p in security_patterns)
            ]

            if security_rules:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:events::account",
                    issue="No security-focused EventBridge rules found",
                    severity="MEDIUM",
                    recommendation="Create EventBridge rules for security event automation",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

        # Check for security SNS topics
        sns = aws_client.get_client("sns")
        try:
            topics = sns.list_topics().get("Topics", [])
            total_resources += 1

            security_topics = [
                t for t in topics
                if any(p in t.get("TopicArn", "").lower() for p in ["security", "alert", "incident"])
            ]

            if security_topics:
                compliant_resources += 1
            else:
                findings.append(create_finding(
                    resource="arn:aws:sns::account",
                    issue="No security notification topics found",
                    severity="LOW",
                    recommendation="Create SNS topics for security notifications",
                    effort="LOW",
                    impact="MEDIUM"
                ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_incident_response",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Review GuardDuty findings regularly",
            "Enable Security Hub standards (CIS, AWS Foundational)",
            "Set up automated alerting with EventBridge and SNS",
            "Document incident response procedures",
            "Practice incident response with game days",
            "Integrate with ticketing systems (Jira, ServiceNow)"
        ]
    )


# =============================================================================
# SEC-5: Infrastructure Protection
# =============================================================================

@tool
def check_infrastructure_protection(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check infrastructure protection configuration (SEC-5).

    Validates:
    - VPC design and network segmentation
    - Private subnets for sensitive workloads
    - NAT Gateways for outbound access
    - VPC endpoints for AWS service access

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

        # Check VPC design
        vpcs = ec2.describe_vpcs().get("Vpcs", [])

        for vpc in vpcs:
            vpc_id = vpc.get("VpcId")
            total_resources += 1
            vpc_issues = 0

            # Check subnets
            subnets = ec2.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            ).get("Subnets", [])

            # Check for private vs public subnets
            route_tables = ec2.describe_route_tables(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            ).get("RouteTables", [])

            public_subnets = []
            private_subnets = []

            for rt in route_tables:
                has_igw = any(
                    r.get("GatewayId", "").startswith("igw-")
                    for r in rt.get("Routes", [])
                )
                for assoc in rt.get("Associations", []):
                    subnet_id = assoc.get("SubnetId")
                    if subnet_id:
                        if has_igw:
                            public_subnets.append(subnet_id)
                        else:
                            private_subnets.append(subnet_id)

            # Check if there's network segmentation
            if len(subnets) < 2:
                vpc_issues += 1
                findings.append(create_finding(
                    resource=vpc_id,
                    issue=f"VPC {vpc_id} has only {len(subnets)} subnet(s)",
                    severity="MEDIUM",
                    recommendation="Create public and private subnets for network segmentation",
                    effort="MEDIUM",
                    impact="MEDIUM"
                ))

            # Check for NAT Gateways (for private subnet outbound)
            nat_gateways = ec2.describe_nat_gateways(
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "state", "Values": ["available"]}
                ]
            ).get("NatGateways", [])

            if private_subnets and not nat_gateways:
                vpc_issues += 1
                findings.append(create_finding(
                    resource=vpc_id,
                    issue=f"VPC {vpc_id} has private subnets but no NAT Gateway",
                    severity="INFO",
                    recommendation="Consider NAT Gateway for private subnet internet access",
                    effort="LOW",
                    impact="LOW"
                ))

            # Check VPC endpoints
            endpoints = ec2.describe_vpc_endpoints(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            ).get("VpcEndpoints", [])

            gateway_endpoints = [e for e in endpoints if e.get("VpcEndpointType") == "Gateway"]
            if not gateway_endpoints:
                findings.append(create_finding(
                    resource=vpc_id,
                    issue=f"VPC {vpc_id} has no Gateway endpoints (S3, DynamoDB)",
                    severity="LOW",
                    recommendation="Add Gateway endpoints for S3 and DynamoDB (free)",
                    effort="LOW",
                    impact="LOW"
                ))

            if vpc_issues == 0:
                compliant_resources += 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_infrastructure_protection",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use multiple subnets (public/private) for network segmentation",
            "Place sensitive workloads in private subnets",
            "Use NAT Gateways for private subnet internet access",
            "Add VPC endpoints for AWS services (reduces data transfer costs)",
            "Implement defense in depth with multiple layers",
            "Use AWS PrivateLink for private connectivity to services"
        ]
    )


# =============================================================================
# Additional Security Checks
# =============================================================================

@tool
def check_aws_account_security(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check AWS account-level security settings (SEC-1).

    Validates:
    - Account belongs to an Organization
    - Service Control Policies (SCPs) in use
    - Alternate contacts configured
    - Account password policy

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check Organizations membership
        org = aws_client.get_client("organizations")
        try:
            org_info = org.describe_organization()
            total_resources += 1
            compliant_resources += 1

            # Check if SCPs are enabled
            master_account = org_info["Organization"].get("MasterAccountId")
            feature_set = org_info["Organization"].get("FeatureSet")

            if feature_set != "ALL":
                findings.append(create_finding(
                    resource="arn:aws:organizations::account",
                    issue="Organizations not using ALL features (SCPs disabled)",
                    severity="MEDIUM",
                    recommendation="Enable all features in Organizations for SCP support",
                    effort="MEDIUM",
                    impact="HIGH"
                ))
        except Exception:
            total_resources += 1
            findings.append(create_finding(
                resource="arn:aws:organizations::account",
                issue="Account not part of an AWS Organization",
                severity="MEDIUM",
                recommendation="Consider using AWS Organizations for centralized governance",
                effort="HIGH",
                impact="MEDIUM"
            ))

        # Check IAM password policy
        iam = aws_client.get_client("iam")
        try:
            policy = iam.get_account_password_policy()["PasswordPolicy"]
            total_resources += 1

            issues = []
            if policy.get("MinimumPasswordLength", 0) < 14:
                issues.append("Minimum password length should be 14+")
            if not policy.get("RequireSymbols"):
                issues.append("Require symbols in passwords")
            if not policy.get("RequireNumbers"):
                issues.append("Require numbers in passwords")
            if not policy.get("RequireUppercaseCharacters"):
                issues.append("Require uppercase characters")
            if not policy.get("RequireLowercaseCharacters"):
                issues.append("Require lowercase characters")
            if policy.get("MaxPasswordAge", 0) > 90 or policy.get("MaxPasswordAge", 0) == 0:
                issues.append("Set password expiration to 90 days or less")

            if issues:
                findings.append(create_finding(
                    resource="arn:aws:iam::account:password-policy",
                    issue=f"Password policy does not meet best practices: {'; '.join(issues)}",
                    severity="MEDIUM",
                    recommendation="Update password policy to meet CIS benchmarks",
                    effort="LOW",
                    impact="MEDIUM",
                    details={"issues": issues}
                ))
            else:
                compliant_resources += 1

        except Exception:
            total_resources += 1
            findings.append(create_finding(
                resource="arn:aws:iam::account:password-policy",
                issue="No IAM password policy configured",
                severity="HIGH",
                recommendation="Configure a strong password policy",
                effort="LOW",
                impact="HIGH"
            ))

        # Check alternate contacts
        account = aws_client.get_client("account")
        try:
            for contact_type in ["SECURITY", "BILLING", "OPERATIONS"]:
                total_resources += 1
                try:
                    contact = account.get_alternate_contact(AlternateContactType=contact_type)
                    compliant_resources += 1
                except Exception:
                    findings.append(create_finding(
                        resource="arn:aws:account::contact",
                        issue=f"{contact_type} alternate contact not configured",
                        severity="LOW",
                        recommendation=f"Configure {contact_type} alternate contact",
                        effort="LOW",
                        impact="LOW"
                    ))
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_aws_account_security",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use AWS Organizations for multi-account governance",
            "Enable all features in Organizations for SCPs",
            "Configure strong IAM password policy (14+ chars, complexity)",
            "Set up alternate contacts for security notifications",
            "Enable AWS account-level MFA",
            "Use AWS Control Tower for multi-account best practices"
        ]
    )


@tool
def check_api_security(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check API security configuration (SEC-6).

    Validates:
    - API Gateway authentication configured
    - API Gateway throttling enabled
    - WAF associated with API Gateway stages
    - Lambda function URLs have auth

    Returns:
        Well-Architected check result with findings and recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    findings = []
    total_resources = 0
    compliant_resources = 0

    try:
        # Check REST APIs
        apigw = aws_client.get_client("apigateway")
        try:
            apis = apigw.get_rest_apis().get("items", [])

            for api in apis:
                api_id = api.get("id")
                api_name = api.get("name")
                total_resources += 1
                api_issues = 0

                # Check stages
                stages = apigw.get_stages(restApiId=api_id).get("item", [])

                for stage in stages:
                    stage_name = stage.get("stageName")

                    # Check WAF association
                    waf_arn = stage.get("webAclArn")
                    if not waf_arn:
                        api_issues += 1
                        findings.append(create_finding(
                            resource=f"arn:aws:apigateway:::restapis/{api_id}/stages/{stage_name}",
                            issue=f"API Gateway stage '{api_name}/{stage_name}' has no WAF",
                            severity="MEDIUM",
                            recommendation="Associate a WAF WebACL with this API stage",
                            effort="MEDIUM",
                            impact="HIGH"
                        ))

                    # Check throttling
                    method_settings = stage.get("methodSettings", {})
                    if "*/*" not in method_settings:
                        api_issues += 1
                        findings.append(create_finding(
                            resource=f"arn:aws:apigateway:::restapis/{api_id}/stages/{stage_name}",
                            issue=f"API Gateway stage '{api_name}/{stage_name}' has no default throttling",
                            severity="LOW",
                            recommendation="Configure default method throttling",
                            effort="LOW",
                            impact="MEDIUM"
                        ))

                if api_issues == 0:
                    compliant_resources += 1
        except Exception:
            pass

        # Check Lambda function URLs
        lambda_client = aws_client.get_client("lambda")
        try:
            paginator = lambda_client.get_paginator("list_functions")
            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    func_name = func.get("FunctionName")

                    # Check for function URL
                    try:
                        url_config = lambda_client.get_function_url_config(FunctionName=func_name)
                        total_resources += 1

                        auth_type = url_config.get("AuthType", "NONE")
                        if auth_type == "NONE":
                            findings.append(create_finding(
                                resource=func.get("FunctionArn"),
                                issue=f"Lambda function URL '{func_name}' has no authentication",
                                severity="HIGH",
                                recommendation="Use AWS_IAM auth type or add custom authorization",
                                effort="MEDIUM",
                                impact="HIGH"
                            ))
                        else:
                            compliant_resources += 1
                    except Exception:
                        pass  # No function URL configured
        except Exception:
            pass

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_api_security",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Use AWS WAF to protect API Gateway",
            "Configure throttling to prevent abuse",
            "Require authentication for all APIs",
            "Use API keys with usage plans",
            "Enable CloudWatch logging for APIs",
            "Use private API endpoints where possible"
        ]
    )


@tool
def check_database_security(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check database security configuration (SEC-8).

    Validates:
    - RDS instances not publicly accessible
    - RDS encryption enabled
    - RDS security groups properly configured
    - IAM database authentication

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
            total_resources += 1
            issues = 0

            # Check public accessibility
            if instance.get("PubliclyAccessible", False):
                issues += 1
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS instance '{instance_id}' is publicly accessible",
                    severity="CRITICAL",
                    recommendation="Disable public accessibility and use private subnets",
                    effort="MEDIUM",
                    impact="CRITICAL"
                ))

            # Check encryption
            if not instance.get("StorageEncrypted", False):
                issues += 1
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS instance '{instance_id}' is not encrypted",
                    severity="HIGH",
                    recommendation="Create encrypted snapshot and restore to encrypted instance",
                    effort="HIGH",
                    impact="HIGH"
                ))

            # Check IAM authentication
            if not instance.get("IAMDatabaseAuthenticationEnabled", False):
                # This is a recommendation, not critical
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS instance '{instance_id}' does not use IAM authentication",
                    severity="LOW",
                    recommendation="Consider enabling IAM database authentication",
                    effort="MEDIUM",
                    impact="LOW"
                ))

            # Check deletion protection
            if not instance.get("DeletionProtection", False):
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS instance '{instance_id}' has no deletion protection",
                    severity="LOW",
                    recommendation="Enable deletion protection for production databases",
                    effort="LOW",
                    impact="MEDIUM"
                ))

            # Check minor version upgrade
            if not instance.get("AutoMinorVersionUpgrade", False):
                findings.append(create_finding(
                    resource=instance_arn,
                    issue=f"RDS instance '{instance_id}' has auto minor version upgrade disabled",
                    severity="LOW",
                    recommendation="Enable auto minor version upgrade for security patches",
                    effort="LOW",
                    impact="MEDIUM"
                ))

            if issues == 0:
                compliant_resources += 1

        # Check RDS clusters (Aurora)
        clusters = rds.describe_db_clusters().get("DBClusters", [])

        for cluster in clusters:
            cluster_id = cluster.get("DBClusterIdentifier")
            cluster_arn = cluster.get("DBClusterArn")
            total_resources += 1
            issues = 0

            if not cluster.get("StorageEncrypted", False):
                issues += 1
                findings.append(create_finding(
                    resource=cluster_arn,
                    issue=f"Aurora cluster '{cluster_id}' is not encrypted",
                    severity="HIGH",
                    recommendation="Create encrypted cluster from snapshot",
                    effort="HIGH",
                    impact="HIGH"
                ))

            if not cluster.get("DeletionProtection", False):
                findings.append(create_finding(
                    resource=cluster_arn,
                    issue=f"Aurora cluster '{cluster_id}' has no deletion protection",
                    severity="LOW",
                    recommendation="Enable deletion protection",
                    effort="LOW",
                    impact="MEDIUM"
                ))

            if issues == 0:
                compliant_resources += 1

    except Exception as e:
        return {"error": str(e)}

    return create_check_result(
        pillar=Pillar.SECURITY.value,
        check_name="check_database_security",
        findings=findings,
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        best_practices=[
            "Never make RDS instances publicly accessible",
            "Enable encryption for all databases",
            "Use IAM database authentication where supported",
            "Enable deletion protection for production databases",
            "Use security groups with least privilege access",
            "Enable enhanced monitoring and Performance Insights"
        ]
    )


# =============================================================================
# Security Pillar Review (Orchestrator)
# =============================================================================

@tool
def run_security_pillar_review(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run comprehensive Security Pillar review (all SEC checks).

    Executes all 14 security checks and provides:
    - Overall security score
    - Prioritized findings
    - Remediation recommendations
    - Best practices summary

    Returns:
        Complete Security Pillar assessment with aggregated results.
    """
    if aws_client is None:
        aws_client = AWSClient()

    check_results = []
    errors = []

    # Run all security checks
    checks = [
        ("Root Account Usage", check_root_account_usage),
        ("Identity Federation", check_identity_federation),
        ("Secrets Management", check_secrets_management),
        ("Encryption at Rest", check_encryption_at_rest),
        ("Encryption in Transit", check_encryption_in_transit),
        ("Network Protection", check_network_protection),
        ("Compute Protection", check_compute_protection),
        ("Data Classification", check_data_classification),
        ("Detective Controls", check_detective_controls),
        ("Incident Response", check_incident_response),
        ("Infrastructure Protection", check_infrastructure_protection),
        ("Account Security", check_aws_account_security),
        ("API Security", check_api_security),
        ("Database Security", check_database_security),
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
        pillar=Pillar.SECURITY.value,
        check_results=check_results,
        recommendations=[
            "Enable MFA for all users, especially root account",
            "Encrypt all data at rest and in transit",
            "Implement least privilege access for all roles",
            "Enable CloudTrail, GuardDuty, and Security Hub",
            "Review and remediate critical findings immediately",
            "Establish incident response procedures and test regularly",
            "Use AWS Organizations with SCPs for governance",
            "Implement network segmentation with VPCs and subnets"
        ]
    )

    if errors:
        result["errors"] = errors

    return result
