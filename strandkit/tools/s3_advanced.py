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
- Encryption auditing (SSE-S3, SSE-KMS, DSSE-KMS)
- Access Points analysis
- Compliance checks (Object Lock, retention)
- Inventory configuration analysis
- Cross-account access detection
- Event notifications audit
- Intelligent-Tiering optimization
- Permission boundary analysis
- Transfer Acceleration audit
- Operational metrics dashboard

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


@tool
def analyze_s3_encryption(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Audit S3 bucket encryption settings across all buckets.

    Checks:
    - Default encryption configuration (SSE-S3, SSE-KMS, DSSE-KMS)
    - KMS key details and rotation status
    - Bucket Key usage (reduces KMS costs)
    - Unencrypted buckets (critical security finding)

    Returns comprehensive encryption audit with recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')
        kms = aws_client.get_client('kms')

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        encrypted_buckets = []
        unencrypted_buckets = []
        kms_keys_used = {}

        for bucket in buckets:
            bucket_name = bucket['Name']

            try:
                # Get encryption configuration
                encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                rules = encryption.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])

                if rules:
                    rule = rules[0]
                    apply_config = rule.get('ApplyServerSideEncryptionByDefault', {})
                    bucket_key_enabled = rule.get('BucketKeyEnabled', False)

                    sse_algorithm = apply_config.get('SSEAlgorithm', 'Unknown')
                    kms_key_id = apply_config.get('KMSMasterKeyID')

                    bucket_info = {
                        'bucket_name': bucket_name,
                        'encryption_type': sse_algorithm,
                        'bucket_key_enabled': bucket_key_enabled,
                        'kms_key_id': kms_key_id
                    }

                    # Get KMS key details if using KMS
                    if kms_key_id and sse_algorithm in ['aws:kms', 'aws:kms:dsse']:
                        try:
                            # Extract key ID from ARN if needed
                            key_id = kms_key_id.split('/')[-1] if '/' in kms_key_id else kms_key_id

                            key_info = kms.describe_key(KeyId=key_id)
                            key_metadata = key_info.get('KeyMetadata', {})

                            bucket_info['kms_key_alias'] = key_metadata.get('Description', '')
                            bucket_info['kms_key_state'] = key_metadata.get('KeyState', 'Unknown')

                            # Check rotation status
                            try:
                                rotation = kms.get_key_rotation_status(KeyId=key_id)
                                bucket_info['kms_rotation_enabled'] = rotation.get('KeyRotationEnabled', False)
                            except Exception:
                                bucket_info['kms_rotation_enabled'] = 'N/A (AWS managed key)'

                            # Track KMS keys
                            if kms_key_id not in kms_keys_used:
                                kms_keys_used[kms_key_id] = []
                            kms_keys_used[kms_key_id].append(bucket_name)

                        except Exception as e:
                            bucket_info['kms_key_error'] = str(e)

                    # Check if Bucket Key should be enabled (cost optimization)
                    if sse_algorithm in ['aws:kms', 'aws:kms:dsse'] and not bucket_key_enabled:
                        bucket_info['recommendation'] = 'Enable Bucket Key to reduce KMS costs by up to 99%'

                    encrypted_buckets.append(bucket_info)
                else:
                    unencrypted_buckets.append({
                        'bucket_name': bucket_name,
                        'status': 'NO_ENCRYPTION',
                        'risk': 'CRITICAL',
                        'recommendation': 'Enable default encryption immediately'
                    })

            except s3.exceptions.ClientError as e:
                if 'ServerSideEncryptionConfigurationNotFoundError' in str(e):
                    unencrypted_buckets.append({
                        'bucket_name': bucket_name,
                        'status': 'NO_ENCRYPTION',
                        'risk': 'CRITICAL',
                        'recommendation': 'Enable default encryption immediately'
                    })
                else:
                    continue
            except Exception:
                continue

        # Categorize encryption types
        encryption_summary = {
            'SSE-S3 (AES-256)': 0,
            'SSE-KMS': 0,
            'DSSE-KMS': 0,
            'Unencrypted': len(unencrypted_buckets)
        }

        buckets_without_bucket_key = []

        for b in encrypted_buckets:
            enc_type = b.get('encryption_type', '')
            if enc_type == 'AES256':
                encryption_summary['SSE-S3 (AES-256)'] += 1
            elif enc_type == 'aws:kms':
                encryption_summary['SSE-KMS'] += 1
                if not b.get('bucket_key_enabled', False):
                    buckets_without_bucket_key.append(b['bucket_name'])
            elif enc_type == 'aws:kms:dsse':
                encryption_summary['DSSE-KMS'] += 1

        # Generate recommendations
        recommendations = []
        findings = []

        if unencrypted_buckets:
            findings.append({
                'severity': 'CRITICAL',
                'finding': f'{len(unencrypted_buckets)} buckets without default encryption',
                'action': 'Enable SSE-S3 or SSE-KMS encryption immediately'
            })

        if buckets_without_bucket_key:
            findings.append({
                'severity': 'MEDIUM',
                'finding': f'{len(buckets_without_bucket_key)} KMS-encrypted buckets without Bucket Key',
                'action': 'Enable Bucket Key to reduce KMS API costs by up to 99%'
            })

        recommendations.append('Use SSE-KMS for compliance requirements (audit trail via CloudTrail)')
        recommendations.append('Enable Bucket Key for all KMS-encrypted buckets')
        recommendations.append('Consider DSSE-KMS for FIPS 140-3 Level 3 compliance')

        if not unencrypted_buckets:
            recommendations.append('All buckets have default encryption enabled')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'encrypted_buckets': len(encrypted_buckets),
                'unencrypted_buckets': len(unencrypted_buckets),
                'encryption_breakdown': encryption_summary,
                'unique_kms_keys': len(kms_keys_used)
            },
            'findings': findings,
            'encrypted_buckets': encrypted_buckets,
            'unencrypted_buckets': unencrypted_buckets,
            'kms_keys_usage': {k: len(v) for k, v in kms_keys_used.items()},
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_access_points(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 Access Points configuration and security.

    Checks:
    - All access points across account
    - Network origin controls (VPC vs Internet)
    - Access point policies
    - Cross-account access point usage
    - Block public access settings per access point

    Returns access point inventory with security analysis.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3control = aws_client.get_client('s3control')
        sts = aws_client.get_client('sts')

        # Get account ID
        identity = sts.get_caller_identity()
        account_id = identity['Account']

        access_points = []
        internet_accessible = []
        cross_account_access = []

        try:
            # List all access points
            paginator = s3control.get_paginator('list_access_points')

            for page in paginator.paginate(AccountId=account_id):
                for ap in page.get('AccessPointList', []):
                    ap_name = ap.get('Name')
                    ap_bucket = ap.get('Bucket')

                    ap_info = {
                        'name': ap_name,
                        'bucket': ap_bucket,
                        'network_origin': ap.get('NetworkOrigin', 'Unknown'),
                        'vpc_id': ap.get('VpcConfiguration', {}).get('VpcId') if ap.get('NetworkOrigin') == 'VPC' else None,
                        'access_point_arn': ap.get('AccessPointArn')
                    }

                    # Get access point policy
                    try:
                        policy_response = s3control.get_access_point_policy(
                            AccountId=account_id,
                            Name=ap_name
                        )
                        policy = policy_response.get('Policy', '{}')
                        ap_info['has_policy'] = True

                        # Check for cross-account access
                        import json
                        try:
                            policy_doc = json.loads(policy)
                            for statement in policy_doc.get('Statement', []):
                                principal = statement.get('Principal', {})
                                if isinstance(principal, dict):
                                    aws_principal = principal.get('AWS', [])
                                    if isinstance(aws_principal, str):
                                        aws_principal = [aws_principal]
                                    for p in aws_principal:
                                        if account_id not in str(p) and p != '*':
                                            ap_info['cross_account_access'] = True
                                            cross_account_access.append(ap_name)
                                            break
                        except json.JSONDecodeError:
                            pass

                    except Exception:
                        ap_info['has_policy'] = False

                    # Check public access block
                    try:
                        pab = s3control.get_access_point_policy_status(
                            AccountId=account_id,
                            Name=ap_name
                        )
                        ap_info['is_public'] = pab.get('PolicyStatus', {}).get('IsPublic', False)
                    except Exception:
                        ap_info['is_public'] = 'Unknown'

                    # Track internet-accessible access points
                    if ap.get('NetworkOrigin') == 'Internet':
                        internet_accessible.append(ap_name)

                    access_points.append(ap_info)

        except Exception as e:
            if 'NoSuchAccessPoint' not in str(e):
                pass  # No access points is fine

        # Generate recommendations
        recommendations = []
        findings = []

        if internet_accessible:
            findings.append({
                'severity': 'MEDIUM',
                'finding': f'{len(internet_accessible)} access points accessible from internet',
                'action': 'Consider restricting to VPC-only access for sensitive data'
            })

        if cross_account_access:
            findings.append({
                'severity': 'HIGH',
                'finding': f'{len(cross_account_access)} access points with cross-account access',
                'action': 'Review and validate cross-account access requirements'
            })

        recommendations.append('Use VPC-origin access points for internal applications')
        recommendations.append('Implement least-privilege policies on access points')
        recommendations.append('Use access points to simplify bucket policy management')

        if not access_points:
            recommendations.append('Consider using Access Points to manage bucket access at scale')

        return {
            'summary': {
                'total_access_points': len(access_points),
                'internet_accessible': len(internet_accessible),
                'vpc_restricted': len(access_points) - len(internet_accessible),
                'cross_account_access': len(cross_account_access)
            },
            'findings': findings,
            'access_points': access_points,
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def find_s3_compliance_issues(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check S3 buckets for compliance and governance issues.

    Checks:
    - Object Lock status (WORM compliance)
    - Default retention settings
    - Legal holds capability
    - Governance vs Compliance mode
    - Versioning status (required for Object Lock)

    Returns compliance audit with regulatory recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        compliant_buckets = []
        non_compliant_buckets = []
        object_lock_buckets = []

        for bucket in buckets:
            bucket_name = bucket['Name']

            bucket_info = {
                'bucket_name': bucket_name,
                'object_lock_enabled': False,
                'versioning_enabled': False,
                'default_retention': None,
                'compliance_issues': []
            }

            try:
                # Check Object Lock configuration
                try:
                    object_lock = s3.get_object_lock_configuration(Bucket=bucket_name)
                    config = object_lock.get('ObjectLockConfiguration', {})

                    if config.get('ObjectLockEnabled') == 'Enabled':
                        bucket_info['object_lock_enabled'] = True

                        # Check default retention
                        retention = config.get('Rule', {}).get('DefaultRetention', {})
                        if retention:
                            bucket_info['default_retention'] = {
                                'mode': retention.get('Mode', 'None'),
                                'days': retention.get('Days'),
                                'years': retention.get('Years')
                            }

                        object_lock_buckets.append(bucket_info)

                except s3.exceptions.ClientError as e:
                    if 'ObjectLockConfigurationNotFoundError' in str(e):
                        bucket_info['object_lock_enabled'] = False
                    else:
                        raise

                # Check versioning (required for Object Lock)
                try:
                    versioning = s3.get_bucket_versioning(Bucket=bucket_name)
                    status = versioning.get('Status', 'Disabled')
                    bucket_info['versioning_enabled'] = status == 'Enabled'
                    bucket_info['versioning_status'] = status

                    mfa_delete = versioning.get('MFADelete', 'Disabled')
                    bucket_info['mfa_delete'] = mfa_delete

                except Exception:
                    bucket_info['versioning_enabled'] = False

                # Identify compliance issues
                if not bucket_info['versioning_enabled']:
                    bucket_info['compliance_issues'].append('Versioning disabled - cannot enable Object Lock')

                if bucket_info['object_lock_enabled']:
                    if not bucket_info.get('default_retention'):
                        bucket_info['compliance_issues'].append('Object Lock enabled but no default retention')
                    compliant_buckets.append(bucket_info)
                else:
                    bucket_info['compliance_issues'].append('Object Lock not enabled - no WORM protection')
                    non_compliant_buckets.append(bucket_info)

            except Exception as e:
                bucket_info['error'] = str(e)
                non_compliant_buckets.append(bucket_info)

        # Generate recommendations
        recommendations = []
        findings = []

        if non_compliant_buckets:
            findings.append({
                'severity': 'INFO',
                'finding': f'{len(non_compliant_buckets)} buckets without Object Lock',
                'action': 'Enable Object Lock on new buckets for regulatory compliance (SEC 17a-4, HIPAA, etc.)'
            })

        versioning_disabled = sum(1 for b in buckets if not any(
            cb.get('versioning_enabled') for cb in compliant_buckets + non_compliant_buckets
            if cb.get('bucket_name') == b['Name']
        ))

        if versioning_disabled > 0:
            findings.append({
                'severity': 'MEDIUM',
                'finding': 'Some buckets have versioning disabled',
                'action': 'Enable versioning for data protection and compliance'
            })

        recommendations.append('Enable Object Lock at bucket creation for WORM compliance')
        recommendations.append('Use Compliance mode for regulatory requirements (cannot be overridden)')
        recommendations.append('Use Governance mode for internal policies (can be overridden with permissions)')
        recommendations.append('Enable MFA Delete for additional protection')

        if object_lock_buckets:
            recommendations.append(f'{len(object_lock_buckets)} buckets are WORM-compliant')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'object_lock_enabled': len(object_lock_buckets),
                'without_object_lock': len(non_compliant_buckets),
                'compliance_rate': round(len(object_lock_buckets) / len(buckets) * 100, 1) if buckets else 0
            },
            'findings': findings,
            'object_lock_buckets': object_lock_buckets,
            'non_compliant_buckets': non_compliant_buckets[:20],  # Limit output
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_inventory_configs(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 Inventory configurations across all buckets.

    Checks:
    - Which buckets have inventory enabled
    - Inventory destination buckets
    - Inventory frequency and fields
    - Estimated inventory costs
    - Missing inventory on large buckets

    Returns inventory configuration analysis with cost estimates.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        buckets_with_inventory = []
        buckets_without_inventory = []
        inventory_destinations = set()

        # Inventory pricing: $0.0025 per million objects listed
        inventory_cost_per_million = 0.0025

        for bucket in buckets:
            bucket_name = bucket['Name']

            try:
                # List inventory configurations
                inventory_configs = s3.list_bucket_inventory_configurations(Bucket=bucket_name)
                configs = inventory_configs.get('InventoryConfigurationList', [])

                if configs:
                    bucket_info = {
                        'bucket_name': bucket_name,
                        'inventory_count': len(configs),
                        'configurations': []
                    }

                    for config in configs:
                        destination = config.get('Destination', {}).get('S3BucketDestination', {})
                        dest_bucket = destination.get('Bucket', '').split(':')[-1]
                        inventory_destinations.add(dest_bucket)

                        config_info = {
                            'id': config.get('Id'),
                            'destination_bucket': dest_bucket,
                            'format': destination.get('Format', 'CSV'),
                            'frequency': config.get('Schedule', {}).get('Frequency', 'Unknown'),
                            'included_fields': config.get('OptionalFields', []),
                            'is_enabled': config.get('IsEnabled', True)
                        }

                        bucket_info['configurations'].append(config_info)

                    buckets_with_inventory.append(bucket_info)
                else:
                    buckets_without_inventory.append({
                        'bucket_name': bucket_name,
                        'recommendation': 'Enable S3 Inventory for storage analysis and optimization'
                    })

            except Exception:
                buckets_without_inventory.append({
                    'bucket_name': bucket_name,
                    'recommendation': 'Enable S3 Inventory for storage analysis and optimization'
                })

        # Generate recommendations
        recommendations = []
        findings = []

        coverage_rate = len(buckets_with_inventory) / len(buckets) * 100 if buckets else 0

        if coverage_rate < 50:
            findings.append({
                'severity': 'MEDIUM',
                'finding': f'Only {coverage_rate:.1f}% of buckets have inventory configured',
                'action': 'Enable inventory on buckets for storage analysis'
            })

        if buckets_without_inventory:
            findings.append({
                'severity': 'INFO',
                'finding': f'{len(buckets_without_inventory)} buckets without inventory',
                'action': 'Consider enabling inventory for cost optimization analysis'
            })

        recommendations.append('Enable inventory on buckets with >1M objects for detailed analysis')
        recommendations.append('Use Parquet format for better query performance with Athena')
        recommendations.append('Include storage class and encryption fields for optimization')
        recommendations.append('Set Daily frequency for active buckets, Weekly for archives')

        estimated_monthly_cost = len(buckets_with_inventory) * inventory_cost_per_million * 10  # Assume 10M objects avg
        recommendations.append(f'Estimated inventory cost: ${estimated_monthly_cost:.2f}/month (assuming 10M objects/bucket)')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'with_inventory': len(buckets_with_inventory),
                'without_inventory': len(buckets_without_inventory),
                'coverage_rate': round(coverage_rate, 1),
                'unique_destinations': len(inventory_destinations)
            },
            'findings': findings,
            'buckets_with_inventory': buckets_with_inventory,
            'buckets_without_inventory': buckets_without_inventory[:20],  # Limit output
            'inventory_destinations': list(inventory_destinations),
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def find_s3_cross_account_access(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Audit S3 buckets for cross-account access configurations.

    Checks:
    - Bucket policies allowing external accounts
    - ACLs granting cross-account access
    - Access points with cross-account policies
    - Identifies unknown or untrusted accounts

    Returns cross-account access audit with security findings.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')
        sts = aws_client.get_client('sts')

        # Get current account ID
        identity = sts.get_caller_identity()
        current_account = identity['Account']

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        cross_account_buckets = []
        public_buckets = []
        external_accounts = set()

        for bucket in buckets:
            bucket_name = bucket['Name']

            bucket_findings = {
                'bucket_name': bucket_name,
                'cross_account_access': [],
                'public_access': False,
                'risk_level': 'LOW'
            }

            try:
                # Check bucket policy
                try:
                    policy_response = s3.get_bucket_policy(Bucket=bucket_name)
                    policy = policy_response.get('Policy', '{}')

                    import json
                    try:
                        policy_doc = json.loads(policy)

                        for statement in policy_doc.get('Statement', []):
                            effect = statement.get('Effect', 'Deny')
                            principal = statement.get('Principal', {})

                            # Check for public access
                            if principal == '*' or principal == {'AWS': '*'}:
                                condition = statement.get('Condition', {})
                                if not condition and effect == 'Allow':
                                    bucket_findings['public_access'] = True
                                    bucket_findings['risk_level'] = 'CRITICAL'
                                    public_buckets.append(bucket_name)

                            # Check for cross-account access
                            if isinstance(principal, dict):
                                aws_principals = principal.get('AWS', [])
                                if isinstance(aws_principals, str):
                                    aws_principals = [aws_principals]

                                for p in aws_principals:
                                    # Extract account ID from ARN
                                    if ':' in str(p):
                                        parts = str(p).split(':')
                                        if len(parts) >= 5:
                                            account_id = parts[4]
                                            if account_id and account_id != current_account and account_id != '*':
                                                external_accounts.add(account_id)
                                                bucket_findings['cross_account_access'].append({
                                                    'account_id': account_id,
                                                    'principal': p,
                                                    'effect': effect,
                                                    'actions': statement.get('Action', [])
                                                })
                                                if bucket_findings['risk_level'] == 'LOW':
                                                    bucket_findings['risk_level'] = 'MEDIUM'
                                    elif p != '*':
                                        # Root account reference
                                        account_id = str(p).replace('arn:aws:iam::', '').split(':')[0]
                                        if account_id and account_id != current_account:
                                            external_accounts.add(account_id)
                                            bucket_findings['cross_account_access'].append({
                                                'account_id': account_id,
                                                'principal': p,
                                                'effect': effect,
                                                'actions': statement.get('Action', [])
                                            })

                    except json.JSONDecodeError:
                        pass

                except s3.exceptions.ClientError:
                    pass  # No bucket policy

                # Check ACLs
                try:
                    acl = s3.get_bucket_acl(Bucket=bucket_name)

                    for grant in acl.get('Grants', []):
                        grantee = grant.get('Grantee', {})
                        grantee_type = grantee.get('Type')

                        if grantee_type == 'CanonicalUser':
                            grantee_id = grantee.get('ID', '')
                            # Note: Would need to map canonical ID to account
                            # For now, flag as external if not owner
                            owner_id = acl.get('Owner', {}).get('ID', '')
                            if grantee_id != owner_id:
                                bucket_findings['cross_account_access'].append({
                                    'type': 'ACL',
                                    'grantee_canonical_id': grantee_id,
                                    'permission': grant.get('Permission')
                                })

                        elif grantee_type == 'Group':
                            uri = grantee.get('URI', '')
                            if 'AllUsers' in uri or 'AuthenticatedUsers' in uri:
                                bucket_findings['public_access'] = True
                                bucket_findings['risk_level'] = 'CRITICAL'
                                if bucket_name not in public_buckets:
                                    public_buckets.append(bucket_name)

                except Exception:
                    pass

                if bucket_findings['cross_account_access'] or bucket_findings['public_access']:
                    cross_account_buckets.append(bucket_findings)

            except Exception:
                continue

        # Generate recommendations
        recommendations = []
        findings = []

        if public_buckets:
            findings.append({
                'severity': 'CRITICAL',
                'finding': f'{len(public_buckets)} buckets with public access',
                'action': 'Review and restrict public access immediately'
            })

        if external_accounts:
            findings.append({
                'severity': 'HIGH',
                'finding': f'{len(external_accounts)} external AWS accounts have access',
                'action': 'Verify all cross-account access is authorized'
            })

        recommendations.append('Enable S3 Block Public Access at account level')
        recommendations.append('Use AWS Organizations SCPs to prevent public bucket creation')
        recommendations.append('Review cross-account access quarterly')
        recommendations.append('Use IAM Access Analyzer to identify external access')

        if not cross_account_buckets:
            recommendations.append('No cross-account or public access detected')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'buckets_with_cross_account': len(cross_account_buckets),
                'public_buckets': len(public_buckets),
                'external_accounts': len(external_accounts),
                'current_account': current_account
            },
            'findings': findings,
            'cross_account_buckets': cross_account_buckets,
            'external_accounts': list(external_accounts),
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_event_notifications(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Audit S3 event notification configurations.

    Checks:
    - Lambda function destinations
    - SQS queue destinations
    - SNS topic destinations
    - EventBridge integration
    - Missing notifications on critical buckets

    Returns event notification audit with recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        buckets_with_notifications = []
        buckets_without_notifications = []
        notification_destinations = {
            'lambda': set(),
            'sqs': set(),
            'sns': set(),
            'eventbridge': 0
        }

        for bucket in buckets:
            bucket_name = bucket['Name']

            try:
                # Get notification configuration
                notification = s3.get_bucket_notification_configuration(Bucket=bucket_name)

                bucket_info = {
                    'bucket_name': bucket_name,
                    'lambda_configs': [],
                    'sqs_configs': [],
                    'sns_configs': [],
                    'eventbridge_enabled': False
                }

                has_notifications = False

                # Lambda configurations
                for config in notification.get('LambdaFunctionConfigurations', []):
                    has_notifications = True
                    lambda_arn = config.get('LambdaFunctionArn', '')
                    notification_destinations['lambda'].add(lambda_arn)
                    bucket_info['lambda_configs'].append({
                        'id': config.get('Id'),
                        'lambda_arn': lambda_arn,
                        'events': config.get('Events', [])
                    })

                # SQS configurations
                for config in notification.get('QueueConfigurations', []):
                    has_notifications = True
                    queue_arn = config.get('QueueArn', '')
                    notification_destinations['sqs'].add(queue_arn)
                    bucket_info['sqs_configs'].append({
                        'id': config.get('Id'),
                        'queue_arn': queue_arn,
                        'events': config.get('Events', [])
                    })

                # SNS configurations
                for config in notification.get('TopicConfigurations', []):
                    has_notifications = True
                    topic_arn = config.get('TopicArn', '')
                    notification_destinations['sns'].add(topic_arn)
                    bucket_info['sns_configs'].append({
                        'id': config.get('Id'),
                        'topic_arn': topic_arn,
                        'events': config.get('Events', [])
                    })

                # EventBridge configuration
                eventbridge = notification.get('EventBridgeConfiguration', {})
                if eventbridge:
                    has_notifications = True
                    bucket_info['eventbridge_enabled'] = True
                    notification_destinations['eventbridge'] += 1

                if has_notifications:
                    buckets_with_notifications.append(bucket_info)
                else:
                    buckets_without_notifications.append({
                        'bucket_name': bucket_name
                    })

            except Exception:
                buckets_without_notifications.append({
                    'bucket_name': bucket_name
                })

        # Generate recommendations
        recommendations = []
        findings = []

        coverage_rate = len(buckets_with_notifications) / len(buckets) * 100 if buckets else 0

        if notification_destinations['eventbridge'] > 0:
            findings.append({
                'severity': 'INFO',
                'finding': f'{notification_destinations["eventbridge"]} buckets using EventBridge',
                'action': 'EventBridge provides more flexible routing options'
            })

        recommendations.append('Use EventBridge for flexible event routing and filtering')
        recommendations.append('Enable notifications for security-sensitive buckets')
        recommendations.append('Consider dead-letter queues for notification failures')
        recommendations.append('Use prefix/suffix filters to reduce unnecessary notifications')

        if coverage_rate < 20:
            recommendations.append('Consider adding notifications for audit and monitoring')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'with_notifications': len(buckets_with_notifications),
                'without_notifications': len(buckets_without_notifications),
                'coverage_rate': round(coverage_rate, 1),
                'lambda_destinations': len(notification_destinations['lambda']),
                'sqs_destinations': len(notification_destinations['sqs']),
                'sns_destinations': len(notification_destinations['sns']),
                'eventbridge_enabled': notification_destinations['eventbridge']
            },
            'findings': findings,
            'buckets_with_notifications': buckets_with_notifications,
            'buckets_without_notifications': buckets_without_notifications[:20],  # Limit output
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_intelligent_tiering(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 Intelligent-Tiering configurations and optimization opportunities.

    Checks:
    - Buckets using Intelligent-Tiering
    - Archive Access tier configuration
    - Deep Archive Access tier configuration
    - Estimated savings from enabling IT
    - Buckets that would benefit from IT

    Returns Intelligent-Tiering analysis with savings estimates.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        buckets_with_it = []
        buckets_without_it = []

        # IT monitoring cost: $0.0025 per 1,000 objects
        monitoring_cost_per_1000 = 0.0025

        for bucket in buckets:
            bucket_name = bucket['Name']

            try:
                # Check for Intelligent-Tiering configurations
                it_configs = []

                try:
                    # List IT configurations
                    paginator = s3.get_paginator('list_bucket_intelligent_tiering_configurations')

                    for page in paginator.paginate(Bucket=bucket_name):
                        for config in page.get('IntelligentTieringConfigurationList', []):
                            config_info = {
                                'id': config.get('Id'),
                                'status': config.get('Status'),
                                'tierings': []
                            }

                            for tiering in config.get('Tierings', []):
                                config_info['tierings'].append({
                                    'access_tier': tiering.get('AccessTier'),
                                    'days': tiering.get('Days')
                                })

                            it_configs.append(config_info)

                except s3.exceptions.ClientError:
                    pass  # No IT configuration

                if it_configs:
                    # Check for Archive tiers
                    has_archive = any(
                        t.get('access_tier') == 'ARCHIVE_ACCESS'
                        for c in it_configs
                        for t in c.get('tierings', [])
                    )
                    has_deep_archive = any(
                        t.get('access_tier') == 'DEEP_ARCHIVE_ACCESS'
                        for c in it_configs
                        for t in c.get('tierings', [])
                    )

                    buckets_with_it.append({
                        'bucket_name': bucket_name,
                        'configurations': it_configs,
                        'archive_tier_enabled': has_archive,
                        'deep_archive_tier_enabled': has_deep_archive,
                        'optimization': 'Enable Deep Archive tier for maximum savings' if not has_deep_archive else 'Fully optimized'
                    })
                else:
                    # Check if bucket would benefit from IT
                    # (Buckets with unpredictable access patterns)
                    buckets_without_it.append({
                        'bucket_name': bucket_name,
                        'recommendation': 'Consider Intelligent-Tiering for automatic cost optimization',
                        'estimated_savings': '20-70% depending on access patterns'
                    })

            except Exception:
                continue

        # Calculate potential savings
        # Assume 30% average savings for buckets without IT
        potential_savings_percentage = 30

        # Generate recommendations
        recommendations = []
        findings = []

        if buckets_without_it:
            findings.append({
                'severity': 'MEDIUM',
                'finding': f'{len(buckets_without_it)} buckets not using Intelligent-Tiering',
                'action': f'Potential {potential_savings_percentage}% savings with IT'
            })

        archive_not_enabled = sum(1 for b in buckets_with_it if not b.get('archive_tier_enabled'))
        if archive_not_enabled:
            findings.append({
                'severity': 'LOW',
                'finding': f'{archive_not_enabled} IT buckets without Archive tier',
                'action': 'Enable Archive Access tier for rarely accessed data'
            })

        recommendations.append('Enable Intelligent-Tiering for buckets with unpredictable access')
        recommendations.append('Configure Archive Access tier (90+ days) for additional savings')
        recommendations.append('Configure Deep Archive tier (180+ days) for maximum savings')
        recommendations.append(f'IT monitoring cost: ${monitoring_cost_per_1000} per 1,000 objects/month')
        recommendations.append('IT is cost-effective for objects >128KB with variable access')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'using_intelligent_tiering': len(buckets_with_it),
                'not_using_it': len(buckets_without_it),
                'with_archive_tier': sum(1 for b in buckets_with_it if b.get('archive_tier_enabled')),
                'with_deep_archive': sum(1 for b in buckets_with_it if b.get('deep_archive_tier_enabled')),
                'potential_savings': f'{potential_savings_percentage}% average'
            },
            'findings': findings,
            'buckets_with_intelligent_tiering': buckets_with_it,
            'buckets_without_intelligent_tiering': buckets_without_it[:20],  # Limit output
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def find_s3_permission_boundaries(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze S3 permission boundaries and access controls.

    Checks:
    - Buckets with overly permissive policies
    - Public access block settings per bucket
    - ACL vs policy conflicts
    - Effective permissions summary
    - Block Public Access account settings

    Returns permission boundary analysis with security recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')
        s3control = aws_client.get_client('s3control')
        sts = aws_client.get_client('sts')

        # Get account ID
        identity = sts.get_caller_identity()
        account_id = identity['Account']

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        # Check account-level public access block
        account_public_block = {}
        try:
            account_pab = s3control.get_public_access_block(AccountId=account_id)
            account_public_block = account_pab.get('PublicAccessBlockConfiguration', {})
        except Exception:
            account_public_block = {'status': 'NOT_CONFIGURED'}

        permission_issues = []
        well_configured_buckets = []

        for bucket in buckets:
            bucket_name = bucket['Name']

            bucket_info = {
                'bucket_name': bucket_name,
                'public_access_block': {},
                'has_policy': False,
                'policy_issues': [],
                'acl_issues': [],
                'risk_level': 'LOW'
            }

            try:
                # Check bucket-level public access block
                try:
                    pab = s3.get_public_access_block(Bucket=bucket_name)
                    config = pab.get('PublicAccessBlockConfiguration', {})
                    bucket_info['public_access_block'] = {
                        'block_public_acls': config.get('BlockPublicAcls', False),
                        'ignore_public_acls': config.get('IgnorePublicAcls', False),
                        'block_public_policy': config.get('BlockPublicPolicy', False),
                        'restrict_public_buckets': config.get('RestrictPublicBuckets', False)
                    }

                    # Check if fully blocked
                    all_blocked = all([
                        config.get('BlockPublicAcls', False),
                        config.get('IgnorePublicAcls', False),
                        config.get('BlockPublicPolicy', False),
                        config.get('RestrictPublicBuckets', False)
                    ])

                    if not all_blocked:
                        bucket_info['policy_issues'].append('Public access block not fully enabled')
                        bucket_info['risk_level'] = 'MEDIUM'

                except s3.exceptions.ClientError:
                    bucket_info['public_access_block'] = {'status': 'NOT_CONFIGURED'}
                    bucket_info['policy_issues'].append('No public access block configuration')
                    bucket_info['risk_level'] = 'HIGH'

                # Check bucket policy
                try:
                    policy_response = s3.get_bucket_policy(Bucket=bucket_name)
                    bucket_info['has_policy'] = True

                    import json
                    policy = json.loads(policy_response.get('Policy', '{}'))

                    for statement in policy.get('Statement', []):
                        effect = statement.get('Effect', 'Deny')
                        principal = statement.get('Principal', {})
                        actions = statement.get('Action', [])

                        if isinstance(actions, str):
                            actions = [actions]

                        # Check for overly permissive policies
                        if effect == 'Allow':
                            if principal == '*' or principal == {'AWS': '*'}:
                                condition = statement.get('Condition', {})
                                if not condition:
                                    bucket_info['policy_issues'].append('Policy allows public access without conditions')
                                    bucket_info['risk_level'] = 'CRITICAL'

                            # Check for dangerous actions
                            dangerous_actions = ['s3:*', 's3:Delete*', 's3:Put*']
                            for action in actions:
                                if any(d in action for d in dangerous_actions):
                                    if principal == '*' or principal == {'AWS': '*'}:
                                        bucket_info['policy_issues'].append(f'Dangerous action {action} allowed publicly')
                                        bucket_info['risk_level'] = 'CRITICAL'

                except s3.exceptions.ClientError:
                    pass  # No bucket policy

                # Check ACL
                try:
                    acl = s3.get_bucket_acl(Bucket=bucket_name)

                    for grant in acl.get('Grants', []):
                        grantee = grant.get('Grantee', {})
                        uri = grantee.get('URI', '')

                        if 'AllUsers' in uri:
                            bucket_info['acl_issues'].append('ACL grants public access (AllUsers)')
                            bucket_info['risk_level'] = 'CRITICAL'
                        elif 'AuthenticatedUsers' in uri:
                            bucket_info['acl_issues'].append('ACL grants access to all authenticated AWS users')
                            bucket_info['risk_level'] = 'HIGH'

                except Exception:
                    pass

                if bucket_info['policy_issues'] or bucket_info['acl_issues']:
                    permission_issues.append(bucket_info)
                else:
                    well_configured_buckets.append({
                        'bucket_name': bucket_name,
                        'status': 'SECURE'
                    })

            except Exception:
                continue

        # Categorize by risk
        critical_buckets = [b for b in permission_issues if b['risk_level'] == 'CRITICAL']
        high_risk_buckets = [b for b in permission_issues if b['risk_level'] == 'HIGH']
        medium_risk_buckets = [b for b in permission_issues if b['risk_level'] == 'MEDIUM']

        # Generate recommendations
        recommendations = []
        findings = []

        if critical_buckets:
            findings.append({
                'severity': 'CRITICAL',
                'finding': f'{len(critical_buckets)} buckets with critical permission issues',
                'action': 'Immediately review and restrict access'
            })

        if high_risk_buckets:
            findings.append({
                'severity': 'HIGH',
                'finding': f'{len(high_risk_buckets)} buckets with high-risk permissions',
                'action': 'Review access controls as priority'
            })

        # Check account-level settings
        if account_public_block.get('status') == 'NOT_CONFIGURED':
            findings.append({
                'severity': 'HIGH',
                'finding': 'Account-level public access block not configured',
                'action': 'Enable S3 Block Public Access at account level'
            })

        recommendations.append('Enable Block Public Access at account level')
        recommendations.append('Use bucket policies instead of ACLs (ACLs are legacy)')
        recommendations.append('Apply least-privilege principle to all bucket policies')
        recommendations.append('Use IAM Access Analyzer to review effective permissions')

        if not permission_issues:
            recommendations.append('All buckets have appropriate permission boundaries')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'secure_buckets': len(well_configured_buckets),
                'buckets_with_issues': len(permission_issues),
                'critical_risk': len(critical_buckets),
                'high_risk': len(high_risk_buckets),
                'medium_risk': len(medium_risk_buckets)
            },
            'account_public_access_block': account_public_block,
            'findings': findings,
            'permission_issues': permission_issues,
            'well_configured_buckets': well_configured_buckets[:10],  # Limit output
            'recommendations': recommendations
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def analyze_s3_transfer_acceleration(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Audit S3 Transfer Acceleration configurations.

    Checks:
    - Buckets with Transfer Acceleration enabled
    - TA usage and estimated costs
    - Buckets that would benefit from TA
    - CloudFront vs TA comparison

    Returns Transfer Acceleration analysis with cost optimization recommendations.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')

        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        ta_enabled_buckets = []
        ta_disabled_buckets = []

        # Transfer Acceleration pricing (additional cost per GB)
        # $0.04/GB for US, Europe, Japan
        # $0.08/GB for other locations
        ta_cost_per_gb_standard = 0.04
        ta_cost_per_gb_other = 0.08

        for bucket in buckets:
            bucket_name = bucket['Name']

            try:
                # Get Transfer Acceleration status
                try:
                    ta_config = s3.get_bucket_accelerate_configuration(Bucket=bucket_name)
                    status = ta_config.get('Status', 'Suspended')

                    if status == 'Enabled':
                        # Get bucket region
                        location = s3.get_bucket_location(Bucket=bucket_name)
                        region = location.get('LocationConstraint') or 'us-east-1'

                        ta_enabled_buckets.append({
                            'bucket_name': bucket_name,
                            'status': 'Enabled',
                            'region': region,
                            'accelerated_endpoint': f'{bucket_name}.s3-accelerate.amazonaws.com',
                            'cost_per_gb': ta_cost_per_gb_standard if region.startswith(('us-', 'eu-', 'ap-northeast-1')) else ta_cost_per_gb_other,
                            'recommendation': 'Review if TA is being utilized; disable if not needed'
                        })
                    else:
                        ta_disabled_buckets.append({
                            'bucket_name': bucket_name,
                            'status': status
                        })

                except s3.exceptions.ClientError:
                    ta_disabled_buckets.append({
                        'bucket_name': bucket_name,
                        'status': 'Not configured'
                    })

            except Exception:
                continue

        # Generate recommendations
        recommendations = []
        findings = []

        if ta_enabled_buckets:
            findings.append({
                'severity': 'INFO',
                'finding': f'{len(ta_enabled_buckets)} buckets with Transfer Acceleration enabled',
                'action': 'Review usage to ensure TA is providing value'
            })

        recommendations.append('Use TA for large file transfers over long distances')
        recommendations.append('Compare TA cost vs CloudFront for your use case')
        recommendations.append('TA is best for: uploads, cross-region transfers, large files')
        recommendations.append('CloudFront is better for: repeated downloads, static content')
        recommendations.append(f'TA cost: ${ta_cost_per_gb_standard}/GB (US/EU) or ${ta_cost_per_gb_other}/GB (other)')

        # Cost comparison note
        recommendations.append('CloudFront: $0.085/GB (first 10TB) with caching benefits')

        if not ta_enabled_buckets:
            recommendations.append('Consider TA for buckets with global upload requirements')

        return {
            'summary': {
                'total_buckets': len(buckets),
                'ta_enabled': len(ta_enabled_buckets),
                'ta_disabled': len(ta_disabled_buckets),
                'estimated_ta_cost_per_gb': f'${ta_cost_per_gb_standard}-${ta_cost_per_gb_other}'
            },
            'findings': findings,
            'ta_enabled_buckets': ta_enabled_buckets,
            'recommendations': recommendations,
            'cloudfront_comparison': {
                'cloudfront_cost_per_gb': '$0.085 (first 10TB)',
                'ta_advantage': 'Better for uploads and dynamic content',
                'cloudfront_advantage': 'Better for repeated downloads with caching'
            }
        }

    except Exception as e:
        return {'error': str(e)}


@tool
def get_s3_operational_metrics(
    bucket_name: Optional[str] = None,
    days_back: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get S3 operational health metrics dashboard.

    Retrieves:
    - 4xx/5xx error rates per bucket
    - First byte latency metrics
    - Total request counts
    - Bandwidth utilization trends
    - All requests breakdown

    Args:
        bucket_name: Specific bucket to analyze (optional, analyzes all if not specified)
        days_back: Number of days to analyze (default: 7)

    Returns operational metrics with performance insights.
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        s3 = aws_client.get_client('s3')
        cloudwatch = aws_client.get_client('cloudwatch')

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)

        # Get buckets to analyze
        if bucket_name:
            buckets_to_check = [{'Name': bucket_name}]
        else:
            response = s3.list_buckets()
            buckets_to_check = response.get('Buckets', [])[:10]  # Limit to 10 for performance

        bucket_metrics = []

        # S3 request metrics (requires bucket metrics to be enabled)
        metric_definitions = [
            {'name': 'AllRequests', 'stat': 'Sum'},
            {'name': 'GetRequests', 'stat': 'Sum'},
            {'name': 'PutRequests', 'stat': 'Sum'},
            {'name': '4xxErrors', 'stat': 'Sum'},
            {'name': '5xxErrors', 'stat': 'Sum'},
            {'name': 'FirstByteLatency', 'stat': 'Average'},
            {'name': 'TotalRequestLatency', 'stat': 'Average'},
            {'name': 'BytesDownloaded', 'stat': 'Sum'},
            {'name': 'BytesUploaded', 'stat': 'Sum'}
        ]

        for bucket in buckets_to_check:
            b_name = bucket['Name']

            bucket_data = {
                'bucket_name': b_name,
                'metrics': {},
                'metrics_enabled': False,
                'health_status': 'UNKNOWN'
            }

            try:
                # Try to get metrics (requires request metrics to be enabled)
                for metric_def in metric_definitions:
                    try:
                        response = cloudwatch.get_metric_statistics(
                            Namespace='AWS/S3',
                            MetricName=metric_def['name'],
                            Dimensions=[
                                {'Name': 'BucketName', 'Value': b_name},
                                {'Name': 'FilterId', 'Value': 'EntireBucket'}
                            ],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=86400,  # Daily
                            Statistics=[metric_def['stat']]
                        )

                        datapoints = response.get('Datapoints', [])
                        if datapoints:
                            bucket_data['metrics_enabled'] = True

                            if metric_def['stat'] == 'Sum':
                                total = sum(dp.get('Sum', 0) for dp in datapoints)
                                bucket_data['metrics'][metric_def['name']] = total
                            else:
                                avg = sum(dp.get('Average', 0) for dp in datapoints) / len(datapoints) if datapoints else 0
                                bucket_data['metrics'][metric_def['name']] = round(avg, 2)

                    except Exception:
                        continue

                # Calculate health status
                if bucket_data['metrics_enabled']:
                    all_requests = bucket_data['metrics'].get('AllRequests', 0)
                    errors_4xx = bucket_data['metrics'].get('4xxErrors', 0)
                    errors_5xx = bucket_data['metrics'].get('5xxErrors', 0)

                    if all_requests > 0:
                        error_rate = (errors_4xx + errors_5xx) / all_requests * 100
                        bucket_data['error_rate_percent'] = round(error_rate, 2)

                        if error_rate < 1:
                            bucket_data['health_status'] = 'HEALTHY'
                        elif error_rate < 5:
                            bucket_data['health_status'] = 'WARNING'
                        else:
                            bucket_data['health_status'] = 'CRITICAL'
                    else:
                        bucket_data['health_status'] = 'NO_TRAFFIC'

                    # Convert bytes to GB
                    if 'BytesDownloaded' in bucket_data['metrics']:
                        bucket_data['metrics']['BytesDownloaded_GB'] = round(
                            bucket_data['metrics']['BytesDownloaded'] / (1024**3), 2
                        )
                    if 'BytesUploaded' in bucket_data['metrics']:
                        bucket_data['metrics']['BytesUploaded_GB'] = round(
                            bucket_data['metrics']['BytesUploaded'] / (1024**3), 2
                        )

                bucket_metrics.append(bucket_data)

            except Exception:
                bucket_metrics.append(bucket_data)

        # Identify buckets needing attention
        buckets_needing_metrics = [b for b in bucket_metrics if not b['metrics_enabled']]
        unhealthy_buckets = [b for b in bucket_metrics if b['health_status'] in ['WARNING', 'CRITICAL']]

        # Generate recommendations
        recommendations = []
        findings = []

        if buckets_needing_metrics:
            findings.append({
                'severity': 'INFO',
                'finding': f'{len(buckets_needing_metrics)} buckets without request metrics',
                'action': 'Enable request metrics for operational visibility'
            })

        if unhealthy_buckets:
            findings.append({
                'severity': 'HIGH',
                'finding': f'{len(unhealthy_buckets)} buckets with elevated error rates',
                'action': 'Investigate 4xx/5xx errors'
            })

        recommendations.append('Enable S3 request metrics for operational visibility')
        recommendations.append('Set up CloudWatch alarms for error rate thresholds')
        recommendations.append('Use S3 Storage Lens for account-wide metrics')
        recommendations.append('Monitor FirstByteLatency for performance issues')

        # Calculate totals
        total_requests = sum(b['metrics'].get('AllRequests', 0) for b in bucket_metrics)
        total_errors = sum(
            b['metrics'].get('4xxErrors', 0) + b['metrics'].get('5xxErrors', 0)
            for b in bucket_metrics
        )

        return {
            'summary': {
                'buckets_analyzed': len(bucket_metrics),
                'buckets_with_metrics': len([b for b in bucket_metrics if b['metrics_enabled']]),
                'analysis_period_days': days_back,
                'total_requests': total_requests,
                'total_errors': total_errors,
                'overall_error_rate': round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
                'healthy_buckets': len([b for b in bucket_metrics if b['health_status'] == 'HEALTHY']),
                'unhealthy_buckets': len(unhealthy_buckets)
            },
            'findings': findings,
            'bucket_metrics': bucket_metrics,
            'recommendations': recommendations,
            'note': 'Request metrics must be enabled on buckets to collect detailed statistics'
        }

    except Exception as e:
        return {'error': str(e)}
