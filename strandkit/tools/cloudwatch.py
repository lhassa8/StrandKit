"""
CloudWatch tools for StrandKit.

This module provides tools for querying CloudWatch Logs and Metrics:
- get_lambda_logs: Retrieve and parse Lambda function logs
- get_metric: Query CloudWatch metrics with automatic statistics
- get_log_insights: Run CloudWatch Logs Insights queries for advanced log analysis
- get_recent_errors: Quick helper to find recent errors across log groups

All tools return structured JSON that's easy for LLMs to process.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from strandkit.core.aws_client import AWSClient


def get_lambda_logs(
    function_name: str,
    start_minutes: int = 60,
    filter_pattern: Optional[str] = None,
    limit: int = 100,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Retrieve CloudWatch logs for a Lambda function.

    This tool fetches recent logs from a Lambda function's CloudWatch log group,
    parses them into structured format, and returns them sorted by timestamp.

    Args:
        function_name: Name of the Lambda function (without '/aws/lambda/' prefix)
        start_minutes: How many minutes back to search (default: 60)
        filter_pattern: Optional CloudWatch Logs filter pattern
                       Example: "ERROR" or "?ERROR ?Exception ?error"
        limit: Maximum number of log events to return (default: 100)
        aws_client: Optional AWSClient instance (creates new one if None)

    Returns:
        Dictionary containing:
        {
            "function_name": str,
            "log_group": str,
            "time_range": {
                "start": str (ISO format),
                "end": str (ISO format)
            },
            "total_events": int,
            "events": [
                {
                    "timestamp": str (ISO format),
                    "message": str,
                    "stream": str
                },
                ...
            ],
            "has_errors": bool,
            "error_count": int
        }

    Example:
        >>> logs = get_lambda_logs("my-api-function", start_minutes=30)
        >>> print(f"Found {logs['total_events']} log entries")
        >>> for event in logs['events']:
        ...     if 'ERROR' in event['message']:
        ...         print(event['message'])

    Tool Schema (for LLMs):
        {
            "name": "get_lambda_logs",
            "description": "Retrieve CloudWatch logs for a Lambda function",
            "parameters": {
                "function_name": {
                    "type": "string",
                    "description": "Lambda function name",
                    "required": true
                },
                "start_minutes": {
                    "type": "integer",
                    "description": "Minutes to look back",
                    "default": 60
                },
                "filter_pattern": {
                    "type": "string",
                    "description": "CloudWatch Logs filter pattern",
                    "required": false
                }
            }
        }
    """
    # Create AWS client if not provided
    if aws_client is None:
        aws_client = AWSClient()

    logs_client = aws_client.get_client("logs")

    # Build log group name (Lambda convention)
    log_group = f"/aws/lambda/{function_name}"

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=start_minutes)

    # Convert to Unix timestamps in milliseconds (CloudWatch requirement)
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)

    try:
        # Build filter_log_events parameters
        params = {
            "logGroupName": log_group,
            "startTime": start_timestamp,
            "endTime": end_timestamp,
            "limit": limit,
        }

        # Add filter pattern if provided
        if filter_pattern:
            params["filterPattern"] = filter_pattern

        # Query CloudWatch Logs
        response = logs_client.filter_log_events(**params)

        # Parse events into structured format
        events = []
        error_count = 0

        for event in response.get("events", []):
            # Convert timestamp from milliseconds to ISO format
            timestamp_ms = event["timestamp"]
            event_time = datetime.utcfromtimestamp(timestamp_ms / 1000)

            message = event["message"]
            stream = event.get("logStreamName", "")

            events.append({
                "timestamp": event_time.isoformat() + "Z",
                "message": message,
                "stream": stream
            })

            # Count errors (look for common error indicators)
            message_upper = message.upper()
            if any(keyword in message_upper for keyword in ["ERROR", "EXCEPTION", "FAILED", "FATAL"]):
                error_count += 1

        # Build response
        return {
            "function_name": function_name,
            "log_group": log_group,
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "total_events": len(events),
            "events": events,
            "has_errors": error_count > 0,
            "error_count": error_count
        }

    except logs_client.exceptions.ResourceNotFoundException:
        # Log group doesn't exist
        return {
            "function_name": function_name,
            "log_group": log_group,
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "total_events": 0,
            "events": [],
            "has_errors": False,
            "error_count": 0,
            "warning": f"Log group '{log_group}' not found. The Lambda function may not exist or has no logs."
        }

    except Exception as e:
        # Handle other errors
        return {
            "function_name": function_name,
            "log_group": log_group,
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "total_events": 0,
            "events": [],
            "has_errors": False,
            "error_count": 0,
            "error": str(e)
        }


def get_metric(
    namespace: str,
    metric_name: str,
    dimensions: Optional[Dict[str, str]] = None,
    statistic: str = "Average",
    period: int = 300,
    start_minutes: int = 120,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Query CloudWatch metrics.

    This tool fetches metric data from CloudWatch and returns it in a
    structured, time-series format that's easy to analyze.

    Args:
        namespace: CloudWatch namespace (e.g., "AWS/Lambda", "AWS/DynamoDB")
        metric_name: Name of the metric (e.g., "Errors", "Duration", "Invocations")
        dimensions: Optional metric dimensions
                   Example: {"FunctionName": "my-function"}
        statistic: Statistic to compute (Average, Sum, Maximum, Minimum, SampleCount)
        period: Period in seconds for each datapoint (default: 300 = 5 minutes)
        start_minutes: How many minutes back to query (default: 120 = 2 hours)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "namespace": str,
            "metric_name": str,
            "dimensions": dict,
            "statistic": str,
            "time_range": {
                "start": str (ISO format),
                "end": str (ISO format)
            },
            "datapoints": [
                {
                    "timestamp": str (ISO format),
                    "value": float,
                    "unit": str
                },
                ...
            ],
            "summary": {
                "min": float,
                "max": float,
                "avg": float,
                "count": int
            }
        }

    Example:
        >>> # Get Lambda error count over last 2 hours
        >>> errors = get_metric(
        ...     namespace="AWS/Lambda",
        ...     metric_name="Errors",
        ...     dimensions={"FunctionName": "my-api"},
        ...     statistic="Sum",
        ...     period=300
        ... )
        >>> if errors['summary']['max'] > 10:
        ...     print("High error rate detected!")

    Tool Schema (for LLMs):
        {
            "name": "get_metric",
            "description": "Query CloudWatch metrics",
            "parameters": {
                "namespace": {
                    "type": "string",
                    "description": "CloudWatch namespace",
                    "required": true
                },
                "metric_name": {
                    "type": "string",
                    "description": "Metric name",
                    "required": true
                },
                "dimensions": {
                    "type": "object",
                    "description": "Metric dimensions",
                    "required": false
                },
                "statistic": {
                    "type": "string",
                    "enum": ["Average", "Sum", "Maximum", "Minimum", "SampleCount"],
                    "default": "Average"
                },
                "period": {
                    "type": "integer",
                    "description": "Period in seconds",
                    "default": 300
                },
                "start_minutes": {
                    "type": "integer",
                    "description": "Minutes to look back",
                    "default": 120
                }
            }
        }
    """
    # Create AWS client if not provided
    if aws_client is None:
        aws_client = AWSClient()

    cloudwatch_client = aws_client.get_client("cloudwatch")

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=start_minutes)

    # Build dimensions array (CloudWatch API format)
    dimensions_array = []
    if dimensions:
        dimensions_array = [
            {"Name": key, "Value": value}
            for key, value in dimensions.items()
        ]

    try:
        # Query CloudWatch Metrics
        response = cloudwatch_client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions_array,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic]
        )

        # Parse datapoints
        datapoints = []
        values = []

        for point in response.get("Datapoints", []):
            timestamp = point["Timestamp"]
            value = point.get(statistic, 0)
            unit = point.get("Unit", "None")

            datapoints.append({
                "timestamp": timestamp.isoformat() + "Z" if hasattr(timestamp, 'isoformat') else str(timestamp),
                "value": value,
                "unit": unit
            })
            values.append(value)

        # Sort datapoints by timestamp
        datapoints.sort(key=lambda x: x["timestamp"])

        # Calculate summary statistics
        if values:
            summary = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values)
            }
        else:
            summary = {
                "min": 0,
                "max": 0,
                "avg": 0,
                "count": 0
            }

        # Build response
        return {
            "namespace": namespace,
            "metric_name": metric_name,
            "dimensions": dimensions or {},
            "statistic": statistic,
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "datapoints": datapoints,
            "summary": summary
        }

    except Exception as e:
        # Handle errors
        return {
            "namespace": namespace,
            "metric_name": metric_name,
            "dimensions": dimensions or {},
            "statistic": statistic,
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "datapoints": [],
            "summary": {
                "min": 0,
                "max": 0,
                "avg": 0,
                "count": 0
            },
            "error": str(e)
        }
