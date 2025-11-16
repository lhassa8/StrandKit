#!/usr/bin/env python3
"""
Test IAM Security tools with live AWS account.

This script tests all 8 Phase 1 IAM Security tools to validate
security auditing and compliance checking capabilities.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import IAM Security tools
from strandkit.tools.iam_security import (
    analyze_iam_users,
    analyze_access_keys,
    analyze_mfa_compliance,
    analyze_password_policy,
    find_cross_account_access,
    detect_privilege_escalation_paths,
    analyze_unused_permissions,
    get_iam_credential_report
)


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)


def test_analyze_iam_users():
    """Test IAM user analysis."""
    print_section("Testing IAM User Analysis")

    result = analyze_iam_users(inactive_days=90)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ IAM User Analysis Complete")

    summary = result.get('summary', {})
    print(f"\nSummary:")
    print(f"  Total users: {summary.get('total_users', 0)}")
    print(f"  Inactive users: {summary.get('inactive_users', 0)}")
    print(f"  Users without MFA: {summary.get('users_without_mfa', 0)}")
    print(f"  Console users without MFA: {summary.get('console_users_without_mfa', 0)}")
    print(f"  Never logged in: {summary.get('never_logged_in', 0)}")
    print(f"  Old access keys: {summary.get('old_access_keys', 0)}")
    print(f"  MFA compliance rate: {summary.get('mfa_compliance_rate', 0)}%")
    print(f"  Console MFA rate: {summary.get('console_mfa_rate', 0)}%")

    # Show inactive users
    inactive = result.get('inactive_users', [])
    if inactive:
        print(f"\nInactive Users (showing up to 5):")
        for user in inactive[:5]:
            print(f"\n  {user['username']}")
            print(f"    Days inactive: {user['days_inactive']}")
            print(f"    Last activity: {user['last_activity'] or 'Never'}")
            print(f"    Has console: {user['has_console_access']}")
            print(f"    Has MFA: {user['has_mfa']}")

    # Show users without MFA
    no_mfa = result.get('console_users_without_mfa', [])
    if no_mfa:
        print(f"\n⚠️  Console Users Without MFA: {', '.join(no_mfa[:10])}")

    # Show old access keys
    old_keys = result.get('old_access_keys', [])
    if old_keys:
        print(f"\nOld Access Keys (>90 days, showing up to 5):")
        for item in old_keys[:5]:
            print(f"\n  {item['username']}")
            print(f"    Oldest key: {item['oldest_key_days']} days")
            for key in item['old_keys']:
                print(f"      - {key['access_key_id']}: {key['age_days']} days")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_analyze_access_keys():
    """Test access key analysis."""
    print_section("Testing Access Key Analysis")

    result = analyze_access_keys(max_age_days=90)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Access Key Analysis Complete")

    summary = result.get('summary', {})
    print(f"\nSummary:")
    print(f"  Total access keys: {summary.get('total_access_keys', 0)}")
    print(f"  Active keys: {summary.get('active_keys', 0)}")
    print(f"  Inactive keys: {summary.get('inactive_keys', 0)}")
    print(f"  Old access keys (>90 days): {summary.get('old_access_keys', 0)}")
    print(f"  Unused access keys: {summary.get('unused_access_keys', 0)}")
    print(f"  Root access keys: {summary.get('root_access_keys', 0)}")
    print(f"  Users with multiple keys: {summary.get('users_with_multiple_keys', 0)}")

    # Root account keys (CRITICAL!)
    root_keys = result.get('root_access_keys', [])
    if root_keys:
        print(f"\n🚨 CRITICAL: Root Account Access Keys Detected!")
        for key_info in root_keys:
            print(f"  {key_info['message']}")
            print(f"  Recommendation: {key_info['recommendation']}")

    # Old keys
    old_keys = result.get('old_access_keys', [])
    if old_keys:
        print(f"\nOld Access Keys (showing up to 5):")
        for key in old_keys[:5]:
            print(f"\n  {key['username']} - {key['access_key_id']}")
            print(f"    Age: {key['age_days']} days")
            print(f"    Risk: {key['risk_level']}")
            print(f"    Last used: {key['last_used_date'] or 'Never'}")

    # Unused keys
    unused = result.get('unused_access_keys', [])
    if unused:
        print(f"\nUnused Access Keys (showing up to 5):")
        for key in unused[:5]:
            print(f"\n  {key['username']} - {key['access_key_id']}")
            print(f"    Created: {key['days_since_creation']} days ago")
            print(f"    Never used!")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_analyze_mfa_compliance():
    """Test MFA compliance analysis."""
    print_section("Testing MFA Compliance Analysis")

    result = analyze_mfa_compliance()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ MFA Compliance Analysis Complete")

    summary = result.get('summary', {})
    print(f"\nSummary:")
    print(f"  Total users: {summary.get('total_users', 0)}")
    print(f"  Console users: {summary.get('console_users', 0)}")
    print(f"  Users with MFA: {summary.get('users_with_mfa', 0)}")
    print(f"  Users without MFA: {summary.get('users_without_mfa', 0)}")
    print(f"  Console MFA compliance: {summary.get('console_mfa_compliance_rate', 0)}%")
    print(f"  Privileged users without MFA: {summary.get('privileged_users_without_mfa', 0)}")

    # Root MFA status
    root_status = result.get('root_mfa_status', {})
    if root_status.get('enabled'):
        print(f"\n✅ Root Account MFA: ENABLED")
    else:
        print(f"\n🚨 Root Account MFA: DISABLED (CRITICAL!)")

    # MFA device types
    device_types = result.get('mfa_device_types', {})
    print(f"\nMFA Device Types:")
    print(f"  Virtual: {device_types.get('virtual', 0)}")
    print(f"  Hardware: {device_types.get('hardware', 0)}")

    # Users without MFA
    no_mfa = result.get('users_without_mfa', [])
    if no_mfa:
        print(f"\nUsers Without MFA (showing up to 10):")
        for user in no_mfa[:10]:
            marker = "🔴" if user['has_console_access'] else "⚪"
            privilege = " (PRIVILEGED!)" if user['is_privileged'] else ""
            print(f"  {marker} {user['username']}{privilege}")

    # Privileged users without MFA (HIGH PRIORITY!)
    privileged_no_mfa = result.get('privileged_users_without_mfa', [])
    if privileged_no_mfa:
        print(f"\n🚨 Privileged Users Without MFA:")
        for user in privileged_no_mfa:
            print(f"  {user['username']}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_analyze_password_policy():
    """Test password policy analysis."""
    print_section("Testing Password Policy Analysis")

    result = analyze_password_policy()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Password Policy Analysis Complete")

    policy_exists = result.get('policy_exists', False)
    security_score = result.get('security_score', 0)

    print(f"\nPolicy Exists: {policy_exists}")
    print(f"Security Score: {security_score}/100")

    if policy_exists:
        policy = result.get('current_policy', {})
        print(f"\nCurrent Password Policy:")
        print(f"  Minimum Length: {policy.get('MinimumPasswordLength', 'Not set')}")
        print(f"  Require Symbols: {policy.get('RequireSymbols', False)}")
        print(f"  Require Numbers: {policy.get('RequireNumbers', False)}")
        print(f"  Require Uppercase: {policy.get('RequireUppercaseCharacters', False)}")
        print(f"  Require Lowercase: {policy.get('RequireLowercaseCharacters', False)}")
        print(f"  Allow Users to Change: {policy.get('AllowUsersToChangePassword', False)}")
        print(f"  Expire Passwords: {policy.get('ExpirePasswords', False)}")
        print(f"  Max Password Age: {policy.get('MaxPasswordAge', 'N/A')} days")
        print(f"  Password Reuse Prevention: {policy.get('PasswordReusePrevention', 'Not set')}")

    # CIS Benchmark compliance
    cis = result.get('cis_benchmark_compliance', {})
    print(f"\nCIS Benchmark Compliance:")
    print(f"  Compliant checks: {cis.get('compliant_checks', 0)}/{cis.get('total_checks', 0)}")
    print(f"  Compliance rate: {cis.get('compliance_rate', 0)}%")

    # Violations
    violations = result.get('violations', [])
    if violations:
        print(f"\nPolicy Violations:")
        for violation in violations:
            severity_icon = "🚨" if violation['severity'] == 'critical' else "⚠️" if violation['severity'] == 'high' else "⚪"
            print(f"\n  {severity_icon} {violation['check']}")
            print(f"    {violation['message']}")
            print(f"    Recommendation: {violation['recommendation']}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_find_cross_account_access():
    """Test cross-account access analysis."""
    print_section("Testing Cross-Account Access Analysis")

    result = find_cross_account_access()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Cross-Account Access Analysis Complete")

    summary = result.get('summary', {})
    print(f"\nSummary:")
    print(f"  Total roles: {summary.get('total_roles', 0)}")
    print(f"  Cross-account roles: {summary.get('cross_account_roles', 0)}")
    print(f"  External accounts: {summary.get('external_account_count', 0)}")
    print(f"  Risky trusts: {summary.get('risky_trusts', 0)}")
    print(f"  Service-linked roles: {summary.get('service_linked_roles', 0)}")
    print(f"  Current account: {summary.get('current_account_id', 'Unknown')}")

    # External accounts
    external_accounts = result.get('external_accounts', [])
    if external_accounts:
        print(f"\nExternal AWS Accounts with Access:")
        for account_id in external_accounts:
            print(f"  - {account_id}")

    # Risky trusts (CRITICAL!)
    risky = result.get('risky_trusts', [])
    if risky:
        print(f"\n🚨 RISKY TRUST RELATIONSHIPS:")
        for trust in risky:
            print(f"\n  Role: {trust['role_name']}")
            print(f"  Risk Level: {trust['risk_level']}")
            print(f"  Principal: {trust['principal']}")
            print(f"  Issue: {trust['issue']}")

    # Cross-account roles
    cross_account = result.get('cross_account_roles', [])
    if cross_account:
        print(f"\nCross-Account Roles (showing up to 10):")
        for role in cross_account[:10]:
            print(f"\n  {role['role_name']}")
            print(f"    External Account: {role.get('external_account_id', 'Unknown')}")
            if role.get('risk_factors'):
                print(f"    Risk Factors:")
                for factor in role['risk_factors']:
                    print(f"      - {factor}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_detect_privilege_escalation():
    """Test privilege escalation path detection."""
    print_section("Testing Privilege Escalation Detection")

    result = detect_privilege_escalation_paths()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Privilege Escalation Detection Complete")

    summary = result.get('summary', {})
    print(f"\nSummary:")
    print(f"  Users checked: {summary.get('users_checked', 0)}")
    print(f"  Roles checked: {summary.get('roles_checked', 0)}")
    print(f"  Escalation paths found: {summary.get('escalation_paths_found', 0)}")
    print(f"  Affected principals: {summary.get('affected_principals', 0)}")
    print(f"  Critical severity: {summary.get('critical_severity', 0)}")
    print(f"  High severity: {summary.get('high_severity', 0)}")

    # Escalation paths
    paths = result.get('privilege_escalation_paths', [])
    if paths:
        print(f"\nPrivilege Escalation Paths Found:")
        for path in paths[:10]:  # Show up to 10
            severity_icon = "🚨" if path['severity'] == 'critical' else "⚠️"
            print(f"\n  {severity_icon} {path['principal_name']} ({path['principal_type']})")
            print(f"    Vector: {path['vector']}")
            print(f"    Severity: {path['severity']}")
            print(f"    Permissions: {', '.join(path['permissions'])}")
            print(f"    Description: {path['description']}")

    # Affected principals
    affected = result.get('affected_principals', [])
    if affected:
        print(f"\nAffected Principals (showing up to 10):")
        for principal in affected[:10]:
            vectors = ', '.join(principal['escalation_vectors'])
            print(f"  {principal['name']} ({principal['type']}): {vectors}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_analyze_unused_permissions():
    """Test unused permissions analysis."""
    print_section("Testing Unused Permissions Analysis")

    result = analyze_unused_permissions(days_back=90)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Unused Permissions Analysis Complete")

    summary = result.get('summary', {})
    print(f"\nSummary:")
    print(f"  Users analyzed: {summary.get('users_analyzed', 0)}")
    print(f"  Roles analyzed: {summary.get('roles_analyzed', 0)}")
    print(f"  Users with unused services: {summary.get('users_with_unused_services', 0)}")
    print(f"  Roles with unused services: {summary.get('roles_with_unused_services', 0)}")
    print(f"  Lookback period: {summary.get('lookback_days', 0)} days")

    # Users with unused services
    users_unused = result.get('users_with_unused_services', [])
    if users_unused:
        print(f"\nUsers with Unused Services (showing up to 5):")
        for user in users_unused[:5]:
            print(f"\n  {user['username']}")
            print(f"    Unused services: {user['unused_count']}")
            print(f"    Top unused services:")
            for service in user['unused_services'][:5]:
                last_access = service['last_accessed']
                print(f"      - {service['service_name']}: {last_access}")

    # Roles with unused services
    roles_unused = result.get('roles_with_unused_services', [])
    if roles_unused:
        print(f"\nRoles with Unused Services (showing up to 5):")
        for role in roles_unused[:5]:
            print(f"\n  {role['role_name']}")
            print(f"    Unused services: {role['unused_count']}")

    print(f"\nNote: {result.get('note', '')}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_get_credential_report():
    """Test IAM credential report."""
    print_section("Testing IAM Credential Report")

    result = get_iam_credential_report()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ IAM Credential Report Generated")

    summary = result.get('summary', {})
    print(f"\nSummary:")
    print(f"  Total users: {summary.get('total_users', 0)}")
    print(f"  Users with password: {summary.get('users_with_password', 0)}")
    print(f"  Users with MFA: {summary.get('users_with_mfa', 0)}")
    print(f"  Users without MFA: {summary.get('users_without_mfa', 0)}")
    print(f"  MFA compliance: {summary.get('mfa_compliance_rate', 0)}%")
    print(f"  Passwords >90 days: {summary.get('passwords_over_90_days', 0)}")
    print(f"  Access keys >90 days: {summary.get('access_keys_over_90_days', 0)}")
    print(f"  Inactive users: {summary.get('inactive_users', 0)}")

    # Root account
    root = result.get('root_account')
    if root:
        print(f"\nRoot Account:")
        print(f"  MFA enabled: {root.get('mfa_active', False)}")
        print(f"  Password last used: {root.get('password_last_used', 'Never')}")

    # Security findings
    findings = result.get('security_findings', {})
    print(f"\nSecurity Findings:")
    print(f"  Critical: {findings.get('critical', 0)}")
    print(f"  High: {findings.get('high', 0)}")
    print(f"  Medium: {findings.get('medium', 0)}")

    # Compliance metrics
    compliance = result.get('compliance_metrics', {})
    print(f"\nCompliance Metrics:")
    print(f"  MFA compliance: {compliance.get('mfa_compliance_rate', 0)}%")
    print(f"  Password rotation: {compliance.get('password_rotation_compliance', 0)}%")

    # Users with issues (sample)
    users = result.get('users', [])
    users_with_issues = [u for u in users if u.get('issues')]
    if users_with_issues:
        print(f"\nUsers with Issues (showing up to 10):")
        for user in users_with_issues[:10]:
            print(f"\n  {user['username']}")
            for issue in user['issues']:
                print(f"    ⚠️  {issue}")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def main():
    """Run all IAM security tests."""
    print("="*80)
    print("StrandKit IAM Security - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTesting 8 Phase 1 IAM Security tools:")
    print("  1. analyze_iam_users")
    print("  2. analyze_access_keys")
    print("  3. analyze_mfa_compliance")
    print("  4. analyze_password_policy")
    print("  5. find_cross_account_access")
    print("  6. detect_privilege_escalation_paths")
    print("  7. analyze_unused_permissions")
    print("  8. get_iam_credential_report")

    results = {}

    # Test 1: IAM Users
    results['users'] = test_analyze_iam_users()

    # Test 2: Access Keys
    results['access_keys'] = test_analyze_access_keys()

    # Test 3: MFA Compliance
    results['mfa'] = test_analyze_mfa_compliance()

    # Test 4: Password Policy
    results['password_policy'] = test_analyze_password_policy()

    # Test 5: Cross-Account Access
    results['cross_account'] = test_find_cross_account_access()

    # Test 6: Privilege Escalation
    results['escalation'] = test_detect_privilege_escalation()

    # Test 7: Unused Permissions
    results['unused_perms'] = test_analyze_unused_permissions()

    # Test 8: Credential Report
    results['cred_report'] = test_get_credential_report()

    print_section("Testing Complete")

    # Summary
    print("\n✅ All IAM Security tools tested!")

    successful = sum(1 for r in results.values() if r and 'error' not in r)
    print(f"\nSuccess Rate: {successful}/8 tools working")

    if successful == 8:
        print("\n🎉 Perfect! All tools are working correctly!")
    elif successful >= 6:
        print("\n✅ Most tools working. Check errors above for details.")
    else:
        print("\n⚠️  Multiple tools had errors. Review output above.")

    print(f"\n💡 Key Findings:")
    if results.get('mfa'):
        mfa_compliance = results['mfa'].get('summary', {}).get('console_mfa_compliance_rate', 0)
        print(f"  MFA Compliance: {mfa_compliance}%")

    if results.get('password_policy'):
        security_score = results['password_policy'].get('security_score', 0)
        print(f"  Password Policy Score: {security_score}/100")

    if results.get('escalation'):
        escalation_paths = results['escalation'].get('summary', {}).get('escalation_paths_found', 0)
        if escalation_paths > 0:
            print(f"  ⚠️  Privilege Escalation Paths: {escalation_paths}")

    if results.get('cross_account'):
        external_accounts = results['cross_account'].get('summary', {}).get('external_account_count', 0)
        if external_accounts > 0:
            print(f"  External Accounts with Access: {external_accounts}")


if __name__ == "__main__":
    main()
