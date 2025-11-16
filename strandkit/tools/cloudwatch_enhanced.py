"""
Enhanced CloudWatch tools for StrandKit.

Additional advanced CloudWatch functionality:
- get_log_insights: Run CloudWatch Logs Insights queries
- get_recent_errors: Quick helper to find errors across log groups
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import time
from strandkit.core.aws_client import AWSClient


def get_log_insights(
    log_group_names: List[str],
    query_string: str,
    start_minutes: int = 60,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Run CloudWatch Logs Insights query for advanced log analysis.

    CloudWatch Logs Insights allows you to run complex queries across logs
    using a SQL-like query language.

    Args:
        log_group_names: List of log group names to query
        query_string: Logs Insights query string
                     Example: "fields @timestamp, @message | filter @message like /ERROR/ | limit 20"
        start_minutes: How many minutes back to search (default: 60)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "log_groups": list[str],
            "query": str,
            "time_range": {
                "start": str,
                "end": str
            },
            "results": [
                {
                    "timestamp": str,
                    "fields": dict  # Field name -> value mapping
                }
            ],
            "statistics": {
                "records_matched": int,
                "records_scanned": int,
                "bytes_scanned": int
            },
            "status": str  # "Complete", "Running", "Failed"
        }

    Example:
        >>> # Find all ERROR messages in last hour
        >>> results = get_log_insights(
        ...     log_group_names=["/aws/lambda/my-function"],
        ...     query_string="fields @timestamp, @message | filter @message like /ERROR/ | limit 20",
        ...     start_minutes=60
        ... )
        >>> for result in results['results']:
        ...     print(result['fields']['@message'])

    Tool Schema (for LLMs):
        {
            "name": "get_log_insights",
            "description": "Run advanced CloudWatch Logs Insights queries",
            "parameters": {
                "log_group_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Log groups to query",
                    "required": true
                },
                "query_string": {
                    "type": "string",
                    "description": "Logs Insights query",
                    "required": true
                },
                "start_minutes": {
                    "type": "integer",
                    "description": "Minutes to look back",
                    "default": 60
                }
            }
        }
    """
    if aws_client is None:
        aws_client = AWSClient()

    logs_client = aws_client.get_client("logs")

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=start_minutes)

    # Convert to Unix timestamps
    start_timestamp = int(start_time.timestamp())
    end_timestamp = int(end_time.timestamp())

    try:
        # Start the query
        response = logs_client.start_query(
            logGroupNames=log_group_names,
            startTime=start_timestamp,
            endTime=end_timestamp,
            queryString=query_string
        )

        query_id = response["queryId"]

        # Poll for results (max 30 seconds)
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            result_response = logs_client.get_query_results(queryId=query_id)
            status = result_response["status"]

            if status == "Complete":
                break
            elif status in ["Failed", "Cancelled"]:
                return {
                    "log_groups": log_group_names,
                    "query": query_string,
                    "time_range": {
                        "start": start_time.isoformat() + "Z",
                        "end": end_time.isoformat() + "Z"
                    },
                    "results": [],
                    "statistics": {
                        "records_matched": 0,
                        "records_scanned": 0,
                        "bytes_scanned": 0
                    },
                    "status": status,
                    "error": f"Query {status.lower()}"
                }

            time.sleep(1)
            attempt += 1

        # Parse results
        results = []
        for result in result_response.get("results", []):
            fields = {}
            timestamp = None

            for field in result:
                field_name = field["field"]
                field_value = field["value"]

                if field_name == "@timestamp":
                    timestamp = field_value
                else:
                    fields[field_name] = field_value

            results.append({
                "timestamp": timestamp,
                "fields": fields
            })

        # Get statistics
        statistics = result_response.get("statistics", {})

        return {
            "log_groups": log_group_names,
            "query": query_string,
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "results": results,
            "statistics": {
                "records_matched": statistics.get("recordsMatched", 0),
                "records_scanned": statistics.get("recordsScanned", 0),
                "bytes_scanned": statistics.get("bytesScanned", 0)
            },
            "status": result_response["status"]
        }

    except Exception as e:
        return {
            "log_groups": log_group_names,
            "query": query_string,
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "results": [],
            "statistics": {
                "records_matched": 0,
                "records_scanned": 0,
                "bytes_scanned": 0
            },
            "status": "Failed",
            "error": str(e)
        }


def get_recent_errors(
    log_group_pattern: str = "/aws/lambda/",
    start_minutes: int = 60,
    limit: int = 50,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Quick helper to find recent errors across multiple log groups.

    This tool searches for ERROR, Exception, and FAILED patterns
    across log groups matching a pattern.

    Args:
        log_group_pattern: Pattern to match log group names (default: "/aws/lambda/")
        start_minutes: How many minutes back to search (default: 60)
        limit: Maximum number of errors to return (default: 50)
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "time_range": {
                "start": str,
                "end": str
            },
            "log_groups_scanned": int,
            "total_errors": int,
            "errors": [
                {
                    "timestamp": str,
                    "log_group": str,
                    "message": str
                }
            ]
        }

    Example:
        >>> # Find all Lambda errors in last hour
        >>> errors = get_recent_errors("/aws/lambda/", start_minutes=60)
        >>> print(f"Found {errors['total_errors']} errors across {errors['log_groups_scanned']} functions")
        >>> for err in errors['errors'][:5]:
        ...     print(f"  [{err['timestamp']}] {err['message'][:80]}")

    Tool Schema (for LLMs):
        {
            "name": "get_recent_errors",
            "description": "Find recent errors across log groups",
            "parameters": {
                "log_group_pattern": {
                    "type": "string",
                    "description": "Log group name pattern",
                    "default": "/aws/lambda/"
                },
                "start_minutes": {
                    "type": "integer",
                    "description": "Minutes to look back",
                    "default": 60
                }
            }
        }
    """
    if aws_client is None:
        aws_client = AWSClient()

    logs_client = aws_client.get_client("logs")

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=start_minutes)

    try:
        # List log groups matching pattern
        log_groups = []
        paginator = logs_client.get_paginator('describe_log_groups')

        for page in paginator.paginate(logGroupNamePrefix=log_group_pattern):
            for group in page['logGroups']:
                log_groups.append(group['logGroupName'])
                if len(log_groups) >= 10:  # Limit to 10 log groups to avoid timeouts
                    break
            if len(log_groups) >= 10:
                break

        if not log_groups:
            return {
                "time_range": {
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z"
                },
                "log_groups_scanned": 0,
                "total_errors": 0,
                "errors": [],
                "warning": f"No log groups found matching pattern '{log_group_pattern}'"
            }

        # Run Logs Insights query to find errors
        query = f"""fields @timestamp, @logStream, @message
            | filter @message like /ERROR/ or @message like /Exception/ or @message like /FAILED/
            | sort @timestamp desc
            | limit {limit}
        """

        insights_result = get_log_insights(
            log_group_names=log_groups,
            query_string=query,
            start_minutes=start_minutes,
            aws_client=aws_client
        )

        # Parse results
        errors = []
        for result in insights_result.get("results", []):
            fields = result.get("fields", {})
            errors.append({
                "timestamp": result.get("timestamp", ""),
                "log_group": fields.get("@logStream", "").split("/")[0] if "@logStream" in fields else "unknown",
                "message": fields.get("@message", "")
            })

        return {
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "log_groups_scanned": len(log_groups),
            "total_errors": len(errors),
            "errors": errors
        }

    except Exception as e:
        return {
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "log_groups_scanned": 0,
            "total_errors": 0,
            "errors": [],
            "error": str(e)
        }
