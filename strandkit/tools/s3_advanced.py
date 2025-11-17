"""
S3 Advanced Optimization Tools for StrandKit.

This module provides comprehensive S3 storage optimization:
- Storage class optimization (Standard → IA → Glacier)
- Lifecycle policy recommendations
- Versioning waste analysis
- Incomplete multipart upload cleanup
- Replication cost analysis
- Request cost optimization
- Large object identification

All tools follow consistent patterns:
- Accept simple, well-typed parameters
- Return structured JSON with consistent keys
- Include cost savings calculations
- Provide actionable recommendations
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from strandkit.core.aws_client import AWSClient
from strands import tool


# S3 Storage Pricing (us-east-1, per GB-month)
S3_STORAGE_PRICING = {
    'STANDARD': 0.023,
    'INTELLIGENT_TIERING': 0.0125,  # Frequent Access tier
    'STANDARD_IA': 0.0125,
    'ONEZONE_IA': 0.01,
    'GLACIER': 0.004,
    'GLACIER_IR': 0.004,
    'DEEP_ARCHIVE': 0.00099
}

# Request Pricing (per 1,000 requests)
S3_REQUEST_PRICING = {
    'PUT_POST_LIST': 0.005,  # PUT, COPY, POST, LIST requests
    'GET_SELECT': 0.0004,    # GET, SELECT requests
}


@tool
def analyze_s3_storage_classes(
    days_back: int = 90,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 storage classes and identify optimization opportunities.
    
    Note: This is a simplified implementation that analyzes bucket-level
    storage classes. Full object-level analysis would require S3 Inventory.
    
    Returns bucket recommendations for storage class transitions.
    """
    if aws_client is None:
        aws_client = AWSClient()
    
    try:
        s3 = aws_client.get_client('s3')
        cloudwatch = aws_client.get_client('cloudwatch')
        
        # Get all buckets
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        optimization_opportunities = []
        total_potential_savings = 0.0
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            
            try:
                # Get bucket location
                location = s3.get_bucket_location(Bucket=bucket_name)
                region = location.get('LocationConstraint') or 'us-east-1'
                
                # Get storage metrics from CloudWatch
                # Note: This requires S3 Storage Lens or manual tracking
                # For now, we'll provide recommendations based on best practices
                
                recommendation = {
                    'bucket_name': bucket_name,
                    'region': region,
                    'recommendations': []
                }
                
                # Check if lifecycle policy exists
                try:
                    s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                    has_lifecycle = True
                except Exception:
                    has_lifecycle = False
                    recommendation['recommendations'].append(
                        'No lifecycle policy - consider adding transitions to IA/Glacier'
                    )
                
                # Check if Intelligent-Tiering is enabled
                try:
                    intelligent_tiering = s3.get_bucket_intelligent_tiering_configuration(
                        Bucket=bucket_name,
                        Id='default'
                    )
                    has_intelligent_tiering = True
                except:
                    has_intelligent_tiering = False
                    recommendation['recommendations'].append(
                        'Consider Intelligent-Tiering for automatic cost optimization'
                    )
                
                if not has_lifecycle and not has_intelligent_tiering:
                    # Estimate potential savings (30-70% with proper lifecycle)
                    recommendation['potential_savings_percentage'] = '30-70%'
                    recommendation['recommendation'] = 'Implement lifecycle policy or Intelligent-Tiering'
                    optimization_opportunities.append(recommendation)
                
            except Exception as e:
                continue
        
        recommendations = []
        
        if optimization_opportunities:
            recommendations.append(
                f"Configure lifecycle policies for {len(optimization_opportunities)} buckets"
            )
            recommendations.append(
                "Transition data to IA after 30 days, Glacier after 90 days"
            )
        
        recommendations.append(
            "Use S3 Storage Lens for detailed object-level analysis"
        )
        
        recommendations.append(
            "Consider Intelligent-Tiering for unpredictable access patterns"
        )
        
        if not optimization_opportunities:
            recommendations.append(
                "✅ Storage class optimization appears well-configured"
            )
        
        return {
            'summary': {
                'total_buckets': len(buckets),
                'buckets_without_optimization': len(optimization_opportunities),
                'potential_savings': '30-70% with proper lifecycle policies'
            },
            'optimization_opportunities': optimization_opportunities,
            'recommendations': recommendations,
            'note': 'For detailed object-level analysis, enable S3 Inventory and Storage Lens'
        }
    
    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_lifecycle_policies(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 lifecycle policies and provide optimization recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()
    
    try:
        s3 = aws_client.get_client('s3')
        
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        buckets_with_lifecycle = []
        buckets_without_lifecycle = []
        lifecycle_recommendations = []
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            
            try:
                lifecycle_config = s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                rules = lifecycle_config.get('Rules', [])
                
                bucket_info = {
                    'bucket_name': bucket_name,
                    'rule_count': len(rules),
                    'rules': []
                }
                
                for rule in rules:
                    rule_info = {
                        'id': rule.get('ID', 'Unnamed'),
                        'status': rule.get('Status', 'Unknown'),
                        'transitions': [],
                        'expiration': None
                    }
                    
                    # Check transitions
                    for transition in rule.get('Transitions', []):
                        rule_info['transitions'].append({
                            'days': transition.get('Days'),
                            'storage_class': transition.get('StorageClass')
                        })
                    
                    # Check expiration
                    if 'Expiration' in rule:
                        rule_info['expiration'] = rule['Expiration'].get('Days')
                    
                    bucket_info['rules'].append(rule_info)
                
                buckets_with_lifecycle.append(bucket_info)

            except Exception:
                # No lifecycle configuration
                buckets_without_lifecycle.append({
                    'bucket_name': bucket_name,
                    'recommendation': 'Add lifecycle policy: 30d→IA, 90d→Glacier, 365d→Delete'
                })
        
        # Generate recommendations
        recommendations = []
        
        if buckets_without_lifecycle:
            recommendations.append(
                f"Add lifecycle policies to {len(buckets_without_lifecycle)} buckets"
            )
            recommendations.append(
                "Recommended policy: 30 days → Standard-IA, 90 days → Glacier"
            )
        
        recommendations.append(
            "Review existing policies for optimization opportunities"
        )
        
        recommendations.append(
            "Use noncurrent version expiration to clean up old versions"
        )
        
        if len(buckets_with_lifecycle) == len(buckets):
            recommendations.append(
                "✅ All buckets have lifecycle policies configured"
            )
        
        return {
            'summary': {
                'total_buckets': len(buckets),
                'with_lifecycle': len(buckets_with_lifecycle),
                'without_lifecycle': len(buckets_without_lifecycle),
                'coverage_rate': round(len(buckets_with_lifecycle) / len(buckets) * 100, 1) if buckets else 0
            },
            'buckets_with_lifecycle': buckets_with_lifecycle,
            'buckets_without_lifecycle': buckets_without_lifecycle,
            'recommendations': recommendations
        }
    
    except Exception as e:
        return {'error': str(e)}


@tool
def find_s3_versioning_waste(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Identify S3 versioning waste from old object versions.
    
    Note: This requires S3 Inventory for accurate analysis at scale.
    This implementation checks versioning status and provides estimates.
    """
    if aws_client is None:
        aws_client = AWSClient()
    
    try:
        s3 = aws_client.get_client('s3')
        
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        versioned_buckets = []
        waste_estimates = []
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            
            try:
                versioning = s3.get_bucket_versioning(Bucket=bucket_name)
                status = versioning.get('Status', 'Disabled')
                
                if status == 'Enabled':
                    # Check if lifecycle policy handles noncurrent versions
                    has_version_lifecycle = False
                    
                    try:
                        lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                        for rule in lifecycle.get('Rules', []):
                            if 'NoncurrentVersionTransitions' in rule or 'NoncurrentVersionExpiration' in rule:
                                has_version_lifecycle = True
                                break
                    except:
                        pass
                    
                    bucket_info = {
                        'bucket_name': bucket_name,
                        'versioning_status': status,
                        'has_version_lifecycle': has_version_lifecycle
                    }
                    
                    if not has_version_lifecycle:
                        bucket_info['warning'] = 'Versioning enabled without lifecycle - versions accumulate indefinitely'
                        bucket_info['recommendation'] = 'Add noncurrent version expiration after 90 days'
                        waste_estimates.append(bucket_info)
                    
                    versioned_buckets.append(bucket_info)
                    
            except Exception:
                continue
        
        recommendations = []
        
        if waste_estimates:
            recommendations.append(
                f"Add noncurrent version lifecycle to {len(waste_estimates)} buckets"
            )
            recommendations.append(
                "Expire noncurrent versions after 90 days to reduce costs"
            )
        
        recommendations.append(
            "Enable S3 Inventory to analyze actual version costs"
        )
        
        recommendations.append(
            "Consider MFA Delete for critical versioned buckets"
        )
        
        if not waste_estimates and versioned_buckets:
            recommendations.append(
                "✅ All versioned buckets have proper lifecycle policies"
            )
        
        return {
            'summary': {
                'total_buckets': len(buckets),
                'versioned_buckets': len(versioned_buckets),
                'buckets_without_version_lifecycle': len(waste_estimates)
            },
            'versioned_buckets': versioned_buckets,
            'waste_estimates': waste_estimates,
            'recommendations': recommendations,
            'note': 'Enable S3 Inventory for detailed version size and cost analysis'
        }
    
    except Exception as e:
        return {'error': str(e)}


@tool
def find_incomplete_multipart_uploads(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Find incomplete multipart uploads that are costing money.
    """
    if aws_client is None:
        aws_client = AWSClient()
    
    try:
        s3 = aws_client.get_client('s3')
        
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        buckets_with_incomplete = []
        total_incomplete = 0
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            
            try:
                # List multipart uploads
                uploads = s3.list_multipart_uploads(Bucket=bucket_name)
                incomplete_uploads = uploads.get('Uploads', [])
                
                if incomplete_uploads:
                    bucket_info = {
                        'bucket_name': bucket_name,
                        'incomplete_count': len(incomplete_uploads),
                        'uploads': []
                    }
                    
                    for upload in incomplete_uploads[:10]:  # Limit to 10 for output
                        bucket_info['uploads'].append({
                            'key': upload.get('Key'),
                            'upload_id': upload.get('UploadId'),
                            'initiated': upload.get('Initiated').isoformat() if upload.get('Initiated') else None
                        })
                    
                    buckets_with_incomplete.append(bucket_info)
                    total_incomplete += len(incomplete_uploads)
                    
            except Exception:
                continue
        
        recommendations = []
        
        if total_incomplete > 0:
            recommendations.append(
                f"Abort {total_incomplete} incomplete multipart uploads across {len(buckets_with_incomplete)} buckets"
            )
            recommendations.append(
                "Add lifecycle policy to abort incomplete uploads after 7 days"
            )
        
        recommendations.append(
            "Lifecycle rule: AbortIncompleteMultipartUpload DaysAfterInitiation: 7"
        )
        
        if total_incomplete == 0:
            recommendations.append(
                "✅ No incomplete multipart uploads found"
            )
        
        return {
            'summary': {
                'total_buckets_checked': len(buckets),
                'buckets_with_incomplete': len(buckets_with_incomplete),
                'total_incomplete_uploads': total_incomplete
            },
            'buckets_with_incomplete': buckets_with_incomplete,
            'recommendations': recommendations
        }
    
    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_replication(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 replication configuration and costs.
    """
    if aws_client is None:
        aws_client = AWSClient()
    
    try:
        s3 = aws_client.get_client('s3')
        
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        buckets_with_replication = []
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            
            try:
                replication = s3.get_bucket_replication(Bucket=bucket_name)
                rules = replication.get('ReplicationConfiguration', {}).get('Rules', [])
                
                bucket_info = {
                    'bucket_name': bucket_name,
                    'rule_count': len(rules),
                    'rules': []
                }
                
                for rule in rules:
                    destination = rule.get('Destination', {})
                    bucket_info['rules'].append({
                        'id': rule.get('ID', 'Unnamed'),
                        'status': rule.get('Status', 'Unknown'),
                        'destination_bucket': destination.get('Bucket', ''),
                        'storage_class': destination.get('StorageClass', 'STANDARD')
                    })
                
                buckets_with_replication.append(bucket_info)

            except Exception:
                # No replication configuration or other error
                continue
        
        recommendations = []
        
        if buckets_with_replication:
            recommendations.append(
                f"Review {len(buckets_with_replication)} replication configurations for necessity"
            )
            recommendations.append(
                "Replication costs: storage + PUT requests + data transfer"
            )
            recommendations.append(
                "Consider replicating to lower-cost storage classes (IA, Glacier)"
            )
        
        recommendations.append(
            "Use S3 Batch Replication for one-time backfill instead of continuous replication"
        )
        
        if not buckets_with_replication:
            recommendations.append(
                "✅ No replication configured - no replication costs"
            )
        
        return {
            'summary': {
                'total_buckets': len(buckets),
                'buckets_with_replication': len(buckets_with_replication)
            },
            'buckets_with_replication': buckets_with_replication,
            'recommendations': recommendations
        }
    
    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_request_costs(
    days_back: int = 30,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 request costs (often overlooked).
    
    Note: Detailed request metrics require CloudWatch metrics or S3 access logs.
    This provides general recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()
    
    try:
        s3 = aws_client.get_client('s3')
        
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        high_request_buckets = []
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            
            recommendation = {
                'bucket_name': bucket_name,
                'optimizations': []
            }
            
            # Check if CloudFront is being used (reduces direct S3 requests)
            # Check if request metrics are enabled
            try:
                # This would require CloudWatch metrics analysis
                # For now, provide general recommendations
                
                # Check if logging is enabled (indicates high-traffic bucket)
                try:
                    logging = s3.get_bucket_logging(Bucket=bucket_name)
                    if 'LoggingEnabled' in logging:
                        recommendation['optimizations'].append(
                            'High-traffic bucket - consider CloudFront for caching'
                        )
                except:
                    pass
                
            except Exception:
                continue
        
        recommendations = []
        
        recommendations.append(
            "Use CloudFront CDN to cache content and reduce S3 GET requests"
        )
        
        recommendations.append(
            "Batch small files into larger archives to reduce request counts"
        )
        
        recommendations.append(
            "Use S3 Select to query data instead of retrieving entire objects"
        )
        
        recommendations.append(
            "Enable S3 request metrics for detailed cost analysis"
        )
        
        return {
            'summary': {
                'total_buckets': len(buckets),
                'analysis_period_days': days_back
            },
            'recommendations': recommendations,
            'note': 'Enable CloudWatch request metrics and S3 access logs for detailed analysis'
        }
    
    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_large_s3_objects(
    size_threshold_gb: int = 5,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Identify large S3 objects for optimization.
    
    Note: For production use at scale, enable S3 Inventory.
    This implementation samples buckets.
    """
    if aws_client is None:
        aws_client = AWSClient()
    
    try:
        s3 = aws_client.get_client('s3')
        
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        large_objects = []
        total_large_object_size = 0
        
        size_threshold_bytes = size_threshold_gb * 1024 * 1024 * 1024
        
        # Sample first 5 buckets to avoid timeout
        for bucket in buckets[:5]:
            bucket_name = bucket['Name']
            
            try:
                # List objects (max 1000)
                objects = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1000)
                
                for obj in objects.get('Contents', []):
                    size_bytes = obj.get('Size', 0)
                    
                    if size_bytes >= size_threshold_bytes:
                        size_gb = size_bytes / (1024**3)
                        
                        large_objects.append({
                            'bucket': bucket_name,
                            'key': obj.get('Key'),
                            'size_gb': round(size_gb, 2),
                            'size_bytes': size_bytes,
                            'last_modified': obj.get('LastModified').isoformat() if obj.get('LastModified') else None,
                            'storage_class': obj.get('StorageClass', 'STANDARD'),
                            'recommendation': f'Consider Glacier for {size_gb:.1f}GB object if rarely accessed'
                        })
                        
                        total_large_object_size += size_bytes
                        
            except Exception:
                continue
        
        recommendations = []
        
        if large_objects:
            recommendations.append(
                f"Review {len(large_objects)} objects >{size_threshold_gb}GB for Glacier migration"
            )
            recommendations.append(
                "Large objects (>5GB) should use multipart upload for better performance"
            )
        
        recommendations.append(
            "Enable S3 Inventory for comprehensive large object analysis"
        )
        
        recommendations.append(
            "Consider S3 Intelligent-Tiering for automatic optimization"
        )
        
        if not large_objects:
            recommendations.append(
                f"✅ No objects >{size_threshold_gb}GB found in sampled buckets"
            )
        
        return {
            'summary': {
                'buckets_sampled': min(5, len(buckets)),
                'large_objects_found': len(large_objects),
                'total_size_gb': round(total_large_object_size / (1024**3), 2),
                'size_threshold_gb': size_threshold_gb
            },
            'large_objects': large_objects[:20],  # Limit output
            'recommendations': recommendations,
            'note': 'Sampled first 5 buckets (max 1000 objects each). Enable S3 Inventory for full analysis.'
        }
    
    except Exception as e:
        return {'error': str(e)}
