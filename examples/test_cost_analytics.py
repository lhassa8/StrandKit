#!/usr/bin/env python3
"""
Test Cost Analytics tools with live AWS account.

This script tests all 6 Phase 1 Cost Analytics tools to validate
high-value cost optimization capabilities.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Cost Analytics tools
from strandkit.tools.cost_analytics import (
    get_budget_status,
    analyze_reserved_instances,
    analyze_savings_plans,
    get_rightsizing_recommendations,
    analyze_commitment_savings,
    find_cost_optimization_opportunities
)


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)


def test_budget_status():
    """Test budget monitoring."""
    print_section("Testing Budget Status")

    result = get_budget_status(forecast_months=3)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    summary = result.get('summary', {})
    budgets = result.get('budgets', [])

    print(f"\n✅ Budget Status Retrieved")
    print(f"\nSummary:")
    print(f"  Total budgets: {summary.get('total_budgets', 0)}")
    print(f"  On track: {summary.get('on_track', 0)}")
    print(f"  Warning: {summary.get('warning', 0)}")
    print(f"  Exceeded: {summary.get('exceeded', 0)}")

    if budgets:
        print(f"\nBudgets:")
        for budget in budgets:
            status_icon = "✅" if budget['status'] == 'on_track' else "⚠️" if budget['status'] == 'warning' else "🔴"
            print(f"\n  {status_icon} {budget['budget_name']}")
            print(f"     Limit: ${budget['limit']:.2f}")
            print(f"     Current: ${budget['current_spend']:.2f} ({budget['percentage_used']:.1f}%)")
            print(f"     Forecast: ${budget['forecasted_spend']:.2f}")
            print(f"     Status: {budget['status']}")

            if budget['alerts']:
                for alert in budget['alerts']:
                    print(f"     {alert}")

            if budget['root_causes']:
                print(f"     Top services:")
                for cause in budget['root_causes'][:3]:
                    print(f"       - {cause}")
    else:
        print("\n  No budgets configured in this account")

    return result


def test_reserved_instances():
    """Test RI analysis."""
    print_section("Testing Reserved Instance Analysis")

    result = analyze_reserved_instances(service="EC2", lookback_days=30)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Reserved Instance Analysis Complete")

    utilization = result.get('utilization', {})
    coverage = result.get('coverage', {})
    expiring = result.get('expiring_soon', [])

    print(f"\nService: {result.get('service', 'EC2')}")
    print(f"Analysis Period: {result.get('analysis_period', {}).get('days', 0)} days")
    print(f"Total RIs: {result.get('total_ris', 0)}")

    print(f"\nUtilization:")
    print(f"  Average: {utilization.get('average', 0):.1f}%")
    print(f"  Target: {utilization.get('target', 90):.1f}%")
    print(f"  Status: {utilization.get('status', 'unknown')}")

    print(f"\nCoverage:")
    print(f"  Percentage: {coverage.get('percentage', 0):.1f}%")
    print(f"  On-Demand Cost: ${coverage.get('on_demand_cost', 0):.2f}")
    print(f"  Potential Savings: ${coverage.get('potential_savings', 0):.2f}/month")

    if expiring:
        print(f"\nExpiring Soon ({len(expiring)} RIs):")
        for ri in expiring[:5]:
            print(f"  - {ri.get('instance_type')} x{ri.get('instance_count')} expires in {ri.get('days_until_expiry')} days")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_savings_plans():
    """Test Savings Plan analysis."""
    print_section("Testing Savings Plan Analysis")

    result = analyze_savings_plans(lookback_days=30)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Savings Plan Analysis Complete")

    utilization = result.get('utilization', {})
    coverage = result.get('coverage', {})
    active_plans = result.get('active_plans', [])

    print(f"\nAnalysis Period: {result.get('analysis_period', {}).get('days', 0)} days")
    print(f"Total Commitment: ${result.get('total_commitment', 0):.2f}")

    print(f"\nUtilization:")
    print(f"  Average: {utilization.get('average', 0):.1f}%")
    print(f"  Status: {utilization.get('status', 'unknown')}")
    print(f"  Underutilized: ${utilization.get('underutilized_amount', 0):.2f}/month wasted")

    print(f"\nCoverage:")
    print(f"  Percentage: {coverage.get('percentage', 0):.1f}%")
    print(f"  On-Demand Cost: ${coverage.get('on_demand_cost', 0):.2f}")
    print(f"  Savings Plan Cost: ${coverage.get('savings_plan_cost', 0):.2f}")
    print(f"  Total Savings: ${coverage.get('total_savings', 0):.2f}")

    if active_plans:
        print(f"\nActive Plans ({len(active_plans)}):")
        for plan in active_plans[:5]:
            print(f"  - {plan.get('savings_plan_type')}: ${plan.get('commitment', 0):.2f}/hour")

    print(f"\nRecommendations:")
    for rec in result.get('recommendations', []):
        print(f"  {rec}")

    return result


def test_rightsizing():
    """Test rightsizing recommendations."""
    print_section("Testing Rightsizing Recommendations")

    result = get_rightsizing_recommendations(service="EC2", min_savings=10.0)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    if 'message' in result:
        print(f"ℹ️  {result['message']}")

    print(f"✅ Rightsizing Analysis Complete")

    summary = result.get('summary', {})
    recommendations = result.get('recommendations', [])

    print(f"\nService: {result.get('service', 'EC2')}")
    print(f"Recommendations Found: {summary.get('recommendation_count', 0)}")

    print(f"\nPotential Savings:")
    print(f"  Monthly: ${summary.get('total_monthly_savings', 0):.2f}")
    print(f"  Annual: ${summary.get('total_annual_savings', 0):.2f}")

    by_action = summary.get('by_action', {})
    print(f"\nBy Action:")
    print(f"  Modify: ${by_action.get('modify', 0):.2f}/month")
    print(f"  Stop: ${by_action.get('stop', 0):.2f}/month")
    print(f"  Terminate: ${by_action.get('terminate', 0):.2f}/month")

    if recommendations:
        print(f"\nTop Recommendations (up to 10):")
        for i, rec in enumerate(recommendations[:10], 1):
            print(f"\n  {i}. {rec.get('resource_id', 'Unknown')}")
            print(f"     Action: {rec.get('recommended_action', 'Unknown')}")
            print(f"     Current: {rec.get('current_type', 'Unknown')} (${rec.get('current_monthly_cost', 0):.2f}/month)")
            print(f"     Recommended: {rec.get('recommended_type', 'Unknown')} (${rec.get('recommended_monthly_cost', 0):.2f}/month)")
            print(f"     Savings: ${rec.get('monthly_savings', 0):.2f}/month (${rec.get('annual_savings', 0):.2f}/year)")
            print(f"     Reason: {rec.get('reason', 'N/A')}")

    return result


def test_commitment_savings():
    """Test commitment savings recommendations."""
    print_section("Testing Commitment Savings Recommendations")

    result = analyze_commitment_savings(
        service="EC2",
        lookback_days=30,
        commitment_term="ONE_YEAR",
        payment_option="PARTIAL_UPFRONT"
    )

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Commitment Savings Analysis Complete")

    summary = result.get('summary', {})
    recommendations = result.get('recommendations', [])

    print(f"\nService: {result.get('service', 'EC2')}")
    print(f"Analysis Period: {result.get('analysis_period', {}).get('lookback_days', 0)} days")

    print(f"\nPotential Annual Savings: ${summary.get('total_potential_annual_savings', 0):.2f}")
    print(f"Recommendation Count: {summary.get('recommendation_count', 0)}")
    print(f"Action: {summary.get('recommended_action', 'None')}")

    if recommendations:
        print(f"\nRecommendations (up to 5):")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"\n  {i}. {rec.get('recommendation_type', 'Unknown')}")
            print(f"     Term: {rec.get('term', 'Unknown')}")
            print(f"     Payment: {rec.get('payment_option', 'Unknown')}")
            print(f"     Upfront Cost: ${rec.get('upfront_cost', 0):.2f}")
            print(f"     Monthly Cost: ${rec.get('monthly_cost', 0):.2f}")
            print(f"     Monthly Savings: ${rec.get('estimated_monthly_savings', 0):.2f}")
            print(f"     Annual Savings: ${rec.get('estimated_annual_savings', 0):.2f}")
            print(f"     Savings %: {rec.get('savings_percentage', 0):.1f}%")
            print(f"     Break-even: {rec.get('break_even_months', 0):.1f} months")

    return result


def test_optimization_opportunities():
    """Test aggregate optimization opportunities."""
    print_section("Testing Cost Optimization Opportunities")

    result = find_cost_optimization_opportunities(min_impact=50.0)

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None

    print(f"✅ Cost Optimization Analysis Complete")

    summary = result.get('summary', {})
    opportunities = result.get('opportunities', [])
    actions = result.get('prioritized_actions', [])

    print(f"\nSummary:")
    print(f"  Total Opportunities: {summary.get('opportunity_count', 0)}")
    print(f"  Quick Wins (low effort, low risk): {summary.get('quick_wins', 0)}")
    print(f"  High Impact (>$1000/month): {summary.get('high_impact', 0)}")

    print(f"\nPotential Savings:")
    print(f"  Monthly: ${summary.get('total_monthly_savings', 0):.2f}")
    print(f"  Annual: ${summary.get('total_annual_savings', 0):,.2f}")

    if opportunities:
        print(f"\nTop Opportunities (up to 10):")
        for opp in opportunities[:10]:
            icon = "🔴" if opp.get('is_alert') else "💰"
            print(f"\n  {icon} Priority #{opp.get('priority', 0)}: {opp.get('title', 'Unknown')}")
            print(f"     Category: {opp.get('category', 'Unknown')}")
            print(f"     Description: {opp.get('description', 'N/A')}")

            if not opp.get('is_alert'):
                print(f"     Monthly Savings: ${opp.get('monthly_savings', 0):.2f}")
                print(f"     Annual Savings: ${opp.get('annual_savings', 0):.2f}")

            print(f"     Effort: {opp.get('effort', 'Unknown')}")
            print(f"     Risk: {opp.get('risk', 'Unknown')}")
            print(f"     Tool: {opp.get('tool', 'Unknown')}")

    if actions:
        print(f"\nPrioritized Action Plan:")
        for action in actions:
            print(f"  {action}")

    return result


def main():
    """Run all cost analytics tests."""
    print("="*80)
    print("StrandKit Cost Analytics - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTesting 6 Phase 1 Cost Analytics tools:")
    print("  1. Budget Status")
    print("  2. Reserved Instance Analysis")
    print("  3. Savings Plan Analysis")
    print("  4. Rightsizing Recommendations")
    print("  5. Commitment Savings Recommendations")
    print("  6. Cost Optimization Opportunities (Aggregate)")

    # Test 1: Budget Status
    budget_result = test_budget_status()

    # Test 2: Reserved Instances
    ri_result = test_reserved_instances()

    # Test 3: Savings Plans
    sp_result = test_savings_plans()

    # Test 4: Rightsizing
    rightsizing_result = test_rightsizing()

    # Test 5: Commitment Savings
    commitment_result = test_commitment_savings()

    # Test 6: Optimization Opportunities (runs all the above)
    optimization_result = test_optimization_opportunities()

    print_section("Testing Complete")

    # Summary
    print("\n✅ All Cost Analytics tools tested!")
    print("\nKey Insights:")

    if optimization_result and not optimization_result.get('error'):
        summary = optimization_result.get('summary', {})
        print(f"  💰 Total Potential Annual Savings: ${summary.get('total_annual_savings', 0):,.2f}")
        print(f"  📊 Opportunities Found: {summary.get('opportunity_count', 0)}")
        print(f"  ⚡ Quick Wins: {summary.get('quick_wins', 0)}")
        print(f"  🎯 High Impact: {summary.get('high_impact', 0)}")

    print(f"\n💡 Next Steps:")
    print(f"  1. Review detailed recommendations from each tool")
    print(f"  2. Prioritize based on effort vs impact")
    print(f"  3. Implement quick wins first (low effort, low risk)")
    print(f"  4. Schedule larger optimization projects")


if __name__ == "__main__":
    main()
