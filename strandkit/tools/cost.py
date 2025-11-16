"""
Cost Explorer tools for StrandKit.

This module provides tools for analyzing AWS costs and spending:
- get_cost_and_usage: Get cost data for a time period
- detect_cost_anomalies: Find unusual spending patterns
- get_cost_by_service: Break down costs by AWS service
- get_cost_forecast: Forecast future costs

These tools help with cost optimization and budget management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from strandkit.core.aws_client import AWSClient


def get_cost_and_usage(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days_back: int = 30,
    granularity: str = "DAILY",
    metrics: Optional[List[str]] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get AWS cost and usage data for a specified time period.

    Args:
        start_date: Start date (YYYY-MM-DD). If None, calculated from days_back
        end_date: End date (YYYY-MM-DD). If None, uses today
        days_back: Number of days to look back if start_date not specified (default: 30)
        granularity: Time granularity - "DAILY", "MONTHLY", or "HOURLY" (default: "DAILY")
        metrics: List of metrics to retrieve. Default: ["UnblendedCost"]
                Options: "UnblendedCost", "BlendedCost", "UsageQuantity", "NormalizedUsageAmount"
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "time_period": {
                "start": str,
                "end": str
            },
            "granularity": str,
            "total_cost": float,
            "currency": str,
            "results_by_time": [
                {
                    "date": str,
                    "amount": float,
                    "unit": str
                }
            ],
            "summary": {
                "total": float,
                "average_daily": float,
                "min_daily": float,
                "max_daily": float
            }
        }

    Example:
        >>> # Get last 30 days of costs
        >>> costs = get_cost_and_usage(days_back=30)
        >>> print(f"Total: ${costs['total_cost']:.2f}")
        >>> print(f"Avg daily: ${costs['summary']['average_daily']:.2f}")

    Tool Schema (for LLMs):
        {
            "name": "get_cost_and_usage",
            "description": "Get AWS cost and usage data",
            "parameters": {
                "days_back": {
                    "type": "integer",
                    "description": "Number of days to look back",
                    "default": 30
                },
                "granularity": {
                    "type": "string",
                    "enum": ["DAILY", "MONTHLY", "HOURLY"],
                    "default": "DAILY"
                }
            }
        }
    """
    if aws_client is None:
        aws_client = AWSClient()

    ce_client = aws_client.get_client("ce")

    # Calculate date range
    if end_date is None:
        end = datetime.utcnow().date()
    else:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date is None:
        start = end - timedelta(days=days_back)
    else:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()

    # Default metrics
    if metrics is None:
        metrics = ["UnblendedCost"]

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": start.strftime("%Y-%m-%d"),
                "End": end.strftime("%Y-%m-%d")
            },
            Granularity=granularity,
            Metrics=metrics
        )

        # Parse results
        results_by_time = []
        total_cost = 0.0
        daily_costs = []
        currency = "USD"

        for result in response.get("ResultsByTime", []):
            start_date = result["TimePeriod"]["Start"]
            amount_data = result["Total"].get(metrics[0], {})
            amount = float(amount_data.get("Amount", 0))
            unit = amount_data.get("Unit", "USD")

            currency = unit
            total_cost += amount
            daily_costs.append(amount)

            results_by_time.append({
                "date": start_date,
                "amount": amount,
                "unit": unit
            })

        # Calculate summary statistics
        if daily_costs:
            summary = {
                "total": total_cost,
                "average_daily": total_cost / len(daily_costs),
                "min_daily": min(daily_costs),
                "max_daily": max(daily_costs)
            }
        else:
            summary = {
                "total": 0,
                "average_daily": 0,
                "min_daily": 0,
                "max_daily": 0
            }

        return {
            "time_period": {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            },
            "granularity": granularity,
            "total_cost": total_cost,
            "currency": currency,
            "results_by_time": results_by_time,
            "summary": summary
        }

    except Exception as e:
        return {
            "time_period": {
                "start": start.strftime("%Y-%m-%d") if start else "",
                "end": end.strftime("%Y-%m-%d") if end else ""
            },
            "granularity": granularity,
            "total_cost": 0,
            "currency": "USD",
            "results_by_time": [],
            "summary": {
                "total": 0,
                "average_daily": 0,
                "min_daily": 0,
                "max_daily": 0
            },
            "error": str(e)
        }


def get_cost_by_service(
    days_back: int = 30,
    top_n: int = 10,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get cost breakdown by AWS service.

    Args:
        days_back: Number of days to look back (default: 30)
        top_n: Number of top services to return (default: 10)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "time_period": {
                "start": str,
                "end": str
            },
            "total_cost": float,
            "currency": str,
            "services": [
                {
                    "service": str,
                    "cost": float,
                    "percentage": float
                }
            ]
        }

    Example:
        >>> costs = get_cost_by_service(days_back=30, top_n=5)
        >>> print("Top 5 most expensive services:")
        >>> for svc in costs['services']:
        ...     print(f"  {svc['service']}: ${svc['cost']:.2f} ({svc['percentage']:.1f}%)")

    Tool Schema (for LLMs):
        {
            "name": "get_cost_by_service",
            "description": "Get cost breakdown by AWS service",
            "parameters": {
                "days_back": {
                    "type": "integer",
                    "description": "Days to look back",
                    "default": 30
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top services",
                    "default": 10
                }
            }
        }
    """
    if aws_client is None:
        aws_client = AWSClient()

    ce_client = aws_client.get_client("ce")

    # Calculate date range
    end = datetime.utcnow().date()
    start = end - timedelta(days=days_back)

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": start.strftime("%Y-%m-%d"),
                "End": end.strftime("%Y-%m-%d")
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE"
                }
            ]
        )

        # Aggregate costs by service
        service_costs = {}
        total_cost = 0.0
        currency = "USD"

        for result in response.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                service = group["Keys"][0]
                cost_data = group["Metrics"]["UnblendedCost"]
                cost = float(cost_data["Amount"])
                currency = cost_data.get("Unit", "USD")

                if service in service_costs:
                    service_costs[service] += cost
                else:
                    service_costs[service] = cost

                total_cost += cost

        # Sort by cost and get top N
        sorted_services = sorted(
            service_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        # Build service list with percentages
        services = []
        for service, cost in sorted_services:
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            services.append({
                "service": service,
                "cost": cost,
                "percentage": percentage
            })

        return {
            "time_period": {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            },
            "total_cost": total_cost,
            "currency": currency,
            "services": services
        }

    except Exception as e:
        return {
            "time_period": {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            },
            "total_cost": 0,
            "currency": "USD",
            "services": [],
            "error": str(e)
        }


def detect_cost_anomalies(
    days_back: int = 30,
    threshold_percentage: float = 20.0,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Detect unusual spending patterns and cost anomalies.

    This tool analyzes daily cost patterns and identifies:
    - Days with unusually high costs
    - Sudden cost spikes
    - Services with unexpected spending

    Args:
        days_back: Number of days to analyze (default: 30)
        threshold_percentage: Percentage above average to flag as anomaly (default: 20%)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "time_period": {
                "start": str,
                "end": str
            },
            "baseline": {
                "average_daily_cost": float,
                "median_daily_cost": float
            },
            "anomalies": [
                {
                    "date": str,
                    "cost": float,
                    "deviation_percentage": float,
                    "severity": str  # "high", "medium", "low"
                }
            ],
            "total_anomalies": int,
            "recommendations": list[str]
        }

    Example:
        >>> anomalies = detect_cost_anomalies(days_back=30, threshold_percentage=25)
        >>> if anomalies['total_anomalies'] > 0:
        ...     print(f"⚠️ Found {anomalies['total_anomalies']} cost anomalies")
        ...     for anomaly in anomalies['anomalies']:
        ...         print(f"  {anomaly['date']}: ${anomaly['cost']:.2f} (+{anomaly['deviation_percentage']:.1f}%)")

    Tool Schema (for LLMs):
        {
            "name": "detect_cost_anomalies",
            "description": "Detect unusual spending patterns",
            "parameters": {
                "days_back": {
                    "type": "integer",
                    "description": "Days to analyze",
                    "default": 30
                },
                "threshold_percentage": {
                    "type": "number",
                    "description": "Percentage above average to flag",
                    "default": 20.0
                }
            }
        }
    """
    if aws_client is None:
        aws_client = AWSClient()

    # Get daily cost data
    cost_data = get_cost_and_usage(
        days_back=days_back,
        granularity="DAILY",
        aws_client=aws_client
    )

    if "error" in cost_data or not cost_data["results_by_time"]:
        return {
            "time_period": cost_data.get("time_period", {}),
            "baseline": {
                "average_daily_cost": 0,
                "median_daily_cost": 0
            },
            "anomalies": [],
            "total_anomalies": 0,
            "recommendations": [],
            "error": cost_data.get("error", "No data available")
        }

    # Calculate baseline
    daily_costs = [item["amount"] for item in cost_data["results_by_time"]]
    average_cost = sum(daily_costs) / len(daily_costs) if daily_costs else 0
    sorted_costs = sorted(daily_costs)
    median_cost = sorted_costs[len(sorted_costs) // 2] if sorted_costs else 0

    # Detect anomalies
    anomalies = []
    threshold = average_cost * (1 + threshold_percentage / 100)

    for item in cost_data["results_by_time"]:
        cost = item["amount"]
        date = item["date"]

        if cost > threshold:
            deviation = ((cost - average_cost) / average_cost * 100) if average_cost > 0 else 0

            # Determine severity
            if deviation > 50:
                severity = "high"
            elif deviation > 30:
                severity = "medium"
            else:
                severity = "low"

            anomalies.append({
                "date": date,
                "cost": cost,
                "deviation_percentage": deviation,
                "severity": severity
            })

    # Sort by deviation
    anomalies.sort(key=lambda x: x["deviation_percentage"], reverse=True)

    # Generate recommendations
    recommendations = []
    if anomalies:
        high_severity = [a for a in anomalies if a["severity"] == "high"]
        if high_severity:
            recommendations.append(f"⚠️ {len(high_severity)} day(s) with high cost anomalies detected - investigate immediately")

        recommendations.append(f"📊 Review service breakdown for dates: {', '.join([a['date'] for a in anomalies[:3]])}")
        recommendations.append("💡 Use get_cost_by_service() to identify which services caused the spike")
    else:
        recommendations.append("✅ No significant cost anomalies detected")

    return {
        "time_period": cost_data["time_period"],
        "baseline": {
            "average_daily_cost": average_cost,
            "median_daily_cost": median_cost
        },
        "anomalies": anomalies,
        "total_anomalies": len(anomalies),
        "recommendations": recommendations
    }


def get_cost_forecast(
    days_forward: int = 30,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get AWS cost forecast for future period.

    Uses AWS Cost Explorer's forecasting to predict future costs
    based on historical usage patterns.

    Args:
        days_forward: Number of days to forecast (default: 30, max: 90)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "time_period": {
                "start": str,
                "end": str
            },
            "forecast": {
                "predicted_cost": float,
                "prediction_interval_lower": float,
                "prediction_interval_upper": float,
                "currency": str
            },
            "daily_forecast": [
                {
                    "date": str,
                    "amount": float
                }
            ]
        }

    Example:
        >>> forecast = get_cost_forecast(days_forward=30)
        >>> predicted = forecast['forecast']['predicted_cost']
        >>> print(f"Predicted cost for next 30 days: ${predicted:.2f}")

    Tool Schema (for LLMs):
        {
            "name": "get_cost_forecast",
            "description": "Forecast future AWS costs",
            "parameters": {
                "days_forward": {
                    "type": "integer",
                    "description": "Days to forecast (max 90)",
                    "default": 30
                }
            }
        }
    """
    if aws_client is None:
        aws_client = AWSClient()

    ce_client = aws_client.get_client("ce")

    # Calculate forecast period (must start today or tomorrow)
    start = datetime.utcnow().date() + timedelta(days=1)
    end = start + timedelta(days=min(days_forward, 90))

    try:
        response = ce_client.get_cost_forecast(
            TimePeriod={
                "Start": start.strftime("%Y-%m-%d"),
                "End": end.strftime("%Y-%m-%d")
            },
            Metric="UNBLENDED_COST",
            Granularity="DAILY"
        )

        # Extract forecast data
        total_forecast = float(response.get("Total", {}).get("Amount", 0))
        currency = response.get("Total", {}).get("Unit", "USD")

        # Parse daily forecasts
        daily_forecast = []
        for result in response.get("ForecastResultsByTime", []):
            date = result["TimePeriod"]["Start"]
            amount = float(result["MeanValue"])

            daily_forecast.append({
                "date": date,
                "amount": amount
            })

        return {
            "time_period": {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            },
            "forecast": {
                "predicted_cost": total_forecast,
                "prediction_interval_lower": total_forecast * 0.9,  # Rough estimate
                "prediction_interval_upper": total_forecast * 1.1,  # Rough estimate
                "currency": currency
            },
            "daily_forecast": daily_forecast
        }

    except Exception as e:
        return {
            "time_period": {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            },
            "forecast": {
                "predicted_cost": 0,
                "prediction_interval_lower": 0,
                "prediction_interval_upper": 0,
                "currency": "USD"
            },
            "daily_forecast": [],
            "error": str(e)
        }
