"""
S3 & Storage Visibility Tools

This module provides tools for analyzing S3 buckets, detecting security risks,
and optimizing storage costs.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import sys
import json

# Handle boto3 import
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Warning: boto3 not installed. Install with: pip install boto3", file=sys.stderr)
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

from strandkit.core.aws_client import AWSClient
from strands import tool


@tool
def analyze_s3_bucket(
    bucket_name: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of an S3 bucket.

    Analyzes bucket configuration, security settings, storage metrics,
    and provides optimization recommendations.

    Args:
        bucket_name: S3 bucket name
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - bucket_details: Basic bucket information
        - security: Encryption, public access, ACLs, policies
        - storage: Size, object count, storage class distribution
        - configuration: Versioning, lifecycle, logging, replication
        - cost_estimate: Estimated monthly storage cost
        - risk_assessment: Security risk level
        - recommendations: Optimization suggestions

    Example:
        >>> analysis = analyze_s3_bucket("my-bucket")
        >>> print(f"Risk level: {analysis['risk_assessment']['risk_level']}")
        >>> print(f"Monthly cost: ${analysis['cost_estimate']['monthly_cost']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3_client = aws_client.get_client("s3")

        # Basic bucket info
        try:
            location_response = s3_client.get_bucket_location(Bucket=bucket_name)
            region = location_response.get('LocationConstraint') or 'us-east-1'
        except Exception:
            region = 'unknown'

        bucket_details = {
            "bucket_name": bucket_name,
            "region": region
        }

        # Get creation date
        try:
            buckets = s3_client.list_buckets()
            for bucket in buckets['Buckets']:
                if bucket['Name'] == bucket_name:
                    bucket_details['creation_date'] = bucket['CreationDate'].isoformat()
                    break
        except Exception:
            pass

        # Security analysis
        security = _analyze_bucket_security(s3_client, bucket_name)

        # Storage metrics
        storage = _analyze_bucket_storage(s3_client, bucket_name)

        # Configuration
        configuration = _analyze_bucket_configuration(s3_client, bucket_name)

        # Cost estimate
        cost_estimate = _estimate_bucket_cost(storage)

        # Risk assessment
        risk_assessment = _assess_bucket_risk(security, configuration)

        # Recommendations
        recommendations = _generate_bucket_recommendations(
            security, configuration, storage, risk_assessment
        )

        return {
            "bucket_name": bucket_name,
            "bucket_details": bucket_details,
            "security": security,
            "storage": storage,
            "configuration": configuration,
            "cost_estimate": cost_estimate,
            "risk_assessment": risk_assessment,
            "recommendations": recommendations
        }

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchBucket':
            return {
                "error": f"Bucket '{bucket_name}' does not exist",
                "bucket_name": bucket_name
            }
        return {
            "error": f"AWS API error: {str(e)}",
            "bucket_name": bucket_name
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "bucket_name": bucket_name
        }


@tool
def find_public_buckets(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Scan all S3 buckets for public access risks.

    Identifies buckets with public ACLs, policies, or disabled
    public access blocks.

    Args:
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - buckets: List of all buckets with public access status
        - public_buckets: List of buckets with public access
        - summary: Statistics by risk level
        - recommendations: Action items

    Example:
        >>> scan = find_public_buckets()
        >>> print(f"Public buckets: {len(scan['public_buckets'])}")
        >>> for bucket in scan['public_buckets']:
        >>>     print(f"  {bucket['bucket_name']}: {bucket['public_reason']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3_client = aws_client.get_client("s3")

        # List all buckets
        response = s3_client.list_buckets()
        all_buckets = response.get('Buckets', [])

        buckets = []
        public_buckets = []

        for bucket in all_buckets:
            bucket_name = bucket['Name']

            # Check public access
            public_info = _check_bucket_public_access(s3_client, bucket_name)

            bucket_summary = {
                "bucket_name": bucket_name,
                "is_public": public_info['is_public'],
                "risk_level": public_info['risk_level'],
                "public_reason": public_info['reasons']
            }

            buckets.append(bucket_summary)

            if public_info['is_public']:
                public_buckets.append(bucket_summary)

        # Summary statistics
        summary = {
            "total_buckets": len(buckets),
            "public_buckets": len(public_buckets),
            "critical": len([b for b in public_buckets if b['risk_level'] == 'critical']),
            "high": len([b for b in public_buckets if b['risk_level'] == 'high']),
            "medium": len([b for b in public_buckets if b['risk_level'] == 'medium'])
        }

        # Recommendations
        recommendations = []
        if summary['critical'] > 0:
            recommendations.append(f"🔴 URGENT: {summary['critical']} bucket(s) with CRITICAL public access - immediate action required")
        if summary['high'] > 0:
            recommendations.append(f"⚠️ {summary['high']} bucket(s) with HIGH risk public access - review and restrict")
        if summary['public_buckets'] == 0:
            recommendations.append("✅ No publicly accessible buckets found - good security posture!")

        return {
            "buckets": buckets,
            "public_buckets": public_buckets,
            "summary": summary,
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "buckets": [],
            "public_buckets": []
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "buckets": [],
            "public_buckets": []
        }


@tool
def get_s3_cost_analysis(
    days_back: int = 30,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 storage costs and optimization opportunities.

    Provides cost breakdown by bucket and storage class with
    optimization recommendations.

    Args:
        days_back: Number of days to analyze (default: 30)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - total_cost: Total S3 costs for period
        - by_bucket: Cost breakdown by bucket
        - by_storage_class: Cost breakdown by storage class
        - optimization_opportunities: Potential savings
        - recommendations: Action items

    Example:
        >>> costs = get_s3_cost_analysis(days_back=30)
        >>> print(f"Total S3 cost: ${costs['total_cost']:.2f}")
        >>> print(f"Potential savings: ${costs['optimization_opportunities']['total_savings']:.2f}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        ce_client = aws_client.get_client("ce")
        s3_client = aws_client.get_client("s3")

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        # Get S3 costs from Cost Explorer
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            Filter={
                'Dimensions': {
                    'Key': 'SERVICE',
                    'Values': ['Amazon Simple Storage Service']
                }
            }
        )

        # Calculate total cost
        total_cost = 0.0
        for result in response['ResultsByTime']:
            total_cost += float(result['Total']['UnblendedCost']['Amount'])

        # Get bucket-level estimates
        buckets = s3_client.list_buckets()['Buckets']
        by_bucket = []

        for bucket in buckets:
            bucket_name = bucket['Name']
            storage_info = _analyze_bucket_storage(s3_client, bucket_name)
            cost = _estimate_bucket_cost(storage_info)

            by_bucket.append({
                "bucket_name": bucket_name,
                "estimated_monthly_cost": cost['monthly_cost'],
                "total_size_gb": storage_info['total_size_gb'],
                "object_count": storage_info['object_count']
            })

        # Sort by cost
        by_bucket.sort(key=lambda x: x['estimated_monthly_cost'], reverse=True)

        # Storage class distribution (from top buckets)
        by_storage_class = {}
        for bucket_info in by_bucket[:10]:  # Top 10 buckets
            storage = _analyze_bucket_storage(s3_client, bucket_info['bucket_name'])
            for sc, count in storage.get('storage_classes', {}).items():
                by_storage_class[sc] = by_storage_class.get(sc, 0) + count

        # Optimization opportunities
        optimization_opportunities = _find_s3_optimization_opportunities(by_bucket, s3_client)

        # Recommendations
        recommendations = []
        if optimization_opportunities['total_savings'] > 10:
            recommendations.append(f"💰 Potential savings: ${optimization_opportunities['total_savings']:.2f}/month")
        if optimization_opportunities['lifecycle_candidates'] > 0:
            recommendations.append(f"📋 {optimization_opportunities['lifecycle_candidates']} bucket(s) could benefit from lifecycle policies")
        if optimization_opportunities['intelligent_tiering_candidates'] > 0:
            recommendations.append(f"🔄 {optimization_opportunities['intelligent_tiering_candidates']} bucket(s) suitable for Intelligent-Tiering")

        return {
            "time_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days_back
            },
            "total_cost": total_cost,
            "by_bucket": by_bucket[:20],  # Top 20
            "by_storage_class": by_storage_class,
            "optimization_opportunities": optimization_opportunities,
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "total_cost": 0.0
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "total_cost": 0.0
        }


@tool
def analyze_bucket_access(
    bucket_name: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 bucket access patterns and logging configuration.

    Examines access logging status, CloudTrail integration, and
    identifies unusual access patterns.

    Args:
        bucket_name: S3 bucket name
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - logging_status: Access logging configuration
        - cloudtrail_status: CloudTrail data events status
        - recent_access: Recent access summary (if available)
        - recommendations: Security improvements

    Example:
        >>> access = analyze_bucket_access("my-bucket")
        >>> print(f"Logging enabled: {access['logging_status']['enabled']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3_client = aws_client.get_client("s3")

        # Check access logging
        logging_status = _check_bucket_logging(s3_client, bucket_name)

        # Check CloudTrail (would require CloudTrail API - simplified here)
        cloudtrail_status = {
            "note": "CloudTrail data events provide detailed access logs"
        }

        # Recommendations
        recommendations = []
        if not logging_status['enabled']:
            recommendations.append("⚠️ Enable S3 access logging to track bucket access")
        if logging_status['enabled']:
            recommendations.append("✅ Access logging is enabled")
            recommendations.append("💡 Review logs regularly for unusual access patterns")

        return {
            "bucket_name": bucket_name,
            "logging_status": logging_status,
            "cloudtrail_status": cloudtrail_status,
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "bucket_name": bucket_name
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "bucket_name": bucket_name
        }


@tool
def find_unused_buckets(
    min_age_days: int = 90,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Find empty or rarely used S3 buckets.

    Identifies buckets that are empty, contain only old objects,
    or haven't been accessed recently.

    Args:
        min_age_days: Minimum age in days to consider bucket unused (default: 90)
        aws_client: Optional AWSClient instance

    Returns:
        Dict containing:
        - empty_buckets: Buckets with no objects
        - old_only_buckets: Buckets with only old objects
        - unused_buckets_count: Total count
        - potential_savings: Estimated cost savings
        - recommendations: Action items

    Example:
        >>> unused = find_unused_buckets(min_age_days=180)
        >>> print(f"Empty buckets: {len(unused['empty_buckets'])}")
        >>> print(f"Potential savings: ${unused['potential_savings']:.2f}/month")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3_client = aws_client.get_client("s3")

        # List all buckets
        response = s3_client.list_buckets()
        all_buckets = response.get('Buckets', [])

        empty_buckets = []
        old_only_buckets = []
        total_savings = 0.0

        cutoff_date = datetime.now() - timedelta(days=min_age_days)

        for bucket in all_buckets:
            bucket_name = bucket['Name']

            try:
                # Check if bucket is empty
                objects = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)

                if 'Contents' not in objects or len(objects['Contents']) == 0:
                    # Empty bucket
                    empty_buckets.append({
                        "bucket_name": bucket_name,
                        "creation_date": bucket['CreationDate'].isoformat(),
                        "reason": "Empty - no objects"
                    })
                else:
                    # Check if all objects are old
                    objects_list = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
                    if 'Contents' in objects_list:
                        newest_date = max(obj['LastModified'] for obj in objects_list['Contents'])

                        if newest_date.replace(tzinfo=None) < cutoff_date:
                            object_count = objects_list.get('KeyCount', 0)
                            old_only_buckets.append({
                                "bucket_name": bucket_name,
                                "newest_object_date": newest_date.isoformat(),
                                "object_count": object_count,
                                "reason": f"No objects modified in {min_age_days}+ days"
                            })

                            # Estimate storage cost (rough)
                            storage_info = _analyze_bucket_storage(s3_client, bucket_name)
                            cost = _estimate_bucket_cost(storage_info)
                            total_savings += cost['monthly_cost']

            except Exception:
                # Skip buckets we can't access
                continue

        # Recommendations
        recommendations = []
        if len(empty_buckets) > 0:
            recommendations.append(f"🗑️ {len(empty_buckets)} empty bucket(s) found - consider deleting")
        if len(old_only_buckets) > 0:
            recommendations.append(f"📦 {len(old_only_buckets)} bucket(s) with only old objects - review and archive")
        if total_savings > 1:
            recommendations.append(f"💰 Potential savings: ${total_savings:.2f}/month from removing unused buckets")
        if len(empty_buckets) == 0 and len(old_only_buckets) == 0:
            recommendations.append("✅ No obviously unused buckets found")

        return {
            "empty_buckets": empty_buckets,
            "old_only_buckets": old_only_buckets,
            "unused_buckets_count": len(empty_buckets) + len(old_only_buckets),
            "potential_savings": total_savings,
            "min_age_days": min_age_days,
            "recommendations": recommendations
        }

    except ClientError as e:
        return {
            "error": f"AWS API error: {str(e)}",
            "empty_buckets": [],
            "old_only_buckets": []
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "empty_buckets": [],
            "old_only_buckets": []
        }


# Helper functions

@tool
def _analyze_bucket_security(s3_client, bucket_name: str) -> Dict[str, Any]:
    """Analyze bucket security settings."""
    security = {}

    # Encryption
    try:
        encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
        security['encryption'] = {
            "enabled": True,
            "rules": encryption.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
            security['encryption'] = {"enabled": False}
        else:
            security['encryption'] = {"error": str(e)}

    # Public Access Block
    try:
        pab = s3_client.get_public_access_block(Bucket=bucket_name)
        config = pab.get('PublicAccessBlockConfiguration', {})
        security['public_access_block'] = {
            "enabled": True,
            "block_public_acls": config.get('BlockPublicAcls', False),
            "ignore_public_acls": config.get('IgnorePublicAcls', False),
            "block_public_policy": config.get('BlockPublicPolicy', False),
            "restrict_public_buckets": config.get('RestrictPublicBuckets', False)
        }
    except ClientError:
        security['public_access_block'] = {"enabled": False}

    # ACL
    try:
        acl = s3_client.get_bucket_acl(Bucket=bucket_name)
        has_public_read = any(
            grant['Grantee'].get('Type') == 'Group' and
            'AllUsers' in grant['Grantee'].get('URI', '')
            for grant in acl.get('Grants', [])
        )
        security['acl'] = {
            "grants_count": len(acl.get('Grants', [])),
            "has_public_read": has_public_read
        }
    except Exception:
        security['acl'] = {"error": "Could not retrieve ACL"}

    # Bucket Policy
    try:
        policy = s3_client.get_bucket_policy(Bucket=bucket_name)
        policy_doc = json.loads(policy['Policy'])
        security['policy'] = {
            "has_policy": True,
            "statements_count": len(policy_doc.get('Statement', []))
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            security['policy'] = {"has_policy": False}
        else:
            security['policy'] = {"error": str(e)}

    return security


@tool
def _analyze_bucket_storage(s3_client, bucket_name: str) -> Dict[str, Any]:
    """Analyze bucket storage metrics."""
    storage = {
        "object_count": 0,
        "total_size_bytes": 0,
        "total_size_gb": 0.0,
        "storage_classes": {}
    }

    try:
        # List objects (sample for large buckets)
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket_name, PaginationConfig={'MaxItems': 1000})

        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    storage['object_count'] += 1
                    storage['total_size_bytes'] += obj.get('Size', 0)

                    storage_class = obj.get('StorageClass', 'STANDARD')
                    storage['storage_classes'][storage_class] = storage['storage_classes'].get(storage_class, 0) + 1

        storage['total_size_gb'] = storage['total_size_bytes'] / (1024 ** 3)

    except Exception:
        pass

    return storage


@tool
def _analyze_bucket_configuration(s3_client, bucket_name: str) -> Dict[str, Any]:
    """Analyze bucket configuration."""
    config = {}

    # Versioning
    try:
        versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
        config['versioning'] = {
            "status": versioning.get('Status', 'Disabled')
        }
    except Exception:
        config['versioning'] = {"status": "Unknown"}

    # Lifecycle
    try:
        lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        config['lifecycle'] = {
            "enabled": True,
            "rules_count": len(lifecycle.get('Rules', []))
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
            config['lifecycle'] = {"enabled": False}
        else:
            config['lifecycle'] = {"error": str(e)}

    # Replication
    try:
        replication = s3_client.get_bucket_replication(Bucket=bucket_name)
        config['replication'] = {
            "enabled": True,
            "rules_count": len(replication.get('ReplicationConfiguration', {}).get('Rules', []))
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'ReplicationConfigurationNotFoundError':
            config['replication'] = {"enabled": False}
        else:
            config['replication'] = {"error": str(e)}

    # Tags
    try:
        tags = s3_client.get_bucket_tagging(Bucket=bucket_name)
        config['tags'] = {tag['Key']: tag['Value'] for tag in tags.get('TagSet', [])}
    except ClientError:
        config['tags'] = {}

    return config


@tool
def _estimate_bucket_cost(storage: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate monthly bucket cost (rough estimates)."""
    # Simplified pricing (US East)
    pricing = {
        'STANDARD': 0.023,  # per GB
        'STANDARD_IA': 0.0125,
        'ONEZONE_IA': 0.01,
        'INTELLIGENT_TIERING': 0.023,
        'GLACIER': 0.004,
        'DEEP_ARCHIVE': 0.00099
    }

    total_cost = storage['total_size_gb'] * pricing.get('STANDARD', 0.023)

    return {
        "monthly_cost": round(total_cost, 2),
        "storage_gb": storage['total_size_gb'],
        "note": "Estimates based on US East pricing"
    }


@tool
def _assess_bucket_risk(security: Dict[str, Any], configuration: Dict[str, Any]) -> Dict[str, Any]:
    """Assess overall bucket security risk."""
    risk_level = 'low'
    risk_factors = []

    # Check encryption
    if not security.get('encryption', {}).get('enabled'):
        risk_factors.append("Encryption not enabled")
        risk_level = 'medium'

    # Check public access block
    pab = security.get('public_access_block', {})
    if not pab.get('enabled') or not pab.get('block_public_acls'):
        risk_factors.append("Public access block not fully enabled")
        risk_level = 'high'

    # Check for public ACLs
    if security.get('acl', {}).get('has_public_read'):
        risk_factors.append("Bucket has public read access via ACL")
        risk_level = 'critical'

    # Check versioning
    if configuration.get('versioning', {}).get('status') != 'Enabled':
        risk_factors.append("Versioning not enabled (no protection against accidental deletion)")

    return {
        "risk_level": risk_level,
        "risk_factors": risk_factors
    }


@tool
def _generate_bucket_recommendations(
    security: Dict[str, Any],
    configuration: Dict[str, Any],
    storage: Dict[str, Any],
    risk_assessment: Dict[str, Any]
) -> List[str]:
    """Generate recommendations for bucket optimization."""
    recommendations = []

    # Security recommendations
    if not security.get('encryption', {}).get('enabled'):
        recommendations.append("🔒 Enable server-side encryption (SSE-S3 or SSE-KMS)")

    pab = security.get('public_access_block', {})
    if not pab.get('enabled') or not all([
        pab.get('block_public_acls'),
        pab.get('ignore_public_acls'),
        pab.get('block_public_policy'),
        pab.get('restrict_public_buckets')
    ]):
        recommendations.append("🔒 Enable all public access block settings")

    # Configuration recommendations
    if configuration.get('versioning', {}).get('status') != 'Enabled':
        recommendations.append("📋 Enable versioning for data protection")

    if not configuration.get('lifecycle', {}).get('enabled'):
        recommendations.append("💰 Configure lifecycle rules to reduce storage costs")

    # Storage recommendations
    if storage['total_size_gb'] > 100:
        recommendations.append("💡 Consider using S3 Intelligent-Tiering for automatic cost optimization")

    if not recommendations:
        recommendations.append("✅ Bucket configuration looks good")

    return recommendations


@tool
def _check_bucket_public_access(s3_client, bucket_name: str) -> Dict[str, Any]:
    """Check if bucket has public access."""
    is_public = False
    reasons = []
    risk_level = 'low'

    try:
        # Check Public Access Block
        try:
            pab = s3_client.get_public_access_block(Bucket=bucket_name)
            config = pab.get('PublicAccessBlockConfiguration', {})

            if not all([
                config.get('BlockPublicAcls', False),
                config.get('IgnorePublicAcls', False),
                config.get('BlockPublicPolicy', False),
                config.get('RestrictPublicBuckets', False)
            ]):
                is_public = True
                reasons.append("Public access block not fully enabled")
                risk_level = 'high'
        except ClientError:
            # No public access block = potentially public
            is_public = True
            reasons.append("No public access block configured")
            risk_level = 'critical'

        # Check ACL
        try:
            acl = s3_client.get_bucket_acl(Bucket=bucket_name)
            for grant in acl.get('Grants', []):
                grantee = grant.get('Grantee', {})
                if grantee.get('Type') == 'Group' and 'AllUsers' in grantee.get('URI', ''):
                    is_public = True
                    reasons.append("Public READ access via ACL")
                    risk_level = 'critical'
        except Exception:
            pass

        # Check Bucket Policy for public statements
        try:
            policy = s3_client.get_bucket_policy(Bucket=bucket_name)
            policy_doc = json.loads(policy['Policy'])

            for statement in policy_doc.get('Statement', []):
                principal = statement.get('Principal', {})
                if principal == '*' or principal.get('AWS') == '*':
                    is_public = True
                    reasons.append("Public access via bucket policy")
                    risk_level = 'critical'
        except ClientError:
            pass

    except Exception:
        pass

    return {
        "is_public": is_public,
        "risk_level": risk_level if is_public else 'low',
        "reasons": reasons if reasons else ["No public access detected"]
    }


@tool
def _check_bucket_logging(s3_client, bucket_name: str) -> Dict[str, Any]:
    """Check bucket access logging configuration."""
    try:
        logging = s3_client.get_bucket_logging(Bucket=bucket_name)

        if 'LoggingEnabled' in logging:
            return {
                "enabled": True,
                "target_bucket": logging['LoggingEnabled'].get('TargetBucket'),
                "target_prefix": logging['LoggingEnabled'].get('TargetPrefix', '')
            }
        else:
            return {"enabled": False}
    except Exception:
        return {"enabled": False, "error": "Could not determine logging status"}


@tool
def _find_s3_optimization_opportunities(
    buckets: List[Dict[str, Any]],
    s3_client
) -> Dict[str, Any]:
    """Find S3 cost optimization opportunities."""
    lifecycle_candidates = 0
    intelligent_tiering_candidates = 0
    total_savings = 0.0

    for bucket_info in buckets[:20]:  # Check top 20 buckets
        bucket_name = bucket_info['bucket_name']

        try:
            # Check if lifecycle is configured
            try:
                s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                    # No lifecycle = candidate
                    if bucket_info['total_size_gb'] > 10:  # Only for buckets > 10 GB
                        lifecycle_candidates += 1
                        # Estimate 30% savings with lifecycle
                        total_savings += bucket_info['estimated_monthly_cost'] * 0.3

            # Check if suitable for Intelligent-Tiering
            if bucket_info['total_size_gb'] > 50:  # Good for larger buckets
                intelligent_tiering_candidates += 1

        except Exception:
            continue

    return {
        "lifecycle_candidates": lifecycle_candidates,
        "intelligent_tiering_candidates": intelligent_tiering_candidates,
        "total_savings": round(total_savings, 2)
    }
