"""
IAM Security & Compliance Tools for StrandKit.

This module provides comprehensive IAM security auditing and compliance checking:
- User access analysis (inactive users, MFA compliance, access keys)
- Password policy compliance checking
- Cross-account access analysis
- Privilege escalation detection
- Unused permissions analysis
- Credential report analysis

All tools follow consistent patterns:
- Accept simple, well-typed parameters
- Return structured JSON with consistent keys
- Include clear security recommendations
- Provide risk assessments
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import time
import csv
import io

from strandkit.core.aws_client import AWSClient


def analyze_iam_users(
    inactive_days: int = 90,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze IAM users for security issues and inactive accounts.

    Checks for:
    - Inactive users (no console login or access key usage)
    - Users without MFA
    - Users with console access but no MFA
    - Old access keys (>90 days)
    - Users who have never logged in
    - Programmatic vs console access patterns

    Args:
        inactive_days: Days of inactivity to flag users (default: 90)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total users, inactive count, MFA compliance, etc.
        - inactive_users: List of inactive users with details
        - users_without_mfa: Users lacking MFA (console access)
        - never_logged_in: Users who have never used console
        - old_access_keys: Users with access keys >90 days old
        - recommendations: Security improvement suggestions

    Example:
        >>> result = analyze_iam_users(inactive_days=90)
        >>> print(f"Inactive users: {result['summary']['inactive_users']}")
        >>> print(f"Users without MFA: {result['summary']['users_without_mfa']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')

        # Get all users
        users_response = iam.list_users()
        all_users = users_response.get('Users', [])

        # Handle pagination
        while users_response.get('IsTruncated', False):
            users_response = iam.list_users(Marker=users_response['Marker'])
            all_users.extend(users_response.get('Users', []))

        inactive_users = []
        users_without_mfa = []
        never_logged_in = []
        old_access_keys = []
        console_users_without_mfa = []

        now = datetime.now(timezone.utc)
        inactive_threshold = now - timedelta(days=inactive_days)

        for user in all_users:
            username = user['UserName']
            create_date = user['CreateDate']

            # Get login profile (console access)
            has_console_access = False
            password_last_used = None
            try:
                iam.get_login_profile(UserName=username)
                has_console_access = True
                password_last_used = user.get('PasswordLastUsed')
            except iam.exceptions.NoSuchEntityException:
                pass

            # Get MFA devices
            mfa_devices = iam.list_mfa_devices(UserName=username)
            has_mfa = len(mfa_devices.get('MFADevices', [])) > 0

            # Get access keys
            access_keys_response = iam.list_access_keys(UserName=username)
            access_keys = access_keys_response.get('AccessKeyMetadata', [])

            # Check for old access keys
            old_keys = []
            for key in access_keys:
                if key['Status'] == 'Active':
                    key_age = (now - key['CreateDate']).days
                    if key_age > 90:
                        old_keys.append({
                            'access_key_id': key['AccessKeyId'],
                            'age_days': key_age,
                            'created': key['CreateDate'].isoformat()
                        })

            if old_keys:
                old_access_keys.append({
                    'username': username,
                    'old_keys': old_keys,
                    'oldest_key_days': max(k['age_days'] for k in old_keys)
                })

            # Get last activity (console or programmatic)
            last_activity = None
            activity_type = None

            if password_last_used:
                last_activity = password_last_used
                activity_type = 'console'

            # Check access key last used
            for key in access_keys:
                if key['Status'] == 'Active':
                    try:
                        key_last_used = iam.get_access_key_last_used(
                            AccessKeyId=key['AccessKeyId']
                        )
                        last_used_date = key_last_used.get('AccessKeyLastUsed', {}).get('LastUsedDate')
                        if last_used_date:
                            if not last_activity or last_used_date > last_activity:
                                last_activity = last_used_date
                                activity_type = 'programmatic'
                    except Exception:
                        pass

            # Determine if user is inactive
            is_inactive = False
            days_inactive = None

            if last_activity:
                days_inactive = (now - last_activity).days
                if last_activity < inactive_threshold:
                    is_inactive = True
            else:
                # User has never logged in or used access keys
                days_since_creation = (now - create_date).days
                if days_since_creation > inactive_days:
                    is_inactive = True
                    days_inactive = days_since_creation

            # Track inactive users
            if is_inactive:
                inactive_users.append({
                    'username': username,
                    'created': create_date.isoformat(),
                    'last_activity': last_activity.isoformat() if last_activity else None,
                    'days_inactive': days_inactive,
                    'activity_type': activity_type,
                    'has_console_access': has_console_access,
                    'has_mfa': has_mfa,
                    'access_keys_count': len(access_keys)
                })

            # Track users without MFA
            if not has_mfa:
                users_without_mfa.append({
                    'username': username,
                    'has_console_access': has_console_access,
                    'access_keys_count': len(access_keys),
                    'last_activity': last_activity.isoformat() if last_activity else None
                })

                if has_console_access:
                    console_users_without_mfa.append(username)

            # Track users who never logged in
            if not password_last_used and has_console_access:
                never_logged_in.append({
                    'username': username,
                    'created': create_date.isoformat(),
                    'days_since_creation': (now - create_date).days,
                    'has_mfa': has_mfa
                })

        # Calculate summary statistics
        total_users = len(all_users)
        users_with_mfa = total_users - len(users_without_mfa)
        mfa_compliance_rate = (users_with_mfa / total_users * 100) if total_users > 0 else 0

        console_users = sum(1 for u in all_users if has_console_access)
        console_mfa_rate = ((console_users - len(console_users_without_mfa)) / console_users * 100) if console_users > 0 else 0

        # Generate recommendations
        recommendations = []

        if inactive_users:
            recommendations.append(
                f"Remove or disable {len(inactive_users)} inactive users (>{inactive_days} days)"
            )

        if console_users_without_mfa:
            recommendations.append(
                f"Enforce MFA for {len(console_users_without_mfa)} console users without MFA"
            )

        if old_access_keys:
            recommendations.append(
                f"Rotate {len(old_access_keys)} user access keys older than 90 days"
            )

        if never_logged_in:
            recommendations.append(
                f"Review {len(never_logged_in)} users who have never logged in"
            )

        if mfa_compliance_rate < 100:
            recommendations.append(
                f"Improve MFA compliance from {mfa_compliance_rate:.1f}% to 100%"
            )

        if not recommendations:
            recommendations.append("✅ All users are active with proper MFA configuration")

        return {
            'summary': {
                'total_users': total_users,
                'inactive_users': len(inactive_users),
                'users_without_mfa': len(users_without_mfa),
                'console_users_without_mfa': len(console_users_without_mfa),
                'never_logged_in': len(never_logged_in),
                'old_access_keys': len(old_access_keys),
                'mfa_compliance_rate': round(mfa_compliance_rate, 1),
                'console_mfa_rate': round(console_mfa_rate, 1),
                'inactive_threshold_days': inactive_days
            },
            'inactive_users': inactive_users,
            'users_without_mfa': users_without_mfa,
            'console_users_without_mfa': console_users_without_mfa,
            'never_logged_in': never_logged_in,
            'old_access_keys': old_access_keys,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


def analyze_access_keys(
    max_age_days: int = 90,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze IAM access keys for security risks.

    Checks for:
    - Access keys older than threshold (default 90 days)
    - Unused access keys (never used)
    - Root account access keys (critical security risk!)
    - Multiple access keys per user
    - Inactive access keys that should be deleted

    Args:
        max_age_days: Maximum acceptable key age (default: 90 days)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total keys, old keys, unused keys, root keys
        - old_access_keys: Keys older than threshold
        - unused_access_keys: Keys never used
        - root_access_keys: Root account keys (CRITICAL!)
        - users_with_multiple_keys: Users with 2+ keys
        - recommendations: Security improvement suggestions

    Example:
        >>> result = analyze_access_keys(max_age_days=90)
        >>> if result['summary']['root_access_keys'] > 0:
        ...     print("CRITICAL: Root account has access keys!")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')

        # Check for root account access keys
        root_keys = []
        try:
            account_summary = iam.get_account_summary()
            root_key_count = account_summary.get('SummaryMap', {}).get('AccountAccessKeysPresent', 0)
            if root_key_count > 0:
                root_keys.append({
                    'risk_level': 'critical',
                    'message': f'Root account has {root_key_count} access key(s)',
                    'recommendation': 'Delete root access keys immediately and use IAM users/roles'
                })
        except Exception as e:
            pass

        # Get all users
        users_response = iam.list_users()
        all_users = users_response.get('Users', [])

        while users_response.get('IsTruncated', False):
            users_response = iam.list_users(Marker=users_response['Marker'])
            all_users.extend(users_response.get('Users', []))

        old_access_keys = []
        unused_access_keys = []
        users_with_multiple_keys = []
        all_keys = []

        now = datetime.now(timezone.utc)
        age_threshold = now - timedelta(days=max_age_days)

        for user in all_users:
            username = user['UserName']

            # Get access keys for user
            access_keys_response = iam.list_access_keys(UserName=username)
            access_keys = access_keys_response.get('AccessKeyMetadata', [])

            if len(access_keys) > 1:
                users_with_multiple_keys.append({
                    'username': username,
                    'key_count': len(access_keys),
                    'keys': [k['AccessKeyId'] for k in access_keys]
                })

            for key in access_keys:
                key_id = key['AccessKeyId']
                key_status = key['Status']
                key_create_date = key['CreateDate']
                key_age_days = (now - key_create_date).days

                # Get last used information
                last_used_info = None
                last_used_date = None
                last_used_service = None
                last_used_region = None

                try:
                    last_used_response = iam.get_access_key_last_used(AccessKeyId=key_id)
                    last_used_data = last_used_response.get('AccessKeyLastUsed', {})
                    last_used_date = last_used_data.get('LastUsedDate')
                    last_used_service = last_used_data.get('ServiceName')
                    last_used_region = last_used_data.get('Region')
                except Exception:
                    pass

                key_info = {
                    'username': username,
                    'access_key_id': key_id,
                    'status': key_status,
                    'created': key_create_date.isoformat(),
                    'age_days': key_age_days,
                    'last_used_date': last_used_date.isoformat() if last_used_date else None,
                    'last_used_service': last_used_service,
                    'last_used_region': last_used_region
                }

                all_keys.append(key_info)

                # Check if key is old
                if key_status == 'Active' and key_create_date < age_threshold:
                    old_access_keys.append({
                        **key_info,
                        'risk_level': 'high' if key_age_days > 180 else 'medium',
                        'recommendation': f'Rotate key (age: {key_age_days} days)'
                    })

                # Check if key is unused
                if key_status == 'Active' and not last_used_date:
                    days_since_creation = (now - key_create_date).days
                    if days_since_creation > 30:  # Give new keys 30 days grace period
                        unused_access_keys.append({
                            **key_info,
                            'days_since_creation': days_since_creation,
                            'recommendation': 'Delete unused key or verify it is still needed'
                        })

        # Generate recommendations
        recommendations = []

        if root_keys:
            recommendations.append(
                "🚨 CRITICAL: Delete root account access keys immediately!"
            )

        if old_access_keys:
            recommendations.append(
                f"Rotate {len(old_access_keys)} access keys older than {max_age_days} days"
            )

        if unused_access_keys:
            recommendations.append(
                f"Delete or verify {len(unused_access_keys)} unused access keys"
            )

        if users_with_multiple_keys:
            recommendations.append(
                f"Review {len(users_with_multiple_keys)} users with multiple access keys"
            )

        recommendations.append(
            "Implement automated key rotation policy (rotate every 90 days)"
        )

        if not old_access_keys and not unused_access_keys and not root_keys:
            recommendations.append(
                "✅ All access keys are properly managed and rotated"
            )

        return {
            'summary': {
                'total_access_keys': len(all_keys),
                'active_keys': sum(1 for k in all_keys if k['status'] == 'Active'),
                'inactive_keys': sum(1 for k in all_keys if k['status'] == 'Inactive'),
                'old_access_keys': len(old_access_keys),
                'unused_access_keys': len(unused_access_keys),
                'root_access_keys': len(root_keys),
                'users_with_multiple_keys': len(users_with_multiple_keys),
                'max_age_days': max_age_days
            },
            'old_access_keys': old_access_keys,
            'unused_access_keys': unused_access_keys,
            'root_access_keys': root_keys,
            'users_with_multiple_keys': users_with_multiple_keys,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


def analyze_mfa_compliance(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze MFA (Multi-Factor Authentication) compliance across all IAM users.

    Checks for:
    - Users with console access but no MFA
    - Root account MFA status
    - Virtual vs hardware MFA device breakdown
    - Privileged users without MFA
    - Overall MFA compliance rate

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: MFA compliance statistics
        - users_without_mfa: Console users lacking MFA
        - root_mfa_status: Root account MFA configuration
        - mfa_device_types: Breakdown by device type
        - privileged_users_without_mfa: Admin users without MFA
        - recommendations: MFA enforcement suggestions

    Example:
        >>> result = analyze_mfa_compliance()
        >>> compliance = result['summary']['console_mfa_compliance_rate']
        >>> print(f"MFA compliance: {compliance}%")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')

        # Check root account MFA
        root_mfa_enabled = False
        try:
            account_summary = iam.get_account_summary()
            root_mfa_enabled = account_summary.get('SummaryMap', {}).get('AccountMFAEnabled', 0) == 1
        except Exception:
            pass

        # Get all users
        users_response = iam.list_users()
        all_users = users_response.get('Users', [])

        while users_response.get('IsTruncated', False):
            users_response = iam.list_users(Marker=users_response['Marker'])
            all_users.extend(users_response.get('Users', []))

        console_users = []
        users_with_mfa = []
        users_without_mfa = []
        privileged_users_without_mfa = []
        mfa_device_types = {
            'virtual': 0,
            'hardware': 0
        }

        for user in all_users:
            username = user['UserName']

            # Check if user has console access
            has_console_access = False
            try:
                iam.get_login_profile(UserName=username)
                has_console_access = True
            except iam.exceptions.NoSuchEntityException:
                pass

            if not has_console_access:
                continue

            console_users.append(username)

            # Get MFA devices
            mfa_devices_response = iam.list_mfa_devices(UserName=username)
            mfa_devices = mfa_devices_response.get('MFADevices', [])
            has_mfa = len(mfa_devices) > 0

            # Classify MFA device type
            device_type = None
            if mfa_devices:
                # Virtual MFA devices have ARN containing "mfa/"
                # Hardware devices have serial numbers
                for device in mfa_devices:
                    serial = device.get('SerialNumber', '')
                    if 'mfa/' in serial:
                        device_type = 'virtual'
                        mfa_device_types['virtual'] += 1
                    else:
                        device_type = 'hardware'
                        mfa_device_types['hardware'] += 1
                    break  # Only count first device

            # Check if user is privileged (has admin-like policies)
            is_privileged = False
            try:
                # Check attached policies
                attached_policies = iam.list_attached_user_policies(UserName=username)
                for policy in attached_policies.get('AttachedPolicies', []):
                    policy_name = policy.get('PolicyName', '').lower()
                    if 'admin' in policy_name or 'poweruser' in policy_name:
                        is_privileged = True
                        break

                # Check group memberships
                if not is_privileged:
                    groups_response = iam.list_groups_for_user(UserName=username)
                    for group in groups_response.get('Groups', []):
                        group_name = group.get('GroupName', '').lower()
                        if 'admin' in group_name or 'poweruser' in group_name:
                            is_privileged = True
                            break
            except Exception:
                pass

            user_info = {
                'username': username,
                'has_console_access': has_console_access,
                'has_mfa': has_mfa,
                'mfa_device_type': device_type,
                'is_privileged': is_privileged,
                'mfa_device_count': len(mfa_devices)
            }

            if has_mfa:
                users_with_mfa.append(user_info)
            else:
                users_without_mfa.append(user_info)
                if is_privileged:
                    privileged_users_without_mfa.append(user_info)

        # Calculate compliance rates
        total_console_users = len(console_users)
        users_with_mfa_count = len(users_with_mfa)
        console_mfa_compliance = (users_with_mfa_count / total_console_users * 100) if total_console_users > 0 else 0

        # Generate recommendations
        recommendations = []

        if not root_mfa_enabled:
            recommendations.append(
                "🚨 CRITICAL: Enable MFA on root account immediately!"
            )

        if privileged_users_without_mfa:
            recommendations.append(
                f"🚨 HIGH PRIORITY: Enable MFA for {len(privileged_users_without_mfa)} privileged users"
            )

        if users_without_mfa:
            recommendations.append(
                f"Enforce MFA for {len(users_without_mfa)} console users without MFA"
            )

        if console_mfa_compliance < 100:
            recommendations.append(
                f"Improve MFA compliance from {console_mfa_compliance:.1f}% to 100%"
            )

        recommendations.append(
            "Consider implementing MFA enforcement via IAM policy conditions"
        )

        if console_mfa_compliance == 100 and root_mfa_enabled:
            recommendations.append(
                "✅ Perfect MFA compliance across all users and root account!"
            )

        return {
            'summary': {
                'total_users': len(all_users),
                'console_users': total_console_users,
                'users_with_mfa': users_with_mfa_count,
                'users_without_mfa': len(users_without_mfa),
                'console_mfa_compliance_rate': round(console_mfa_compliance, 1),
                'root_mfa_enabled': root_mfa_enabled,
                'privileged_users_without_mfa': len(privileged_users_without_mfa)
            },
            'root_mfa_status': {
                'enabled': root_mfa_enabled,
                'risk_level': 'critical' if not root_mfa_enabled else 'low'
            },
            'users_without_mfa': users_without_mfa,
            'privileged_users_without_mfa': privileged_users_without_mfa,
            'mfa_device_types': mfa_device_types,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


def analyze_password_policy(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze IAM password policy against security best practices.

    Checks current password policy against:
    - CIS AWS Foundations Benchmark
    - AWS Security Best Practices
    - Industry standards (minimum length, complexity, expiration)

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - current_policy: Current password policy settings
        - cis_benchmark_compliance: Compliance with CIS standards
        - security_score: Overall security score (0-100)
        - violations: List of policy violations
        - recommendations: Policy improvement suggestions

    Example:
        >>> result = analyze_password_policy()
        >>> score = result['security_score']
        >>> print(f"Password policy security score: {score}/100")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')

        # Get account password policy
        policy_exists = True
        current_policy = {}
        try:
            policy_response = iam.get_account_password_policy()
            current_policy = policy_response.get('PasswordPolicy', {})
        except iam.exceptions.NoSuchEntityException:
            policy_exists = False

        # CIS AWS Foundations Benchmark requirements
        cis_requirements = {
            'minimum_password_length': {'required': 14, 'current': current_policy.get('MinimumPasswordLength', 0)},
            'require_symbols': {'required': True, 'current': current_policy.get('RequireSymbols', False)},
            'require_numbers': {'required': True, 'current': current_policy.get('RequireNumbers', False)},
            'require_uppercase': {'required': True, 'current': current_policy.get('RequireUppercaseCharacters', False)},
            'require_lowercase': {'required': True, 'current': current_policy.get('RequireLowercaseCharacters', False)},
            'allow_users_to_change': {'required': True, 'current': current_policy.get('AllowUsersToChangePassword', False)},
            'expire_passwords': {'required': True, 'current': current_policy.get('ExpirePasswords', False)},
            'max_password_age': {'required': 90, 'current': current_policy.get('MaxPasswordAge', 0)},
            'password_reuse_prevention': {'required': 24, 'current': current_policy.get('PasswordReusePrevention', 0)},
        }

        # Check compliance
        violations = []
        compliant_count = 0
        total_checks = len(cis_requirements)

        if not policy_exists:
            violations.append({
                'check': 'password_policy_exists',
                'severity': 'critical',
                'message': 'No password policy configured!',
                'recommendation': 'Create a password policy meeting CIS Benchmark standards'
            })
        else:
            # Check each requirement
            if current_policy.get('MinimumPasswordLength', 0) < cis_requirements['minimum_password_length']['required']:
                violations.append({
                    'check': 'minimum_password_length',
                    'severity': 'high',
                    'current': current_policy.get('MinimumPasswordLength', 0),
                    'required': cis_requirements['minimum_password_length']['required'],
                    'message': f"Password length {current_policy.get('MinimumPasswordLength', 0)} is less than required 14",
                    'recommendation': 'Set MinimumPasswordLength to at least 14 characters'
                })
            else:
                compliant_count += 1

            if not current_policy.get('RequireSymbols', False):
                violations.append({
                    'check': 'require_symbols',
                    'severity': 'medium',
                    'message': 'Password policy does not require symbols',
                    'recommendation': 'Enable RequireSymbols'
                })
            else:
                compliant_count += 1

            if not current_policy.get('RequireNumbers', False):
                violations.append({
                    'check': 'require_numbers',
                    'severity': 'medium',
                    'message': 'Password policy does not require numbers',
                    'recommendation': 'Enable RequireNumbers'
                })
            else:
                compliant_count += 1

            if not current_policy.get('RequireUppercaseCharacters', False):
                violations.append({
                    'check': 'require_uppercase',
                    'severity': 'medium',
                    'message': 'Password policy does not require uppercase characters',
                    'recommendation': 'Enable RequireUppercaseCharacters'
                })
            else:
                compliant_count += 1

            if not current_policy.get('RequireLowercaseCharacters', False):
                violations.append({
                    'check': 'require_lowercase',
                    'severity': 'medium',
                    'message': 'Password policy does not require lowercase characters',
                    'recommendation': 'Enable RequireLowercaseCharacters'
                })
            else:
                compliant_count += 1

            if not current_policy.get('AllowUsersToChangePassword', False):
                violations.append({
                    'check': 'allow_users_to_change',
                    'severity': 'medium',
                    'message': 'Users cannot change their own passwords',
                    'recommendation': 'Enable AllowUsersToChangePassword'
                })
            else:
                compliant_count += 1

            if not current_policy.get('ExpirePasswords', False):
                violations.append({
                    'check': 'expire_passwords',
                    'severity': 'high',
                    'message': 'Passwords do not expire',
                    'recommendation': 'Enable ExpirePasswords with MaxPasswordAge of 90 days'
                })
            else:
                compliant_count += 1

                # Check max password age
                max_age = current_policy.get('MaxPasswordAge', 0)
                if max_age > 90:
                    violations.append({
                        'check': 'max_password_age',
                        'severity': 'medium',
                        'current': max_age,
                        'required': 90,
                        'message': f'Password expiration {max_age} days exceeds recommended 90 days',
                        'recommendation': 'Set MaxPasswordAge to 90 days or less'
                    })

            if current_policy.get('PasswordReusePrevention', 0) < 24:
                violations.append({
                    'check': 'password_reuse_prevention',
                    'severity': 'medium',
                    'current': current_policy.get('PasswordReusePrevention', 0),
                    'required': 24,
                    'message': f'Password reuse prevention {current_policy.get("PasswordReusePrevention", 0)} is less than required 24',
                    'recommendation': 'Set PasswordReusePrevention to 24'
                })
            else:
                compliant_count += 1

        # Calculate security score
        security_score = (compliant_count / total_checks * 100) if policy_exists else 0

        # Generate recommendations
        recommendations = []

        if not policy_exists:
            recommendations.append(
                "🚨 CRITICAL: Create an IAM password policy immediately"
            )
            recommendations.append(
                "Set minimum password length to 14 characters"
            )
            recommendations.append(
                "Require uppercase, lowercase, numbers, and symbols"
            )
            recommendations.append(
                "Enable password expiration (90 days)"
            )
            recommendations.append(
                "Prevent password reuse (last 24 passwords)"
            )
        else:
            for violation in violations:
                if violation['severity'] == 'critical':
                    recommendations.append(f"🚨 {violation['recommendation']}")
                elif violation['severity'] == 'high':
                    recommendations.append(f"⚠️ {violation['recommendation']}")
                else:
                    recommendations.append(f"• {violation['recommendation']}")

        if security_score == 100:
            recommendations.append(
                "✅ Password policy meets all CIS Benchmark requirements!"
            )

        return {
            'policy_exists': policy_exists,
            'current_policy': current_policy if policy_exists else None,
            'cis_benchmark_compliance': {
                'compliant_checks': compliant_count,
                'total_checks': total_checks,
                'compliance_rate': round(security_score, 1)
            },
            'security_score': round(security_score, 1),
            'violations': violations,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


def find_cross_account_access(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze cross-account access via IAM role trust relationships.

    Identifies:
    - All roles with cross-account trust policies
    - External AWS account IDs with access
    - Wildcard principals (risky!)
    - Third-party service access
    - Risk assessment for each trust relationship

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total cross-account roles, external accounts, risk counts
        - cross_account_roles: Roles with external account access
        - external_accounts: Unique external account IDs
        - risky_trusts: High-risk trust relationships
        - service_linked_roles: AWS service roles (informational)
        - recommendations: Security improvement suggestions

    Example:
        >>> result = find_cross_account_access()
        >>> print(f"External accounts with access: {result['summary']['external_account_count']}")
        >>> for role in result['risky_trusts']:
        ...     print(f"Risky role: {role['role_name']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')
        sts = aws_client.get_client('sts')

        # Get current account ID
        current_account = sts.get_caller_identity()['Account']

        # Get all roles
        roles_response = iam.list_roles()
        all_roles = roles_response.get('Roles', [])

        while roles_response.get('IsTruncated', False):
            roles_response = iam.list_roles(Marker=roles_response['Marker'])
            all_roles.extend(roles_response.get('Roles', []))

        cross_account_roles = []
        external_accounts = set()
        risky_trusts = []
        service_linked_roles = []
        same_account_roles = []

        for role in all_roles:
            role_name = role['RoleName']
            trust_policy = role.get('AssumeRolePolicyDocument', {})

            # Skip service-linked roles (managed by AWS)
            if role.get('Path', '').startswith('/aws-service-role/'):
                service_linked_roles.append({
                    'role_name': role_name,
                    'path': role.get('Path'),
                    'description': role.get('Description', 'AWS service role')
                })
                continue

            # Parse trust policy
            statements = trust_policy.get('Statement', [])

            for statement in statements:
                effect = statement.get('Effect', '')
                if effect != 'Allow':
                    continue

                principal = statement.get('Principal', {})

                # Check for AWS principals
                aws_principals = principal.get('AWS', [])
                if isinstance(aws_principals, str):
                    aws_principals = [aws_principals]

                # Check for Service principals
                service_principals = principal.get('Service', [])
                if isinstance(service_principals, str):
                    service_principals = [service_principals]

                role_info = {
                    'role_name': role_name,
                    'role_arn': role['Arn'],
                    'created': role['CreateDate'].isoformat(),
                    'aws_principals': aws_principals,
                    'service_principals': service_principals,
                    'conditions': statement.get('Condition', {}),
                    'risk_factors': []
                }

                # Analyze AWS principals
                for principal_arn in aws_principals:
                    # Check for wildcards
                    if '*' in principal_arn:
                        role_info['risk_factors'].append('Wildcard principal - EXTREMELY RISKY!')
                        risky_trusts.append({
                            **role_info,
                            'risk_level': 'critical',
                            'principal': principal_arn,
                            'issue': 'Wildcard principal allows any AWS account to assume this role'
                        })
                        continue

                    # Extract account ID from ARN or root principal
                    account_id = None
                    if principal_arn.startswith('arn:aws:iam::'):
                        # Format: arn:aws:iam::123456789012:...
                        parts = principal_arn.split(':')
                        if len(parts) >= 5:
                            account_id = parts[4]
                    elif principal_arn.isdigit() and len(principal_arn) == 12:
                        # Direct account ID
                        account_id = principal_arn

                    if account_id and account_id != current_account:
                        external_accounts.add(account_id)
                        role_info['external_account_id'] = account_id
                        role_info['risk_factors'].append(f'External account: {account_id}')

                        # Check if conditions are present (reduces risk)
                        if not statement.get('Condition'):
                            role_info['risk_factors'].append('No conditions on trust - consider adding ExternalId')

                        cross_account_roles.append(role_info)
                    elif account_id == current_account:
                        same_account_roles.append(role_info)

        # Risk assessment
        critical_risk = len([r for r in risky_trusts if r.get('risk_level') == 'critical'])
        high_risk = len([r for r in cross_account_roles if not r.get('conditions') and 'Wildcard' not in str(r.get('risk_factors', []))])

        # Generate recommendations
        recommendations = []

        if critical_risk > 0:
            recommendations.append(
                f"🚨 CRITICAL: Fix {critical_risk} role(s) with wildcard principals immediately!"
            )

        if high_risk > 0:
            recommendations.append(
                f"⚠️ Add ExternalId conditions to {high_risk} cross-account role(s) without conditions"
            )

        if cross_account_roles:
            recommendations.append(
                f"Review and document {len(cross_account_roles)} cross-account access relationships"
            )
            recommendations.append(
                "Verify all external account IDs are authorized and documented"
            )

        recommendations.append(
            "Implement regular audits of cross-account trust relationships"
        )

        if not cross_account_roles and not risky_trusts:
            recommendations.append(
                "✅ No cross-account access detected - good security posture"
            )

        return {
            'summary': {
                'total_roles': len(all_roles),
                'cross_account_roles': len(cross_account_roles),
                'external_account_count': len(external_accounts),
                'risky_trusts': len(risky_trusts),
                'service_linked_roles': len(service_linked_roles),
                'current_account_id': current_account
            },
            'cross_account_roles': cross_account_roles,
            'external_accounts': sorted(list(external_accounts)),
            'risky_trusts': risky_trusts,
            'service_linked_roles': service_linked_roles[:10],  # Limit output
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


def detect_privilege_escalation_paths(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Detect IAM privilege escalation paths and risky permission combinations.

    Checks for dangerous permission combinations that allow privilege escalation:
    - iam:PassRole + service creation permissions (Lambda, EC2, etc.)
    - iam:CreateAccessKey on other users
    - iam:UpdateAssumeRolePolicy
    - iam:AttachUserPolicy / iam:AttachRolePolicy
    - iam:PutUserPolicy / iam:PutRolePolicy
    - iam:CreatePolicyVersion with SetAsDefault
    - iam:AddUserToGroup with admin groups

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Total users/roles checked, escalation paths found
        - privilege_escalation_paths: Detailed escalation vectors
        - high_risk_permissions: Dangerous permission combinations
        - affected_principals: Users/roles with escalation capabilities
        - recommendations: Remediation suggestions

    Example:
        >>> result = detect_privilege_escalation_paths()
        >>> if result['summary']['escalation_paths_found'] > 0:
        ...     print("WARNING: Privilege escalation paths detected!")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')

        # Dangerous permission combinations that allow privilege escalation
        escalation_vectors = {
            'PassRole + CreateFunction': {
                'permissions': ['iam:PassRole', 'lambda:CreateFunction'],
                'description': 'Can create Lambda function with privileged role and execute arbitrary code',
                'severity': 'critical'
            },
            'PassRole + CreateInstance': {
                'permissions': ['iam:PassRole', 'ec2:RunInstances'],
                'description': 'Can launch EC2 instance with privileged role',
                'severity': 'high'
            },
            'CreateAccessKey': {
                'permissions': ['iam:CreateAccessKey'],
                'description': 'Can create access keys for other users (if not scoped to self)',
                'severity': 'critical'
            },
            'UpdateAssumeRolePolicy': {
                'permissions': ['iam:UpdateAssumeRolePolicy'],
                'description': 'Can modify role trust policy to allow self to assume privileged role',
                'severity': 'critical'
            },
            'AttachUserPolicy': {
                'permissions': ['iam:AttachUserPolicy'],
                'description': 'Can attach administrator policies to users',
                'severity': 'critical'
            },
            'AttachRolePolicy': {
                'permissions': ['iam:AttachRolePolicy'],
                'description': 'Can attach administrator policies to roles',
                'severity': 'critical'
            },
            'PutUserPolicy': {
                'permissions': ['iam:PutUserPolicy'],
                'description': 'Can add inline policies with admin permissions to users',
                'severity': 'critical'
            },
            'PutRolePolicy': {
                'permissions': ['iam:PutRolePolicy'],
                'description': 'Can add inline policies with admin permissions to roles',
                'severity': 'critical'
            },
            'CreatePolicyVersion': {
                'permissions': ['iam:CreatePolicyVersion'],
                'description': 'Can create new policy version with elevated permissions',
                'severity': 'high'
            },
            'SetDefaultPolicyVersion': {
                'permissions': ['iam:SetDefaultPolicyVersion'],
                'description': 'Can activate dormant policy version with elevated permissions',
                'severity': 'high'
            },
            'AddUserToGroup': {
                'permissions': ['iam:AddUserToGroup'],
                'description': 'Can add users to groups with elevated permissions',
                'severity': 'high'
            }
        }

        # Get all users and roles
        users_response = iam.list_users()
        all_users = users_response.get('Users', [])

        while users_response.get('IsTruncated', False):
            users_response = iam.list_users(Marker=users_response['Marker'])
            all_users.extend(users_response.get('Users', []))

        roles_response = iam.list_roles()
        all_roles = roles_response.get('Roles', [])

        while roles_response.get('IsTruncated', False):
            roles_response = iam.list_roles(Marker=roles_response['Marker'])
            all_roles.extend(roles_response.get('Roles', []))

        escalation_paths = []
        affected_principals = []

        def check_permissions(principal_name, principal_type, policies):
            """Check if principal has dangerous permission combinations."""
            found_permissions = set()

            # Extract all actions from policies
            for policy_doc in policies:
                statements = policy_doc.get('Statement', [])
                for statement in statements:
                    if statement.get('Effect') != 'Allow':
                        continue

                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]

                    for action in actions:
                        # Handle wildcards
                        if action == '*' or action == 'iam:*':
                            # Full admin - has all permissions
                            found_permissions.update([
                                'iam:PassRole', 'lambda:CreateFunction', 'ec2:RunInstances',
                                'iam:CreateAccessKey', 'iam:UpdateAssumeRolePolicy',
                                'iam:AttachUserPolicy', 'iam:AttachRolePolicy',
                                'iam:PutUserPolicy', 'iam:PutRolePolicy',
                                'iam:CreatePolicyVersion', 'iam:SetDefaultPolicyVersion',
                                'iam:AddUserToGroup'
                            ])
                            break
                        else:
                            found_permissions.add(action.lower())

            # Check for escalation vectors
            for vector_name, vector_info in escalation_vectors.items():
                required_perms = [p.lower() for p in vector_info['permissions']]

                # Check if all required permissions are present
                if all(perm in found_permissions or any(perm in fp for fp in found_permissions if '*' in fp) for perm in required_perms):
                    escalation_paths.append({
                        'principal_name': principal_name,
                        'principal_type': principal_type,
                        'vector': vector_name,
                        'permissions': vector_info['permissions'],
                        'description': vector_info['description'],
                        'severity': vector_info['severity']
                    })

                    if principal_name not in [p['name'] for p in affected_principals]:
                        affected_principals.append({
                            'name': principal_name,
                            'type': principal_type,
                            'escalation_vectors': []
                        })

                    # Add vector to principal
                    for principal in affected_principals:
                        if principal['name'] == principal_name:
                            principal['escalation_vectors'].append(vector_name)

        # Check users (sample first 50 to avoid timeout)
        for user in all_users[:50]:
            username = user['UserName']
            user_policies = []

            try:
                # Get inline policies
                inline_policies = iam.list_user_policies(UserName=username)
                for policy_name in inline_policies.get('PolicyNames', []):
                    policy_doc = iam.get_user_policy(UserName=username, PolicyName=policy_name)
                    user_policies.append(policy_doc.get('PolicyDocument', {}))

                # Get attached policies
                attached = iam.list_attached_user_policies(UserName=username)
                for policy in attached.get('AttachedPolicies', []):
                    policy_arn = policy['PolicyArn']
                    try:
                        policy_version = iam.get_policy(PolicyArn=policy_arn)
                        default_version = policy_version['Policy']['DefaultVersionId']
                        policy_doc = iam.get_policy_version(PolicyArn=policy_arn, VersionId=default_version)
                        user_policies.append(policy_doc['PolicyVersion']['Document'])
                    except Exception:
                        pass

                # Get group policies
                groups = iam.list_groups_for_user(UserName=username)
                for group in groups.get('Groups', []):
                    group_name = group['GroupName']

                    # Group inline policies
                    group_inline = iam.list_group_policies(GroupName=group_name)
                    for policy_name in group_inline.get('PolicyNames', []):
                        policy_doc = iam.get_group_policy(GroupName=group_name, PolicyName=policy_name)
                        user_policies.append(policy_doc.get('PolicyDocument', {}))

                    # Group attached policies
                    group_attached = iam.list_attached_group_policies(GroupName=group_name)
                    for policy in group_attached.get('AttachedPolicies', []):
                        policy_arn = policy['PolicyArn']
                        try:
                            policy_version = iam.get_policy(PolicyArn=policy_arn)
                            default_version = policy_version['Policy']['DefaultVersionId']
                            policy_doc = iam.get_policy_version(PolicyArn=policy_arn, VersionId=default_version)
                            user_policies.append(policy_doc['PolicyVersion']['Document'])
                        except Exception:
                            pass

                check_permissions(username, 'user', user_policies)

            except Exception as e:
                pass

        # Check roles (sample first 50)
        for role in all_roles[:50]:
            if role.get('Path', '').startswith('/aws-service-role/'):
                continue  # Skip service-linked roles

            role_name = role['RoleName']
            role_policies = []

            try:
                # Get inline policies
                inline_policies = iam.list_role_policies(RoleName=role_name)
                for policy_name in inline_policies.get('PolicyNames', []):
                    policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                    role_policies.append(policy_doc.get('PolicyDocument', {}))

                # Get attached policies
                attached = iam.list_attached_role_policies(RoleName=role_name)
                for policy in attached.get('AttachedPolicies', []):
                    policy_arn = policy['PolicyArn']
                    try:
                        policy_version = iam.get_policy(PolicyArn=policy_arn)
                        default_version = policy_version['Policy']['DefaultVersionId']
                        policy_doc = iam.get_policy_version(PolicyArn=policy_arn, VersionId=default_version)
                        role_policies.append(policy_doc['PolicyVersion']['Document'])
                    except Exception:
                        pass

                check_permissions(role_name, 'role', role_policies)

            except Exception:
                pass

        # Count by severity
        critical_count = len([p for p in escalation_paths if p['severity'] == 'critical'])
        high_count = len([p for p in escalation_paths if p['severity'] == 'high'])

        # Generate recommendations
        recommendations = []

        if critical_count > 0:
            recommendations.append(
                f"🚨 CRITICAL: Found {critical_count} critical privilege escalation path(s)!"
            )

        if high_count > 0:
            recommendations.append(
                f"⚠️ Found {high_count} high-risk privilege escalation path(s)"
            )

        if escalation_paths:
            recommendations.append(
                "Review and scope down permissions for affected principals"
            )
            recommendations.append(
                "Use permission boundaries to limit maximum permissions"
            )
            recommendations.append(
                "Implement SCPs (Service Control Policies) to prevent escalation"
            )

        if not escalation_paths:
            recommendations.append(
                "✅ No obvious privilege escalation paths detected"
            )
        else:
            recommendations.append(
                f"Audit {len(affected_principals)} principal(s) with escalation capabilities"
            )

        return {
            'summary': {
                'users_checked': min(len(all_users), 50),
                'roles_checked': min(len(all_roles), 50),
                'escalation_paths_found': len(escalation_paths),
                'affected_principals': len(affected_principals),
                'critical_severity': critical_count,
                'high_severity': high_count
            },
            'privilege_escalation_paths': escalation_paths,
            'affected_principals': affected_principals,
            'escalation_vectors': escalation_vectors,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


def analyze_unused_permissions(
    days_back: int = 90,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze unused IAM permissions using service last accessed data.

    Identifies permissions that are granted but never used, helping enforce
    the principle of least privilege.

    Note: Requires IAM Access Analyzer to be enabled. This function uses
    service-level data (which services were accessed), not action-level.

    Args:
        days_back: Number of days to look back for access data (default: 90)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: Overview of analysis
        - users_with_unused_services: Users with granted but unused services
        - roles_with_unused_services: Roles with granted but unused services
        - optimization_opportunities: Specific permission removal suggestions
        - recommendations: Least privilege enforcement suggestions

    Example:
        >>> result = analyze_unused_permissions(days_back=90)
        >>> print(f"Users with unused permissions: {len(result['users_with_unused_services'])}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')

        # Get all users (sample to avoid timeout)
        users_response = iam.list_users(MaxItems=50)
        all_users = users_response.get('Users', [])

        users_with_unused = []
        roles_with_unused = []

        now = datetime.now(timezone.utc)
        lookback_date = now - timedelta(days=days_back)

        # Analyze users
        for user in all_users[:25]:  # Limit to 25 users
            username = user['UserName']

            try:
                # Generate service last accessed report
                report_response = iam.generate_service_last_accessed_details(
                    Arn=user['Arn']
                )
                job_id = report_response['JobId']

                # Wait for report to complete (with timeout)
                max_attempts = 10
                for attempt in range(max_attempts):
                    time.sleep(2)

                    details_response = iam.get_service_last_accessed_details(JobId=job_id)

                    if details_response['JobStatus'] == 'COMPLETED':
                        services = details_response.get('ServicesLastAccessed', [])

                        unused_services = []
                        for service in services:
                            service_name = service['ServiceName']
                            service_namespace = service['ServiceNamespace']
                            last_accessed = service.get('LastAuthenticated')

                            # Check if service was never accessed or not accessed recently
                            if not last_accessed or last_accessed < lookback_date:
                                unused_services.append({
                                    'service_name': service_name,
                                    'service_namespace': service_namespace,
                                    'last_accessed': last_accessed.isoformat() if last_accessed else 'Never',
                                    'days_since_access': (now - last_accessed).days if last_accessed else None
                                })

                        if unused_services:
                            users_with_unused.append({
                                'username': username,
                                'unused_services': unused_services,
                                'unused_count': len(unused_services)
                            })

                        break

                    elif details_response['JobStatus'] == 'FAILED':
                        break

            except Exception as e:
                # Skip this user if there's an error
                pass

        # Get sample roles
        roles_response = iam.list_roles(MaxItems=25)
        all_roles = roles_response.get('Roles', [])

        # Analyze roles (limit to non-service roles)
        for role in all_roles[:15]:
            if role.get('Path', '').startswith('/aws-service-role/'):
                continue

            role_name = role['RoleName']

            try:
                report_response = iam.generate_service_last_accessed_details(
                    Arn=role['Arn']
                )
                job_id = report_response['JobId']

                max_attempts = 10
                for attempt in range(max_attempts):
                    time.sleep(2)

                    details_response = iam.get_service_last_accessed_details(JobId=job_id)

                    if details_response['JobStatus'] == 'COMPLETED':
                        services = details_response.get('ServicesLastAccessed', [])

                        unused_services = []
                        for service in services:
                            service_name = service['ServiceName']
                            service_namespace = service['ServiceNamespace']
                            last_accessed = service.get('LastAuthenticated')

                            if not last_accessed or last_accessed < lookback_date:
                                unused_services.append({
                                    'service_name': service_name,
                                    'service_namespace': service_namespace,
                                    'last_accessed': last_accessed.isoformat() if last_accessed else 'Never',
                                    'days_since_access': (now - last_accessed).days if last_accessed else None
                                })

                        if unused_services:
                            roles_with_unused.append({
                                'role_name': role_name,
                                'unused_services': unused_services,
                                'unused_count': len(unused_services)
                            })

                        break

                    elif details_response['JobStatus'] == 'FAILED':
                        break

            except Exception:
                pass

        # Generate recommendations
        recommendations = []

        if users_with_unused or roles_with_unused:
            recommendations.append(
                f"Review and remove unused service permissions from {len(users_with_unused)} user(s) and {len(roles_with_unused)} role(s)"
            )
            recommendations.append(
                "Implement least privilege by removing permissions not used in 90 days"
            )
            recommendations.append(
                "Use IAM Access Analyzer for detailed action-level recommendations"
            )

        recommendations.append(
            "Regularly audit permissions using service last accessed data"
        )

        recommendations.append(
            "Consider implementing Permission Boundaries for additional protection"
        )

        if not users_with_unused and not roles_with_unused:
            recommendations.append(
                "✅ All analyzed principals are using their granted permissions efficiently"
            )

        return {
            'summary': {
                'users_analyzed': len(all_users[:25]),
                'roles_analyzed': len([r for r in all_roles[:15] if not r.get('Path', '').startswith('/aws-service-role/')]),
                'users_with_unused_services': len(users_with_unused),
                'roles_with_unused_services': len(roles_with_unused),
                'lookback_days': days_back
            },
            'users_with_unused_services': users_with_unused,
            'roles_with_unused_services': roles_with_unused,
            'recommendations': recommendations,
            'note': 'This analysis uses service-level data. For action-level details, use IAM Access Analyzer in the AWS Console.'
        }

    except Exception as e:
        return {'error': str(e)}


def get_iam_credential_report(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Generate and parse IAM credential report for comprehensive security audit.

    The credential report provides a comprehensive view of all IAM users and
    their credential status including:
    - Password status and age
    - Access key status and age
    - MFA device assignments
    - Last login/usage dates

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - summary: High-level statistics
        - security_findings: Critical security issues
        - users: List of users with credential details
        - compliance_metrics: Compliance-related metrics
        - recommendations: Security improvement suggestions

    Example:
        >>> result = get_iam_credential_report()
        >>> print(f"Users without MFA: {result['summary']['users_without_mfa']}")
        >>> print(f"Old passwords: {result['summary']['passwords_over_90_days']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        iam = aws_client.get_client('iam')

        # Generate credential report
        try:
            iam.generate_credential_report()
        except Exception:
            pass

        # Wait for report to be ready (with timeout)
        max_attempts = 20
        report_content = None

        for attempt in range(max_attempts):
            try:
                response = iam.get_credential_report()
                if response['Content']:
                    report_content = response['Content'].decode('utf-8')
                    break
            except iam.exceptions.CredentialReportNotReadyException:
                time.sleep(2)
            except Exception as e:
                break

        if not report_content:
            return {
                'error': 'Failed to generate credential report',
                'recommendations': ['Try again in a few moments']
            }

        # Parse CSV report
        csv_reader = csv.DictReader(io.StringIO(report_content))
        users = []

        now = datetime.now(timezone.utc)

        # Statistics
        total_users = 0
        users_with_password = 0
        users_with_mfa = 0
        users_without_mfa = 0
        passwords_over_90_days = 0
        access_keys_over_90_days = 0
        inactive_users = 0
        root_account_info = None

        for row in csv_reader:
            username = row.get('user', '')

            # Parse dates
            def parse_date(date_str):
                if date_str and date_str != 'N/A' and date_str != 'no_information':
                    try:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        pass
                return None

            password_enabled = row.get('password_enabled', 'false') == 'true'
            password_last_used = parse_date(row.get('password_last_used'))
            password_last_changed = parse_date(row.get('password_last_changed'))

            mfa_active = row.get('mfa_active', 'false') == 'true'

            access_key_1_active = row.get('access_key_1_active', 'false') == 'true'
            access_key_1_last_rotated = parse_date(row.get('access_key_1_last_rotated'))
            access_key_1_last_used = parse_date(row.get('access_key_1_last_used_date'))

            access_key_2_active = row.get('access_key_2_active', 'false') == 'true'
            access_key_2_last_rotated = parse_date(row.get('access_key_2_last_rotated'))
            access_key_2_last_used = parse_date(row.get('access_key_2_last_used_date'))

            # Calculate ages
            password_age = (now - password_last_changed).days if password_last_changed else None
            key1_age = (now - access_key_1_last_rotated).days if access_key_1_last_rotated else None
            key2_age = (now - access_key_2_last_rotated).days if access_key_2_last_rotated else None

            # Determine last activity
            last_activity = None
            for date in [password_last_used, access_key_1_last_used, access_key_2_last_used]:
                if date and (not last_activity or date > last_activity):
                    last_activity = date

            days_inactive = (now - last_activity).days if last_activity else None

            user_info = {
                'username': username,
                'password_enabled': password_enabled,
                'password_last_used': password_last_used.isoformat() if password_last_used else None,
                'password_last_changed': password_last_changed.isoformat() if password_last_changed else None,
                'password_age_days': password_age,
                'mfa_active': mfa_active,
                'access_key_1_active': access_key_1_active,
                'access_key_1_age_days': key1_age,
                'access_key_2_active': access_key_2_active,
                'access_key_2_age_days': key2_age,
                'last_activity': last_activity.isoformat() if last_activity else None,
                'days_inactive': days_inactive,
                'issues': []
            }

            # Track root account separately
            if username == '<root_account>':
                root_account_info = user_info
                continue

            total_users += 1

            # Identify issues
            if password_enabled:
                users_with_password += 1

                if not mfa_active:
                    users_without_mfa += 1
                    user_info['issues'].append('No MFA on console access')
                else:
                    users_with_mfa += 1

                if password_age and password_age > 90:
                    passwords_over_90_days += 1
                    user_info['issues'].append(f'Password age: {password_age} days')

            if access_key_1_active and key1_age and key1_age > 90:
                access_keys_over_90_days += 1
                user_info['issues'].append(f'Access key 1 age: {key1_age} days')

            if access_key_2_active and key2_age and key2_age > 90:
                access_keys_over_90_days += 1
                user_info['issues'].append(f'Access key 2 age: {key2_age} days')

            if days_inactive and days_inactive > 90:
                inactive_users += 1
                user_info['issues'].append(f'Inactive for {days_inactive} days')

            users.append(user_info)

        # Calculate compliance rate
        console_users = users_with_password
        mfa_compliance = (users_with_mfa / console_users * 100) if console_users > 0 else 100

        # Generate recommendations
        recommendations = []

        if root_account_info and not root_account_info.get('mfa_active'):
            recommendations.append(
                "🚨 CRITICAL: Enable MFA on root account!"
            )

        if users_without_mfa > 0:
            recommendations.append(
                f"⚠️ Enable MFA for {users_without_mfa} console user(s) without MFA"
            )

        if passwords_over_90_days > 0:
            recommendations.append(
                f"Rotate {passwords_over_90_days} password(s) older than 90 days"
            )

        if access_keys_over_90_days > 0:
            recommendations.append(
                f"Rotate {access_keys_over_90_days} access key(s) older than 90 days"
            )

        if inactive_users > 0:
            recommendations.append(
                f"Remove or disable {inactive_users} inactive user(s) (>90 days)"
            )

        if mfa_compliance == 100 and passwords_over_90_days == 0 and access_keys_over_90_days == 0:
            recommendations.append(
                "✅ Excellent credential hygiene - all users compliant!"
            )

        return {
            'summary': {
                'total_users': total_users,
                'users_with_password': users_with_password,
                'users_with_mfa': users_with_mfa,
                'users_without_mfa': users_without_mfa,
                'mfa_compliance_rate': round(mfa_compliance, 1),
                'passwords_over_90_days': passwords_over_90_days,
                'access_keys_over_90_days': access_keys_over_90_days,
                'inactive_users': inactive_users
            },
            'root_account': root_account_info,
            'security_findings': {
                'critical': users_without_mfa if root_account_info and not root_account_info.get('mfa_active') else 0,
                'high': users_without_mfa + passwords_over_90_days,
                'medium': access_keys_over_90_days + inactive_users
            },
            'users': users,
            'compliance_metrics': {
                'mfa_compliance_rate': round(mfa_compliance, 1),
                'password_rotation_compliance': round(((users_with_password - passwords_over_90_days) / users_with_password * 100) if users_with_password > 0 else 100, 1)
            },
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}
