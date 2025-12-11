"""
AWS Well-Architected Framework Tools for StrandKit.

This module provides automated checks aligned with the 6 pillars of the
AWS Well-Architected Framework:

1. Security - Protect data, systems, and assets (15 tools)
2. Reliability - Recover from failures, meet demand (12 tools)
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

# Security Pillar Tools (15 tools)
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

# Reliability Pillar Tools (12 tools)
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

__all__ = [
    # Security Pillar (15 tools)
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
    # Reliability Pillar (12 tools)
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
]
