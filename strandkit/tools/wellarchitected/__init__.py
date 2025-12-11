"""
AWS Well-Architected Framework Tools for StrandKit.

This module provides automated checks aligned with the 6 pillars of the
AWS Well-Architected Framework (2025 edition):

1. Security - Protect data, systems, and assets (23 tools)
   - SEC01-SEC10: Complete coverage of all security questions
2. Reliability - Recover from failures, meet demand (18 tools)
   - REL01-REL13: Complete coverage of all reliability questions
3. Cost Optimization - Avoid unnecessary costs (coming soon)
4. Operational Excellence - Run and monitor systems (coming soon)
5. Performance Efficiency - Use resources efficiently (coming soon)
6. Sustainability - Minimize environmental impact (coming soon)

Each pillar module provides tools that map to specific Well-Architected
Framework questions and best practices.

Usage with Strands Agents:
    from strands import Agent
    from strandkit.strands import get_tools_by_category

    # Get all Well-Architected tools
    agent = Agent(tools=get_tools_by_category('wellarchitected'))

    # Run a comprehensive review
    response = agent("Run a Well-Architected review of my AWS account")

Usage standalone:
    from strandkit.tools.wellarchitected import run_security_pillar_review

    results = run_security_pillar_review()
    print(f"Security Score: {results['score']}/100")
"""

# Security Pillar Tools - Core (15 tools)
from strandkit.tools.wellarchitected.security import (
    check_root_account_usage,
    check_identity_federation,
    check_secrets_management,
    check_encryption_at_rest,
    check_encryption_in_transit,
    check_network_protection,
    check_compute_protection,
    check_data_classification,
    check_incident_response,
    check_detective_controls,
    check_infrastructure_protection,
    check_aws_account_security,
    check_api_security,
    check_database_security,
    run_security_pillar_review,
)

# Security Pillar Tools - Extended (8 tools)
from strandkit.tools.wellarchitected.security_extended import (
    # SEC02 - Authentication
    check_mfa_compliance,
    check_credential_rotation,
    # SEC03 - Permissions
    check_iam_access_analyzer,
    check_permission_boundaries,
    check_resource_policies,
    # SEC06 - Vulnerability Management
    check_vulnerability_management,
    # SEC10 - Incident Response
    check_incident_response_readiness,
    check_forensic_capabilities,
)

# Reliability Pillar Tools - Core (12 tools)
from strandkit.tools.wellarchitected.reliability import (
    check_service_quotas,
    check_network_topology,
    check_backup_strategy,
    check_disaster_recovery,
    check_fault_isolation,
    check_auto_scaling_config,
    check_load_balancer_health,
    check_monitoring_alerting,
    check_distributed_system_design,
    check_change_management,
    check_database_reliability,
    run_reliability_pillar_review,
)

# Reliability Pillar Tools - Extended (6 tools)
from strandkit.tools.wellarchitected.reliability_extended import (
    # REL03 - Workload Architecture
    check_service_architecture,
    # REL04 - Preventing Failures
    check_failure_prevention,
    # REL05 - Mitigating Failures
    check_failure_mitigation,
    # REL11 - Withstanding Failures
    check_availability_design,
    # REL12 - Testing Reliability
    check_reliability_testing,
    check_runbooks_playbooks,
)

__all__ = [
    # Security Pillar - Core (15 tools)
    "check_root_account_usage",
    "check_identity_federation",
    "check_secrets_management",
    "check_encryption_at_rest",
    "check_encryption_in_transit",
    "check_network_protection",
    "check_compute_protection",
    "check_data_classification",
    "check_incident_response",
    "check_detective_controls",
    "check_infrastructure_protection",
    "check_aws_account_security",
    "check_api_security",
    "check_database_security",
    "run_security_pillar_review",
    # Security Pillar - Extended (8 tools)
    "check_mfa_compliance",
    "check_credential_rotation",
    "check_iam_access_analyzer",
    "check_permission_boundaries",
    "check_resource_policies",
    "check_vulnerability_management",
    "check_incident_response_readiness",
    "check_forensic_capabilities",
    # Reliability Pillar - Core (12 tools)
    "check_service_quotas",
    "check_network_topology",
    "check_backup_strategy",
    "check_disaster_recovery",
    "check_fault_isolation",
    "check_auto_scaling_config",
    "check_load_balancer_health",
    "check_monitoring_alerting",
    "check_distributed_system_design",
    "check_change_management",
    "check_database_reliability",
    "run_reliability_pillar_review",
    # Reliability Pillar - Extended (6 tools)
    "check_service_architecture",
    "check_failure_prevention",
    "check_failure_mitigation",
    "check_availability_design",
    "check_reliability_testing",
    "check_runbooks_playbooks",
]
