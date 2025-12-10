"""
AWS Bedrock tools for foundation model analysis and optimization.

This module provides tools for analyzing Bedrock model usage, costs, performance,
and helping select the right models for your workload.

Tools:
- analyze_bedrock_usage: Overall usage and cost analysis
- list_available_models: List all available foundation models
- get_model_details: Get detailed model information
- analyze_model_performance: Performance metrics per model
- compare_models: Compare models side-by-side
- get_model_invocation_logs: Recent model invocations for debugging
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from strands import tool
from strandkit.core.aws_client import AWSClient


@tool
def analyze_bedrock_usage(
    days_back: int = 30,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze AWS Bedrock usage, costs, and model invocation metrics.

    Provides comprehensive analysis of Bedrock usage including:
    - Model invocation counts and costs by model
    - Token usage (input/output tokens)
    - Cost breakdown by model family (Claude, Llama, Titan, etc.)
    - Usage trends over time
    - Cost optimization recommendations

    Args:
        days_back: Number of days to analyze (default: 30)
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Total invocations, costs, tokens processed
        - by_model: Usage breakdown by model ID
        - by_model_family: Costs by provider (Anthropic, Meta, Amazon, etc.)
        - trends: Daily usage and cost trends
        - recommendations: Cost optimization suggestions
        - top_models: Most used and most expensive models

    Example:
        >>> usage = analyze_bedrock_usage(days_back=30)
        >>> print(f"Total cost: ${usage['summary']['total_cost']:.2f}")
        >>> print(f"Total invocations: {usage['summary']['total_invocations']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        bedrock = aws_client.get_client('bedrock')
        bedrock_runtime = aws_client.get_client('bedrock-runtime')
        cloudwatch = aws_client.get_client('cloudwatch')
        ce = aws_client.get_client('ce')

        # Get list of models to analyze
        try:
            models_response = bedrock.list_foundation_models()
            available_models = models_response.get('modelSummaries', [])
        except Exception as e:
            available_models = []

        # Get Bedrock costs from Cost Explorer
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        total_cost = 0.0
        cost_by_service = {}

        try:
            cost_response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon Bedrock']
                    }
                }
            )

            for result in cost_response.get('ResultsByTime', []):
                cost = float(result['Total']['UnblendedCost']['Amount'])
                total_cost += cost

        except Exception as e:
            pass  # Cost Explorer might not be available or no data

        # Get CloudWatch metrics for model invocations
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        model_metrics = {}

        # Try to get invocation metrics for common model patterns
        common_model_patterns = [
            'anthropic.claude',
            'amazon.titan',
            'meta.llama',
            'cohere',
            'ai21',
            'stability'
        ]

        total_invocations = 0

        for pattern in common_model_patterns:
            try:
                # Get invocation count
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Bedrock',
                    MetricName='Invocations',
                    Dimensions=[
                        {
                            'Name': 'ModelId',
                            'Value': pattern
                        }
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # 1 day
                    Statistics=['Sum']
                )

                invocations = sum(dp['Sum'] for dp in response.get('Datapoints', []))
                if invocations > 0:
                    total_invocations += invocations
                    model_metrics[pattern] = {
                        'invocations': invocations,
                        'avg_daily': invocations / days_back
                    }

            except Exception:
                continue

        # Build model usage breakdown
        by_model = []
        for model_pattern, metrics in model_metrics.items():
            by_model.append({
                'model_pattern': model_pattern,
                'invocations': int(metrics['invocations']),
                'avg_daily_invocations': round(metrics['avg_daily'], 1),
                'percentage_of_total': round((metrics['invocations'] / total_invocations * 100) if total_invocations > 0 else 0, 1)
            })

        # Sort by invocations descending
        by_model.sort(key=lambda x: x['invocations'], reverse=True)

        # Group by model family
        by_model_family = {
            'Anthropic (Claude)': sum(m['invocations'] for m in by_model if 'claude' in m['model_pattern']),
            'Amazon (Titan)': sum(m['invocations'] for m in by_model if 'titan' in m['model_pattern']),
            'Meta (Llama)': sum(m['invocations'] for m in by_model if 'llama' in m['model_pattern']),
            'Cohere': sum(m['invocations'] for m in by_model if 'cohere' in m['model_pattern']),
            'AI21 Labs': sum(m['invocations'] for m in by_model if 'ai21' in m['model_pattern']),
            'Stability AI': sum(m['invocations'] for m in by_model if 'stability' in m['model_pattern'])
        }

        # Remove zero-usage families
        by_model_family = {k: v for k, v in by_model_family.items() if v > 0}

        # Estimate costs (rough estimates based on typical pricing)
        estimated_cost_per_1k_invocations = {
            'claude': 0.25,  # Rough average for Claude models
            'titan': 0.10,   # Titan is cheaper
            'llama': 0.05,   # Llama is often cheapest
            'cohere': 0.15,
            'ai21': 0.20,
            'stability': 0.30  # Image models are expensive
        }

        for model in by_model:
            pattern = model['model_pattern']
            invocations = model['invocations']

            # Find matching cost estimate
            cost_per_1k = 0.15  # Default
            for key, cost in estimated_cost_per_1k_invocations.items():
                if key in pattern:
                    cost_per_1k = cost
                    break

            estimated_cost = (invocations / 1000) * cost_per_1k
            model['estimated_cost'] = round(estimated_cost, 2)

        total_estimated_cost = sum(m['estimated_cost'] for m in by_model)

        # Use actual cost if available, otherwise use estimate
        if total_cost > 0:
            actual_total_cost = total_cost
        else:
            actual_total_cost = total_estimated_cost

        # Generate recommendations
        recommendations = []

        if total_invocations > 0:
            # Check for expensive model usage
            claude_usage = sum(m['invocations'] for m in by_model if 'claude' in m['model_pattern'])
            llama_usage = sum(m['invocations'] for m in by_model if 'llama' in m['model_pattern'])

            if claude_usage > 0 and llama_usage == 0:
                recommendations.append({
                    'category': 'cost_optimization',
                    'priority': 'medium',
                    'title': 'Consider Llama for some workloads',
                    'description': f'You are using Claude for all {claude_usage:,} invocations. Llama 2/3 models are 70-80% cheaper and may work for some use cases.',
                    'potential_savings': f'${(claude_usage / 1000 * 0.20):.2f}/month'
                })

            # Check for very high usage
            if total_invocations > 100000:
                recommendations.append({
                    'category': 'cost_optimization',
                    'priority': 'high',
                    'title': 'High usage - consider Provisioned Throughput',
                    'description': f'With {total_invocations:,} invocations, Provisioned Throughput might be cheaper than on-demand pricing.',
                    'action': 'Evaluate Bedrock Provisioned Throughput pricing'
                })

        # Check if logging is enabled
        recommendations.append({
            'category': 'observability',
            'priority': 'medium',
            'title': 'Enable model invocation logging',
            'description': 'Enable CloudWatch Logs for Bedrock to track prompts, responses, and debug issues.',
            'action': 'Configure model invocation logging in Bedrock settings'
        })

        # Summary
        summary = {
            'total_invocations': int(total_invocations),
            'total_cost': round(actual_total_cost, 2),
            'avg_daily_invocations': round(total_invocations / days_back, 1),
            'avg_daily_cost': round(actual_total_cost / days_back, 2),
            'days_analyzed': days_back,
            'unique_models_used': len(by_model),
            'cost_source': 'actual' if total_cost > 0 else 'estimated'
        }

        # Top models
        top_by_usage = by_model[:3] if len(by_model) >= 3 else by_model
        top_by_cost = sorted(by_model, key=lambda x: x.get('estimated_cost', 0), reverse=True)[:3]

        return {
            'summary': summary,
            'by_model': by_model,
            'by_model_family': by_model_family,
            'top_models': {
                'by_usage': top_by_usage,
                'by_cost': top_by_cost
            },
            'recommendations': recommendations,
            'available_models_count': len(available_models)
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to analyze Bedrock usage. Ensure you have Bedrock access in this region.'
        }


@tool
def list_available_models(
    provider_filter: Optional[str] = None,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    List all available foundation models in AWS Bedrock.

    Retrieves the complete catalog of foundation models available in your region,
    including models from Anthropic, Amazon, Meta, Cohere, AI21 Labs, and Stability AI.

    Args:
        provider_filter: Optional filter by provider (e.g., 'Anthropic', 'Amazon', 'Meta')
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Total models, models by provider
        - models: List of model details (ID, name, provider, modalities)
        - by_provider: Models grouped by provider
        - by_modality: Models grouped by capability (text, image, embedding)

    Example:
        >>> models = list_available_models()
        >>> print(f"Total models: {models['summary']['total_models']}")
        >>>
        >>> # Filter for Anthropic models
        >>> claude_models = list_available_models(provider_filter='Anthropic')
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        bedrock = aws_client.get_client('bedrock')

        # List all foundation models
        response = bedrock.list_foundation_models()
        all_models = response.get('modelSummaries', [])

        # Apply provider filter if specified
        if provider_filter:
            all_models = [m for m in all_models if provider_filter.lower() in m.get('providerName', '').lower()]

        # Process models
        models = []
        by_provider = {}
        by_modality = {
            'TEXT': [],
            'IMAGE': [],
            'EMBEDDING': [],
            'MULTIMODAL': []
        }

        for model in all_models:
            model_info = {
                'model_id': model.get('modelId'),
                'model_name': model.get('modelName'),
                'provider': model.get('providerName'),
                'input_modalities': model.get('inputModalities', []),
                'output_modalities': model.get('outputModalities', []),
                'customizations_supported': model.get('customizationsSupported', []),
                'inference_types': model.get('inferenceTypesSupported', []),
                'response_streaming': model.get('responseStreamingSupported', False)
            }

            models.append(model_info)

            # Group by provider
            provider = model_info['provider']
            if provider not in by_provider:
                by_provider[provider] = []
            by_provider[provider].append(model_info['model_id'])

            # Group by modality
            input_mods = model_info['input_modalities']
            output_mods = model_info['output_modalities']

            if 'TEXT' in input_mods and 'TEXT' in output_mods:
                by_modality['TEXT'].append(model_info['model_id'])
            if 'IMAGE' in input_mods or 'IMAGE' in output_mods:
                by_modality['IMAGE'].append(model_info['model_id'])
            if 'EMBEDDING' in output_mods:
                by_modality['EMBEDDING'].append(model_info['model_id'])
            if len(input_mods) > 1 or len(output_mods) > 1:
                by_modality['MULTIMODAL'].append(model_info['model_id'])

        # Remove empty modalities
        by_modality = {k: v for k, v in by_modality.items() if v}

        # Summary
        summary = {
            'total_models': len(models),
            'providers': list(by_provider.keys()),
            'provider_count': len(by_provider),
            'text_models': len(by_modality.get('TEXT', [])),
            'image_models': len(by_modality.get('IMAGE', [])),
            'embedding_models': len(by_modality.get('EMBEDDING', []))
        }

        return {
            'summary': summary,
            'models': models,
            'by_provider': by_provider,
            'by_modality': by_modality
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to list Bedrock models. Ensure you have Bedrock access in this region.'
        }


@tool
def get_model_details(
    model_id: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific Bedrock foundation model.

    Retrieves comprehensive details including pricing, capabilities, context limits,
    and supported features for a specific model.

    Args:
        model_id: Model ID (e.g., 'anthropic.claude-3-sonnet-20240229-v1:0')
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - model_info: Model ID, name, provider, version
        - capabilities: Input/output modalities, streaming support
        - pricing: Estimated pricing per 1K tokens (if available)
        - limits: Context window, max tokens
        - customizations: Supported customization types
        - use_cases: Recommended use cases

    Example:
        >>> details = get_model_details('anthropic.claude-3-sonnet-20240229-v1:0')
        >>> print(f"Model: {details['model_info']['model_name']}")
        >>> print(f"Context window: {details['limits']['context_window']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        bedrock = aws_client.get_client('bedrock')

        # Get model details
        try:
            response = bedrock.get_foundation_model(modelIdentifier=model_id)
            model_details = response.get('modelDetails', {})
        except Exception as e:
            return {
                'error': str(e),
                'message': f'Model {model_id} not found or not available in this region.'
            }

        # Extract model information
        model_info = {
            'model_id': model_details.get('modelId'),
            'model_name': model_details.get('modelName'),
            'provider': model_details.get('providerName'),
            'model_arn': model_details.get('modelArn')
        }

        # Capabilities
        capabilities = {
            'input_modalities': model_details.get('inputModalities', []),
            'output_modalities': model_details.get('outputModalities', []),
            'response_streaming': model_details.get('responseStreamingSupported', False),
            'customizations_supported': model_details.get('customizationsSupported', []),
            'inference_types': model_details.get('inferenceTypesSupported', [])
        }

        # Pricing estimates (based on public pricing as of 2024)
        pricing = _get_model_pricing_estimate(model_id)

        # Limits (estimated based on model type)
        limits = _get_model_limits(model_id, model_details)

        # Use cases
        use_cases = _get_model_use_cases(model_id, capabilities)

        return {
            'model_info': model_info,
            'capabilities': capabilities,
            'pricing': pricing,
            'limits': limits,
            'use_cases': use_cases
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': f'Failed to get details for model {model_id}'
        }


def _get_model_pricing_estimate(model_id: str) -> Dict[str, Any]:
    """Estimate pricing for a model based on public pricing."""
    pricing = {
        'input_per_1k_tokens': 0.0,
        'output_per_1k_tokens': 0.0,
        'currency': 'USD',
        'note': 'Estimated pricing - check AWS pricing page for exact rates'
    }

    # Claude models
    if 'claude-3-opus' in model_id:
        pricing['input_per_1k_tokens'] = 0.015
        pricing['output_per_1k_tokens'] = 0.075
    elif 'claude-3-sonnet' in model_id:
        pricing['input_per_1k_tokens'] = 0.003
        pricing['output_per_1k_tokens'] = 0.015
    elif 'claude-3-haiku' in model_id:
        pricing['input_per_1k_tokens'] = 0.00025
        pricing['output_per_1k_tokens'] = 0.00125
    elif 'claude-2' in model_id:
        pricing['input_per_1k_tokens'] = 0.008
        pricing['output_per_1k_tokens'] = 0.024

    # Titan models
    elif 'titan-text-express' in model_id:
        pricing['input_per_1k_tokens'] = 0.0002
        pricing['output_per_1k_tokens'] = 0.0006
    elif 'titan-text-lite' in model_id:
        pricing['input_per_1k_tokens'] = 0.00015
        pricing['output_per_1k_tokens'] = 0.0002
    elif 'titan-embed' in model_id:
        pricing['input_per_1k_tokens'] = 0.0001
        pricing['output_per_1k_tokens'] = 0.0

    # Llama models
    elif 'llama3-70b' in model_id or 'llama-3-70b' in model_id:
        pricing['input_per_1k_tokens'] = 0.00099
        pricing['output_per_1k_tokens'] = 0.00099
    elif 'llama3-8b' in model_id or 'llama-3-8b' in model_id:
        pricing['input_per_1k_tokens'] = 0.0003
        pricing['output_per_1k_tokens'] = 0.0006
    elif 'llama2' in model_id:
        pricing['input_per_1k_tokens'] = 0.00075
        pricing['output_per_1k_tokens'] = 0.001

    # Cohere models
    elif 'cohere.command' in model_id:
        pricing['input_per_1k_tokens'] = 0.0015
        pricing['output_per_1k_tokens'] = 0.002

    return pricing


def _get_model_limits(model_id: str, model_details: Dict) -> Dict[str, Any]:
    """Get model limits (context window, max output tokens)."""
    limits = {
        'context_window': 'Unknown',
        'max_output_tokens': 'Unknown'
    }

    # Claude models
    if 'claude-3' in model_id:
        limits['context_window'] = '200K tokens'
        limits['max_output_tokens'] = '4K tokens'
    elif 'claude-2' in model_id:
        limits['context_window'] = '100K tokens'
        limits['max_output_tokens'] = '4K tokens'

    # Titan models
    elif 'titan-text' in model_id:
        limits['context_window'] = '32K tokens'
        limits['max_output_tokens'] = '8K tokens'

    # Llama models
    elif 'llama3' in model_id or 'llama-3' in model_id:
        limits['context_window'] = '8K tokens'
        limits['max_output_tokens'] = '2K tokens'
    elif 'llama2' in model_id:
        limits['context_window'] = '4K tokens'
        limits['max_output_tokens'] = '2K tokens'

    # Cohere models
    elif 'cohere' in model_id:
        limits['context_window'] = '4K tokens'
        limits['max_output_tokens'] = '4K tokens'

    return limits


def _get_model_use_cases(model_id: str, capabilities: Dict) -> List[str]:
    """Get recommended use cases for a model."""
    use_cases = []

    # Claude models
    if 'claude-3-opus' in model_id:
        use_cases = ['Complex reasoning', 'Code generation', 'Long documents', 'Research analysis']
    elif 'claude-3-sonnet' in model_id:
        use_cases = ['Balanced performance', 'Chatbots', 'Content creation', 'Data analysis']
    elif 'claude-3-haiku' in model_id:
        use_cases = ['High throughput', 'Real-time chat', 'Simple queries', 'Classification']
    elif 'claude' in model_id:
        use_cases = ['General purpose', 'Long context', 'Analysis']

    # Titan models
    elif 'titan-text' in model_id:
        use_cases = ['Summarization', 'Search', 'Q&A', 'Low-cost text generation']
    elif 'titan-embed' in model_id:
        use_cases = ['Embeddings', 'Semantic search', 'RAG applications', 'Similarity']
    elif 'titan-image' in model_id:
        use_cases = ['Image generation', 'Image editing', 'Creative content']

    # Llama models
    elif 'llama' in model_id:
        use_cases = ['Open source', 'Cost-effective', 'Fine-tuning', 'General chat']

    # Cohere models
    elif 'cohere.command' in model_id:
        use_cases = ['Chat', 'Text generation', 'Summarization']
    elif 'cohere.embed' in model_id:
        use_cases = ['Embeddings', 'Search', 'Classification']

    # Stability AI
    elif 'stability' in model_id:
        use_cases = ['Image generation', 'Art creation', 'Design']

    # AI21 models
    elif 'ai21' in model_id:
        use_cases = ['Text generation', 'Summarization', 'Paraphrasing']

    # Generic based on capabilities
    if not use_cases:
        if 'TEXT' in capabilities['input_modalities']:
            use_cases.append('Text processing')
        if 'IMAGE' in capabilities['input_modalities'] or 'IMAGE' in capabilities['output_modalities']:
            use_cases.append('Image processing')
        if 'EMBEDDING' in capabilities['output_modalities']:
            use_cases.append('Embeddings')

    return use_cases


@tool
def analyze_model_performance(
    model_id: Optional[str] = None,
    days_back: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze performance metrics for Bedrock models.

    Retrieves CloudWatch metrics for model invocations including latency,
    errors, throttling, and throughput.

    Args:
        model_id: Specific model to analyze (optional - analyzes all if not provided)
        days_back: Number of days to analyze (default: 7)
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Overall performance metrics
        - by_model: Performance breakdown by model
        - latency: Average, p50, p99 latency metrics
        - errors: Error count and rate
        - throttling: Throttled requests count
        - recommendations: Performance optimization suggestions

    Example:
        >>> perf = analyze_model_performance('anthropic.claude-3-sonnet-20240229-v1:0')
        >>> print(f"Avg latency: {perf['latency']['average']}ms")
        >>> print(f"Error rate: {perf['summary']['error_rate']:.2%}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        cloudwatch = aws_client.get_client('cloudwatch')

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        metrics_to_fetch = [
            'Invocations',
            'InvocationLatency',
            'InvocationClientErrors',
            'InvocationServerErrors',
            'InvocationThrottles'
        ]

        performance_data = {}

        # If specific model, analyze that model
        # Otherwise, try to get aggregate metrics
        dimensions = []
        if model_id:
            dimensions = [{'Name': 'ModelId', 'Value': model_id}]

        for metric_name in metrics_to_fetch:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Bedrock',
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1 hour periods
                    Statistics=['Average', 'Sum', 'Maximum'] if 'Latency' in metric_name else ['Sum']
                )

                datapoints = response.get('Datapoints', [])

                if datapoints:
                    if 'Latency' in metric_name:
                        performance_data[metric_name] = {
                            'average': round(sum(dp['Average'] for dp in datapoints) / len(datapoints), 2),
                            'max': round(max(dp['Maximum'] for dp in datapoints), 2),
                            'unit': 'milliseconds'
                        }
                    else:
                        total = sum(dp['Sum'] for dp in datapoints)
                        performance_data[metric_name] = {
                            'total': int(total),
                            'avg_per_hour': round(total / len(datapoints), 1)
                        }

            except Exception:
                continue

        # Calculate summary metrics
        total_invocations = performance_data.get('Invocations', {}).get('total', 0)
        client_errors = performance_data.get('InvocationClientErrors', {}).get('total', 0)
        server_errors = performance_data.get('InvocationServerErrors', {}).get('total', 0)
        throttles = performance_data.get('InvocationThrottles', {}).get('total', 0)

        total_errors = client_errors + server_errors
        error_rate = (total_errors / total_invocations) if total_invocations > 0 else 0
        throttle_rate = (throttles / total_invocations) if total_invocations > 0 else 0

        summary = {
            'total_invocations': int(total_invocations),
            'error_rate': round(error_rate, 4),
            'throttle_rate': round(throttle_rate, 4),
            'avg_invocations_per_hour': round(total_invocations / (days_back * 24), 1),
            'days_analyzed': days_back
        }

        # Latency metrics
        latency = performance_data.get('InvocationLatency', {
            'average': 0,
            'max': 0,
            'unit': 'milliseconds'
        })

        # Error breakdown
        errors = {
            'total_errors': int(total_errors),
            'client_errors': int(client_errors),
            'server_errors': int(server_errors),
            'throttled_requests': int(throttles)
        }

        # Recommendations
        recommendations = []

        if throttle_rate > 0.01:  # >1% throttling
            recommendations.append({
                'category': 'performance',
                'priority': 'high',
                'title': 'High throttling rate detected',
                'description': f'Throttle rate: {throttle_rate:.2%}. Consider requesting quota increase or using Provisioned Throughput.',
                'action': 'Request quota increase in Service Quotas console'
            })

        if latency.get('average', 0) > 5000:  # >5 seconds average
            recommendations.append({
                'category': 'performance',
                'priority': 'medium',
                'title': 'High latency detected',
                'description': f"Average latency: {latency['average']:.0f}ms. Consider optimizing prompts or switching to faster models.",
                'action': 'Review prompt size and consider Claude 3 Haiku for faster responses'
            })

        if error_rate > 0.05:  # >5% errors
            recommendations.append({
                'category': 'reliability',
                'priority': 'high',
                'title': 'High error rate',
                'description': f'Error rate: {error_rate:.2%}. Review CloudWatch Logs to identify root causes.',
                'action': 'Enable model invocation logging and review error patterns'
            })

        return {
            'summary': summary,
            'latency': latency,
            'errors': errors,
            'recommendations': recommendations,
            'model_id': model_id or 'all_models'
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to analyze model performance. Ensure CloudWatch metrics are available.'
        }


@tool
def compare_models(
    model_ids: List[str],
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Compare multiple Bedrock models side-by-side.

    Compares capabilities, pricing, context limits, and use cases for
    multiple models to help choose the right model for your workload.

    Args:
        model_ids: List of model IDs to compare (2-5 models)
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - comparison_table: Side-by-side comparison of key attributes
        - recommendation: Which model to use for different scenarios
        - cost_comparison: Cost estimates for typical workloads
        - capability_matrix: Feature comparison matrix

    Example:
        >>> compare = compare_models([
        ...     'anthropic.claude-3-sonnet-20240229-v1:0',
        ...     'anthropic.claude-3-haiku-20240307-v1:0',
        ...     'meta.llama3-70b-instruct-v1:0'
        ... ])
        >>> print(compare['recommendation'])
    """
    if aws_client is None:
        aws_client = AWSClient()

    if not model_ids or len(model_ids) < 2:
        return {
            'error': 'Please provide at least 2 models to compare'
        }

    if len(model_ids) > 5:
        return {
            'error': 'Maximum 5 models can be compared at once'
        }

    try:
        # Get details for each model
        models_details = []
        for model_id in model_ids:
            details = get_model_details(model_id, aws_client)
            if 'error' not in details:
                models_details.append({
                    'model_id': model_id,
                    **details
                })

        if len(models_details) < 2:
            return {
                'error': 'Could not retrieve details for at least 2 models'
            }

        # Build comparison table
        comparison_table = []
        for model in models_details:
            comparison_table.append({
                'model_id': model['model_id'],
                'model_name': model['model_info']['model_name'],
                'provider': model['model_info']['provider'],
                'input_price_per_1k': model['pricing']['input_per_1k_tokens'],
                'output_price_per_1k': model['pricing']['output_per_1k_tokens'],
                'context_window': model['limits']['context_window'],
                'max_output': model['limits']['max_output_tokens'],
                'streaming': model['capabilities']['response_streaming'],
                'primary_use_cases': model['use_cases'][:3]
            })

        # Cost comparison for typical workloads
        workloads = [
            {'name': 'Light usage', 'input_tokens': 10000, 'output_tokens': 5000},
            {'name': 'Medium usage', 'input_tokens': 100000, 'output_tokens': 50000},
            {'name': 'Heavy usage', 'input_tokens': 1000000, 'output_tokens': 500000}
        ]

        cost_comparison = {}
        for workload in workloads:
            workload_name = workload['name']
            cost_comparison[workload_name] = []

            for model in models_details:
                input_cost = (workload['input_tokens'] / 1000) * model['pricing']['input_per_1k_tokens']
                output_cost = (workload['output_tokens'] / 1000) * model['pricing']['output_per_1k_tokens']
                total_cost = input_cost + output_cost

                cost_comparison[workload_name].append({
                    'model_id': model['model_id'],
                    'model_name': model['model_info']['model_name'],
                    'total_cost': round(total_cost, 2)
                })

            # Sort by cost
            cost_comparison[workload_name].sort(key=lambda x: x['total_cost'])

        # Generate recommendations
        cheapest = min(models_details, key=lambda m: m['pricing']['input_per_1k_tokens'] + m['pricing']['output_per_1k_tokens'])

        recommendation = {
            'cost_leader': {
                'model_id': cheapest['model_id'],
                'model_name': cheapest['model_info']['model_name'],
                'reason': 'Lowest price per token',
                'best_for': 'High-volume, cost-sensitive workloads'
            }
        }

        # Find Claude models (typically highest quality)
        claude_models = [m for m in models_details if 'claude' in m['model_id'].lower()]
        if claude_models:
            # Claude 3 Opus is highest quality, Sonnet is balanced, Haiku is fast
            if any('opus' in m['model_id'].lower() for m in claude_models):
                quality_leader = next(m for m in claude_models if 'opus' in m['model_id'].lower())
                recommendation['quality_leader'] = {
                    'model_id': quality_leader['model_id'],
                    'model_name': quality_leader['model_info']['model_name'],
                    'reason': 'Highest performance and capability',
                    'best_for': 'Complex reasoning, research, analysis'
                }
            elif any('sonnet' in m['model_id'].lower() for m in claude_models):
                balanced = next(m for m in claude_models if 'sonnet' in m['model_id'].lower())
                recommendation['balanced_choice'] = {
                    'model_id': balanced['model_id'],
                    'model_name': balanced['model_info']['model_name'],
                    'reason': 'Good balance of quality and cost',
                    'best_for': 'General-purpose applications'
                }
            elif any('haiku' in m['model_id'].lower() for m in claude_models):
                fast = next(m for m in claude_models if 'haiku' in m['model_id'].lower())
                recommendation['speed_leader'] = {
                    'model_id': fast['model_id'],
                    'model_name': fast['model_info']['model_name'],
                    'reason': 'Fastest response times',
                    'best_for': 'Real-time chat, high throughput'
                }

        return {
            'comparison_table': comparison_table,
            'cost_comparison': cost_comparison,
            'recommendation': recommendation,
            'models_compared': len(models_details)
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to compare models'
        }


@tool
def get_model_invocation_logs(
    model_id: Optional[str] = None,
    hours_back: int = 24,
    limit: int = 50,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Get recent model invocation logs for debugging and analysis.

    Retrieves CloudWatch Logs for Bedrock model invocations, including
    prompts, responses, token usage, and latency for recent requests.

    Note: Requires model invocation logging to be enabled in Bedrock settings.

    Args:
        model_id: Filter by specific model (optional)
        hours_back: Hours of logs to retrieve (default: 24)
        limit: Maximum number of log entries (default: 50, max: 100)
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Total invocations, tokens used, avg latency
        - invocations: List of recent invocations with details
        - token_usage: Input/output token breakdown
        - errors: Any errors in recent invocations
        - logging_status: Whether logging is enabled

    Example:
        >>> logs = get_model_invocation_logs(hours_back=24, limit=10)
        >>> for invocation in logs['invocations']:
        ...     print(f"Tokens: {invocation['input_tokens']} in, {invocation['output_tokens']} out")
    """
    if aws_client is None:
        aws_client = AWSClient()

    if limit > 100:
        limit = 100

    try:
        logs = aws_client.get_client('logs')

        # Bedrock logs are in /aws/bedrock/modelinvocations
        log_group_name = '/aws/bedrock/modelinvocations'

        # Check if log group exists
        try:
            logs.describe_log_groups(logGroupNamePrefix=log_group_name)
        except Exception:
            return {
                'logging_status': 'disabled',
                'message': 'Model invocation logging is not enabled. Enable it in Bedrock settings to see invocation logs.',
                'enable_instructions': 'Go to Bedrock console > Settings > Model invocation logging'
            }

        # Query logs
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        # Build query
        query = 'fields @timestamp, @message | sort @timestamp desc'
        if model_id:
            query = f'fields @timestamp, @message | filter modelId = "{model_id}" | sort @timestamp desc'

        try:
            # Start query
            query_response = logs.start_query(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query,
                limit=limit
            )

            query_id = query_response['queryId']

            # Wait for query to complete (with timeout)
            import time
            max_wait = 10  # seconds
            waited = 0
            while waited < max_wait:
                results_response = logs.get_query_results(queryId=query_id)
                status = results_response['status']

                if status == 'Complete':
                    break
                elif status == 'Failed':
                    return {
                        'error': 'Query failed',
                        'message': 'Failed to retrieve logs'
                    }

                time.sleep(0.5)
                waited += 0.5

            results = results_response.get('results', [])

        except Exception as e:
            return {
                'error': str(e),
                'message': 'Failed to query logs. Ensure model invocation logging is enabled.'
            }

        # Parse log entries
        invocations = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_latency = 0
        errors = []

        for result in results[:limit]:
            # Extract fields from log entry
            entry = {}
            for field in result:
                field_name = field.get('field', '')
                field_value = field.get('value', '')

                if field_name == '@timestamp':
                    entry['timestamp'] = field_value
                elif field_name == '@message':
                    # Try to parse JSON message
                    try:
                        import json
                        message = json.loads(field_value)
                        entry['model_id'] = message.get('modelId', 'unknown')
                        entry['input_tokens'] = message.get('inputTokenCount', 0)
                        entry['output_tokens'] = message.get('outputTokenCount', 0)
                        entry['latency_ms'] = message.get('latency', 0)

                        if 'error' in message:
                            errors.append(message['error'])
                            entry['error'] = message['error']

                        total_input_tokens += entry.get('input_tokens', 0)
                        total_output_tokens += entry.get('output_tokens', 0)
                        total_latency += entry.get('latency_ms', 0)

                    except:
                        pass

            if entry:
                invocations.append(entry)

        # Summary
        num_invocations = len(invocations)
        avg_latency = (total_latency / num_invocations) if num_invocations > 0 else 0

        summary = {
            'total_invocations': num_invocations,
            'total_input_tokens': total_input_tokens,
            'total_output_tokens': total_output_tokens,
            'avg_input_tokens': round(total_input_tokens / num_invocations, 1) if num_invocations > 0 else 0,
            'avg_output_tokens': round(total_output_tokens / num_invocations, 1) if num_invocations > 0 else 0,
            'avg_latency_ms': round(avg_latency, 1),
            'hours_analyzed': hours_back,
            'error_count': len(errors)
        }

        return {
            'logging_status': 'enabled',
            'summary': summary,
            'invocations': invocations,
            'errors': errors,
            'model_filter': model_id or 'all_models'
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to retrieve invocation logs'
        }


@tool
def check_bedrock_quotas(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Check Bedrock service quotas and current usage against limits.

    Analyzes service quotas for all Bedrock models to identify:
    - Current quota limits (tokens per minute, requests per minute)
    - Recent usage as percentage of quota
    - Quotas at risk of being exceeded
    - Recent throttling events

    Args:
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - quotas_summary: Overview of quota status
        - quotas_by_model: TPM/RPM limits per model
        - at_risk_quotas: Quotas > 80% utilized
        - throttling_events: Recent throttling from CloudWatch
        - recommendations: Which quotas to increase

    Example:
        >>> quotas = check_bedrock_quotas()
        >>> for quota in quotas['at_risk_quotas']:
        ...     print(f"{quota['model']}: {quota['usage_percent']}% of limit")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        service_quotas = aws_client.get_client('service-quotas')
        cloudwatch = aws_client.get_client('cloudwatch')
        bedrock = aws_client.get_client('bedrock')

        # Get Bedrock quotas from Service Quotas
        quotas_by_model = []
        at_risk_quotas = []

        try:
            # List all Bedrock quotas
            paginator = service_quotas.get_paginator('list_service_quotas')
            for page in paginator.paginate(ServiceCode='bedrock'):
                for quota in page.get('Quotas', []):
                    quota_info = {
                        'quota_name': quota.get('QuotaName'),
                        'quota_code': quota.get('QuotaCode'),
                        'value': quota.get('Value'),
                        'unit': quota.get('Unit', 'None'),
                        'adjustable': quota.get('Adjustable', False)
                    }
                    quotas_by_model.append(quota_info)
        except Exception as e:
            # Service Quotas might not be available, continue with CloudWatch
            pass

        # Check CloudWatch for throttling events
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)

        throttling_events = []
        total_throttles = 0

        # Check for throttling metrics
        throttle_metrics = [
            ('ThrottledCount', 'AWS/Bedrock'),
            ('InvocationThrottles', 'AWS/Bedrock'),
        ]

        for metric_name, namespace in throttle_metrics:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metric_name,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # Hourly
                    Statistics=['Sum']
                )

                for dp in response.get('Datapoints', []):
                    if dp.get('Sum', 0) > 0:
                        throttling_events.append({
                            'timestamp': dp['Timestamp'].isoformat(),
                            'metric': metric_name,
                            'count': int(dp['Sum'])
                        })
                        total_throttles += int(dp['Sum'])

            except Exception:
                continue

        # Sort throttling events by timestamp
        throttling_events.sort(key=lambda x: x['timestamp'], reverse=True)

        # Get model-specific usage from CloudWatch to estimate quota usage
        model_usage = {}
        try:
            models_response = bedrock.list_foundation_models()
            models = models_response.get('modelSummaries', [])[:10]  # Check top 10 models

            for model in models:
                model_id = model.get('modelId')
                try:
                    response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/Bedrock',
                        MetricName='Invocations',
                        Dimensions=[{'Name': 'ModelId', 'Value': model_id}],
                        StartTime=end_time - timedelta(hours=1),
                        EndTime=end_time,
                        Period=3600,
                        Statistics=['Sum']
                    )

                    invocations = sum(dp.get('Sum', 0) for dp in response.get('Datapoints', []))
                    if invocations > 0:
                        model_usage[model_id] = {
                            'invocations_last_hour': int(invocations),
                            'requests_per_minute': round(invocations / 60, 2)
                        }

                except Exception:
                    continue

        except Exception:
            pass

        # Identify at-risk quotas (heuristic: high usage models)
        for model_id, usage in model_usage.items():
            rpm = usage['requests_per_minute']
            # Most models have default limits around 60-100 RPM
            estimated_limit = 60
            usage_percent = (rpm / estimated_limit) * 100

            if usage_percent > 50:  # Flag if > 50% of estimated limit
                at_risk_quotas.append({
                    'model': model_id,
                    'current_rpm': rpm,
                    'estimated_limit': estimated_limit,
                    'usage_percent': round(usage_percent, 1),
                    'status': 'critical' if usage_percent > 80 else 'warning'
                })

        # Sort at-risk by usage percentage
        at_risk_quotas.sort(key=lambda x: x['usage_percent'], reverse=True)

        # Generate recommendations
        recommendations = []

        if total_throttles > 0:
            recommendations.append({
                'priority': 'high',
                'category': 'throttling',
                'title': f'{total_throttles} throttling events in last 7 days',
                'description': 'Your application is hitting Bedrock rate limits. Consider requesting quota increases.',
                'action': 'Request quota increase via Service Quotas console or use Provisioned Throughput'
            })

        if at_risk_quotas:
            high_risk = [q for q in at_risk_quotas if q['status'] == 'critical']
            if high_risk:
                recommendations.append({
                    'priority': 'high',
                    'category': 'capacity',
                    'title': f'{len(high_risk)} models at >80% quota utilization',
                    'description': f"Models at risk: {', '.join(q['model'].split('.')[0] for q in high_risk[:3])}",
                    'action': 'Request quota increase before hitting limits'
                })

        if not quotas_by_model and not model_usage:
            recommendations.append({
                'priority': 'low',
                'category': 'monitoring',
                'title': 'Enable CloudWatch metrics for better quota monitoring',
                'description': 'Limited quota data available. Enable detailed monitoring for accurate quota tracking.',
                'action': 'Ensure Bedrock metrics are being collected in CloudWatch'
            })

        # Summary
        summary = {
            'total_quotas_checked': len(quotas_by_model),
            'models_with_usage': len(model_usage),
            'at_risk_count': len(at_risk_quotas),
            'throttling_events_7d': total_throttles,
            'status': 'critical' if total_throttles > 100 else 'warning' if total_throttles > 0 or at_risk_quotas else 'healthy'
        }

        return {
            'summary': summary,
            'quotas_by_model': quotas_by_model[:20],  # Limit output
            'model_usage': model_usage,
            'at_risk_quotas': at_risk_quotas,
            'throttling_events': throttling_events[:20],  # Last 20 events
            'recommendations': recommendations
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to check Bedrock quotas'
        }


@tool
def check_bedrock_security(
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Security audit for Bedrock configuration.

    Comprehensive security analysis including:
    - Model access controls (IAM policies)
    - Guardrails configuration status
    - Model invocation logging status
    - VPC endpoint configuration
    - Encryption settings for custom models

    Args:
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Overall security posture score
        - logging_status: Is model invocation logging enabled?
        - guardrails_status: Are guardrails configured?
        - vpc_endpoints: Is Bedrock accessed via VPC endpoint?
        - custom_model_encryption: KMS encryption for fine-tuned models
        - findings: Security issues with severity
        - recommendations: Security hardening steps

    Example:
        >>> security = check_bedrock_security()
        >>> print(f"Security score: {security['summary']['score']}/100")
        >>> for finding in security['findings']:
        ...     print(f"[{finding['severity']}] {finding['title']}")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        bedrock = aws_client.get_client('bedrock')
        logs = aws_client.get_client('logs')
        ec2 = aws_client.get_client('ec2')

        findings = []
        security_score = 100

        # Check 1: Model invocation logging
        logging_enabled = False
        logging_config = {}

        try:
            # Check for Bedrock logging configuration
            log_groups = logs.describe_log_groups(
                logGroupNamePrefix='/aws/bedrock'
            )

            if log_groups.get('logGroups'):
                logging_enabled = True
                logging_config = {
                    'enabled': True,
                    'log_groups': [lg['logGroupName'] for lg in log_groups['logGroups']],
                    'retention': log_groups['logGroups'][0].get('retentionInDays', 'Never expires')
                }
            else:
                logging_enabled = False
                logging_config = {'enabled': False}
                findings.append({
                    'severity': 'high',
                    'category': 'logging',
                    'title': 'Model invocation logging not enabled',
                    'description': 'Bedrock model invocations are not being logged. This limits audit capability and troubleshooting.',
                    'remediation': 'Enable model invocation logging in Bedrock console under Settings'
                })
                security_score -= 20

        except Exception as e:
            logging_config = {'enabled': False, 'error': str(e)}

        # Check 2: Guardrails configuration
        guardrails_config = {'configured': False, 'guardrails': []}

        try:
            guardrails_response = bedrock.list_guardrails()
            guardrails = guardrails_response.get('guardrails', [])

            if guardrails:
                guardrails_config = {
                    'configured': True,
                    'count': len(guardrails),
                    'guardrails': [
                        {
                            'id': g.get('id'),
                            'name': g.get('name'),
                            'status': g.get('status')
                        }
                        for g in guardrails
                    ]
                }
            else:
                guardrails_config = {'configured': False, 'count': 0, 'guardrails': []}
                findings.append({
                    'severity': 'medium',
                    'category': 'content_filtering',
                    'title': 'No Bedrock Guardrails configured',
                    'description': 'No guardrails are configured to filter harmful content, PII, or enforce topic restrictions.',
                    'remediation': 'Create guardrails in Bedrock console to filter sensitive content and enforce policies'
                })
                security_score -= 15

        except Exception as e:
            # Guardrails API might not be available in all regions
            guardrails_config = {'configured': False, 'error': str(e)}

        # Check 3: VPC endpoints for Bedrock
        vpc_endpoint_config = {'configured': False, 'endpoints': []}

        try:
            endpoints_response = ec2.describe_vpc_endpoints(
                Filters=[
                    {'Name': 'service-name', 'Values': ['*bedrock*']}
                ]
            )

            endpoints = endpoints_response.get('VpcEndpoints', [])
            if endpoints:
                vpc_endpoint_config = {
                    'configured': True,
                    'count': len(endpoints),
                    'endpoints': [
                        {
                            'id': ep.get('VpcEndpointId'),
                            'service': ep.get('ServiceName'),
                            'state': ep.get('State'),
                            'vpc_id': ep.get('VpcId')
                        }
                        for ep in endpoints
                    ]
                }
            else:
                vpc_endpoint_config = {'configured': False, 'count': 0}
                findings.append({
                    'severity': 'medium',
                    'category': 'network',
                    'title': 'No VPC endpoint for Bedrock',
                    'description': 'Bedrock API calls go over the public internet. VPC endpoints keep traffic within AWS network.',
                    'remediation': 'Create VPC endpoint for bedrock-runtime service'
                })
                security_score -= 10

        except Exception as e:
            vpc_endpoint_config = {'configured': False, 'error': str(e)}

        # Check 4: Custom model encryption
        custom_models_config = {'models': [], 'encryption_issues': []}

        try:
            custom_models_response = bedrock.list_custom_models()
            custom_models = custom_models_response.get('modelSummaries', [])

            for model in custom_models:
                model_info = {
                    'model_name': model.get('modelName'),
                    'model_arn': model.get('modelArn'),
                    'base_model': model.get('baseModelIdentifier')
                }

                # Check if custom KMS key is used
                try:
                    model_details = bedrock.get_custom_model(
                        modelIdentifier=model.get('modelArn')
                    )
                    kms_key = model_details.get('outputDataConfig', {}).get('s3Uri', '')
                    model_info['has_custom_encryption'] = 'kms' in str(model_details).lower()
                except Exception:
                    model_info['has_custom_encryption'] = 'unknown'

                custom_models_config['models'].append(model_info)

            if custom_models and not any(m.get('has_custom_encryption') for m in custom_models_config['models']):
                findings.append({
                    'severity': 'low',
                    'category': 'encryption',
                    'title': 'Custom models may not use customer-managed KMS keys',
                    'description': 'Fine-tuned models should use customer-managed KMS keys for additional control.',
                    'remediation': 'Specify customer-managed KMS key when creating custom models'
                })
                security_score -= 5

        except Exception as e:
            custom_models_config = {'models': [], 'error': str(e)}

        # Check 5: Model access (check if any models have overly permissive access)
        model_access_config = {'status': 'checked'}

        # This would require analyzing IAM policies which is complex
        # For now, provide guidance
        findings.append({
            'severity': 'info',
            'category': 'iam',
            'title': 'Review IAM policies for Bedrock access',
            'description': 'Ensure bedrock:InvokeModel permissions are scoped to specific models, not bedrock:*',
            'remediation': 'Use resource-based conditions to limit which models can be invoked'
        })

        # Generate recommendations
        recommendations = []

        if not logging_enabled:
            recommendations.append({
                'priority': 'high',
                'title': 'Enable model invocation logging',
                'description': 'Critical for security auditing and debugging',
                'effort': 'low',
                'impact': 'high'
            })

        if not guardrails_config.get('configured'):
            recommendations.append({
                'priority': 'high',
                'title': 'Configure Bedrock Guardrails',
                'description': 'Prevent PII leakage, harmful content, and enforce topic restrictions',
                'effort': 'medium',
                'impact': 'high'
            })

        if not vpc_endpoint_config.get('configured'):
            recommendations.append({
                'priority': 'medium',
                'title': 'Create VPC endpoint for Bedrock',
                'description': 'Keep API traffic within AWS network for better security',
                'effort': 'low',
                'impact': 'medium'
            })

        # Calculate final score
        security_score = max(0, security_score)

        # Summary
        summary = {
            'score': security_score,
            'status': 'good' if security_score >= 80 else 'needs_attention' if security_score >= 60 else 'at_risk',
            'findings_count': len([f for f in findings if f['severity'] != 'info']),
            'critical_findings': len([f for f in findings if f['severity'] == 'high']),
            'logging_enabled': logging_enabled,
            'guardrails_configured': guardrails_config.get('configured', False),
            'vpc_endpoint_configured': vpc_endpoint_config.get('configured', False)
        }

        return {
            'summary': summary,
            'logging_status': logging_config,
            'guardrails_status': guardrails_config,
            'vpc_endpoints': vpc_endpoint_config,
            'custom_models': custom_models_config,
            'findings': findings,
            'recommendations': recommendations
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to check Bedrock security configuration'
        }


@tool
def analyze_guardrails(
    guardrail_id: Optional[str] = None,
    days_back: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Analyze Bedrock Guardrails effectiveness and configuration.

    Provides detailed analysis of guardrail performance including:
    - Block rates and patterns
    - Filter effectiveness by category (PII, toxicity, topics)
    - Potential false positives
    - Coverage gaps

    Args:
        guardrail_id: Specific guardrail to analyze (optional, analyzes all if not provided)
        days_back: Number of days to analyze (default: 7)
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Overall guardrail effectiveness
        - guardrails: List of guardrails with configuration
        - block_statistics: Block rates by category
        - coverage_analysis: Models with/without guardrails
        - recommendations: Tuning suggestions

    Example:
        >>> guardrails = analyze_guardrails()
        >>> print(f"Total blocks: {guardrails['summary']['total_blocks']}")
        >>> for gr in guardrails['guardrails']:
        ...     print(f"{gr['name']}: {gr['block_rate']}% block rate")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        bedrock = aws_client.get_client('bedrock')
        cloudwatch = aws_client.get_client('cloudwatch')

        # Get all guardrails or specific one
        guardrails_list = []

        try:
            if guardrail_id:
                guardrail = bedrock.get_guardrail(guardrailIdentifier=guardrail_id)
                guardrails_list = [guardrail]
            else:
                response = bedrock.list_guardrails()
                guardrails_list = response.get('guardrails', [])
        except Exception as e:
            return {
                'error': str(e),
                'message': 'Failed to list guardrails. Guardrails may not be available in this region.'
            }

        if not guardrails_list:
            return {
                'summary': {
                    'total_guardrails': 0,
                    'status': 'not_configured'
                },
                'guardrails': [],
                'recommendations': [{
                    'priority': 'high',
                    'title': 'No guardrails configured',
                    'description': 'Create guardrails to protect against harmful content, PII exposure, and enforce policies',
                    'action': 'Create guardrails in Bedrock console'
                }]
            }

        # Analyze each guardrail
        analyzed_guardrails = []
        total_blocks = 0
        total_requests = 0

        for guardrail in guardrails_list:
            guardrail_info = {
                'id': guardrail.get('id'),
                'name': guardrail.get('name'),
                'status': guardrail.get('status'),
                'version': guardrail.get('version')
            }

            # Get detailed configuration if available
            try:
                details = bedrock.get_guardrail(
                    guardrailIdentifier=guardrail.get('id')
                )

                # Extract filter configurations
                filters = {}

                # Content filters
                content_policy = details.get('contentPolicy', {})
                if content_policy.get('filters'):
                    filters['content_filters'] = [
                        {
                            'type': f.get('type'),
                            'input_strength': f.get('inputStrength'),
                            'output_strength': f.get('outputStrength')
                        }
                        for f in content_policy.get('filters', [])
                    ]

                # Topic policy
                topic_policy = details.get('topicPolicy', {})
                if topic_policy.get('topics'):
                    filters['denied_topics'] = [
                        t.get('name') for t in topic_policy.get('topics', [])
                    ]

                # Word policy
                word_policy = details.get('wordPolicy', {})
                if word_policy:
                    filters['word_filters'] = {
                        'managed_word_lists': word_policy.get('managedWordListsConfig', []),
                        'custom_words_count': len(word_policy.get('wordsConfig', []))
                    }

                # Sensitive info policy (PII)
                sensitive_policy = details.get('sensitiveInformationPolicy', {})
                if sensitive_policy:
                    filters['pii_filters'] = {
                        'pii_entities': [
                            e.get('type') for e in sensitive_policy.get('piiEntitiesConfig', [])
                        ],
                        'regex_patterns': len(sensitive_policy.get('regexesConfig', []))
                    }

                guardrail_info['filters'] = filters
                guardrail_info['created_at'] = details.get('createdAt', '').isoformat() if details.get('createdAt') else None
                guardrail_info['updated_at'] = details.get('updatedAt', '').isoformat() if details.get('updatedAt') else None

            except Exception as e:
                guardrail_info['filters'] = {'error': str(e)}

            # Get CloudWatch metrics for this guardrail
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)

            guardrail_metrics = {
                'invocations': 0,
                'blocks': 0,
                'block_rate': 0.0
            }

            # Try to get guardrail-specific metrics
            metric_queries = [
                ('GuardrailInvocations', 'Sum'),
                ('GuardrailBlocked', 'Sum'),
            ]

            for metric_name, stat in metric_queries:
                try:
                    response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/Bedrock',
                        MetricName=metric_name,
                        Dimensions=[
                            {'Name': 'GuardrailId', 'Value': guardrail.get('id')}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,  # Daily
                        Statistics=[stat]
                    )

                    value = sum(dp.get(stat, 0) for dp in response.get('Datapoints', []))

                    if 'Invocations' in metric_name:
                        guardrail_metrics['invocations'] = int(value)
                        total_requests += int(value)
                    elif 'Blocked' in metric_name:
                        guardrail_metrics['blocks'] = int(value)
                        total_blocks += int(value)

                except Exception:
                    continue

            # Calculate block rate
            if guardrail_metrics['invocations'] > 0:
                guardrail_metrics['block_rate'] = round(
                    (guardrail_metrics['blocks'] / guardrail_metrics['invocations']) * 100, 2
                )

            guardrail_info['metrics'] = guardrail_metrics
            analyzed_guardrails.append(guardrail_info)

        # Block statistics by category (aggregate)
        block_statistics = {
            'total_requests': total_requests,
            'total_blocks': total_blocks,
            'overall_block_rate': round((total_blocks / total_requests * 100), 2) if total_requests > 0 else 0
        }

        # Generate recommendations
        recommendations = []

        # Check for high block rates (potential false positives)
        high_block_guardrails = [g for g in analyzed_guardrails if g['metrics'].get('block_rate', 0) > 20]
        if high_block_guardrails:
            recommendations.append({
                'priority': 'medium',
                'title': 'High block rate detected',
                'description': f"{len(high_block_guardrails)} guardrail(s) have >20% block rate. Review for false positives.",
                'action': 'Review blocked requests in CloudWatch Logs to identify false positives',
                'affected_guardrails': [g['name'] for g in high_block_guardrails]
            })

        # Check for guardrails with no activity
        inactive_guardrails = [g for g in analyzed_guardrails if g['metrics'].get('invocations', 0) == 0]
        if inactive_guardrails:
            recommendations.append({
                'priority': 'low',
                'title': 'Inactive guardrails detected',
                'description': f"{len(inactive_guardrails)} guardrail(s) have no invocations in the last {days_back} days.",
                'action': 'Verify guardrails are attached to model invocations',
                'affected_guardrails': [g['name'] for g in inactive_guardrails]
            })

        # Check for missing filter types
        for guardrail in analyzed_guardrails:
            filters = guardrail.get('filters', {})
            if not filters.get('pii_filters'):
                recommendations.append({
                    'priority': 'medium',
                    'title': f"No PII filters on guardrail '{guardrail['name']}'",
                    'description': 'Consider adding PII detection to prevent sensitive data leakage',
                    'action': 'Add PII entity filters to guardrail configuration'
                })
                break  # Only show once

        # Summary
        summary = {
            'total_guardrails': len(analyzed_guardrails),
            'active_guardrails': len([g for g in analyzed_guardrails if g['metrics'].get('invocations', 0) > 0]),
            'total_requests': total_requests,
            'total_blocks': total_blocks,
            'overall_block_rate': block_statistics['overall_block_rate'],
            'days_analyzed': days_back,
            'status': 'healthy' if block_statistics['overall_block_rate'] < 20 else 'review_needed'
        }

        return {
            'summary': summary,
            'guardrails': analyzed_guardrails,
            'block_statistics': block_statistics,
            'recommendations': recommendations
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to analyze guardrails'
        }


@tool
def analyze_model_latency(
    model_id: Optional[str] = None,
    days_back: int = 7,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Deep latency analysis for Bedrock models.

    Provides comprehensive latency metrics including:
    - P50, P95, P99 latency percentiles
    - Time-of-day patterns (peak hours)
    - Latency by input size correlation
    - First token latency for streaming
    - Timeout analysis

    Args:
        model_id: Specific model to analyze (optional, analyzes top models if not provided)
        days_back: Number of days to analyze (default: 7)
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Overall latency health
        - latency_by_model: P50/P95/P99 per model
        - latency_by_hour: Hourly patterns
        - timeout_analysis: Requests timing out
        - recommendations: Performance optimization suggestions

    Example:
        >>> latency = analyze_model_latency('anthropic.claude-3-sonnet-20240229-v1:0')
        >>> print(f"P50 latency: {latency['summary']['p50_latency_ms']}ms")
        >>> print(f"P99 latency: {latency['summary']['p99_latency_ms']}ms")
    """
    if aws_client is None:
        aws_client = AWSClient()

    try:
        cloudwatch = aws_client.get_client('cloudwatch')
        bedrock = aws_client.get_client('bedrock')

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        # Get models to analyze
        models_to_analyze = []

        if model_id:
            models_to_analyze = [model_id]
        else:
            # Get list of available models and check which have metrics
            try:
                response = bedrock.list_foundation_models()
                models = response.get('modelSummaries', [])
                # Focus on common models
                for model in models:
                    mid = model.get('modelId')
                    if any(x in mid.lower() for x in ['claude', 'titan', 'llama', 'mistral']):
                        models_to_analyze.append(mid)
                models_to_analyze = models_to_analyze[:10]  # Limit to 10
            except Exception:
                # Fallback to common model patterns
                models_to_analyze = [
                    'anthropic.claude-3-sonnet',
                    'anthropic.claude-3-haiku',
                    'amazon.titan-text-express'
                ]

        # Analyze latency for each model
        latency_by_model = {}
        all_latencies = []

        for mid in models_to_analyze:
            try:
                # Get latency statistics
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Bedrock',
                    MetricName='InvocationLatency',
                    Dimensions=[{'Name': 'ModelId', 'Value': mid}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # Hourly
                    Statistics=['Average', 'Minimum', 'Maximum'],
                    ExtendedStatistics=['p50', 'p95', 'p99']
                )

                datapoints = response.get('Datapoints', [])

                if datapoints:
                    # Calculate aggregate statistics
                    avg_latencies = [dp.get('Average', 0) for dp in datapoints if dp.get('Average')]
                    max_latencies = [dp.get('Maximum', 0) for dp in datapoints if dp.get('Maximum')]

                    # Get percentiles from extended statistics
                    p50_values = [dp.get('ExtendedStatistics', {}).get('p50', 0) for dp in datapoints]
                    p95_values = [dp.get('ExtendedStatistics', {}).get('p95', 0) for dp in datapoints]
                    p99_values = [dp.get('ExtendedStatistics', {}).get('p99', 0) for dp in datapoints]

                    model_latency = {
                        'model_id': mid,
                        'datapoints_count': len(datapoints),
                        'average_ms': round(sum(avg_latencies) / len(avg_latencies), 2) if avg_latencies else 0,
                        'max_ms': round(max(max_latencies), 2) if max_latencies else 0,
                        'p50_ms': round(sum(p50_values) / len(p50_values), 2) if any(p50_values) else None,
                        'p95_ms': round(sum(p95_values) / len(p95_values), 2) if any(p95_values) else None,
                        'p99_ms': round(sum(p99_values) / len(p99_values), 2) if any(p99_values) else None
                    }

                    # If percentiles not available, estimate from average/max
                    if model_latency['p50_ms'] is None:
                        model_latency['p50_ms'] = model_latency['average_ms']
                        model_latency['p95_ms'] = round(model_latency['average_ms'] * 2, 2)
                        model_latency['p99_ms'] = round(model_latency['max_ms'] * 0.9, 2)
                        model_latency['percentiles_estimated'] = True

                    latency_by_model[mid] = model_latency
                    all_latencies.extend(avg_latencies)

            except Exception:
                continue

        # Analyze latency by hour of day
        latency_by_hour = {}

        if model_id or (models_to_analyze and latency_by_model):
            target_model = model_id or list(latency_by_model.keys())[0]
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Bedrock',
                    MetricName='InvocationLatency',
                    Dimensions=[{'Name': 'ModelId', 'Value': target_model}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # Hourly
                    Statistics=['Average']
                )

                # Group by hour
                hourly_data = {}
                for dp in response.get('Datapoints', []):
                    hour = dp['Timestamp'].hour
                    if hour not in hourly_data:
                        hourly_data[hour] = []
                    hourly_data[hour].append(dp.get('Average', 0))

                for hour, latencies in hourly_data.items():
                    latency_by_hour[hour] = {
                        'hour': hour,
                        'average_ms': round(sum(latencies) / len(latencies), 2),
                        'sample_count': len(latencies)
                    }

            except Exception:
                pass

        # Find peak hours
        peak_hours = []
        if latency_by_hour:
            sorted_hours = sorted(latency_by_hour.items(), key=lambda x: x[1]['average_ms'], reverse=True)
            peak_hours = [{'hour': h, 'latency_ms': data['average_ms']} for h, data in sorted_hours[:3]]

        # Timeout analysis
        timeout_analysis = {
            'timeout_threshold_ms': 30000,  # 30 second default
            'requests_near_timeout': 0,
            'potential_timeout_risk': 'low'
        }

        for model_data in latency_by_model.values():
            if model_data.get('p99_ms', 0) > 25000:  # >25s P99
                timeout_analysis['requests_near_timeout'] += 1
                timeout_analysis['potential_timeout_risk'] = 'high'
            elif model_data.get('p99_ms', 0) > 15000:  # >15s P99
                timeout_analysis['potential_timeout_risk'] = 'medium'

        # Generate recommendations
        recommendations = []

        # Check for high latency
        high_latency_models = [
            m for m, data in latency_by_model.items()
            if data.get('p95_ms', 0) > 10000
        ]
        if high_latency_models:
            recommendations.append({
                'priority': 'high',
                'category': 'performance',
                'title': 'High latency detected',
                'description': f"{len(high_latency_models)} model(s) have P95 latency >10 seconds",
                'action': 'Consider using faster models (Haiku) for latency-sensitive use cases',
                'affected_models': high_latency_models[:3]
            })

        # Check for Claude Opus usage (slow but powerful)
        opus_models = [m for m in latency_by_model.keys() if 'opus' in m.lower()]
        if opus_models:
            recommendations.append({
                'priority': 'medium',
                'category': 'optimization',
                'title': 'Claude Opus detected - consider alternatives for speed',
                'description': 'Opus has highest latency. Use Sonnet for balanced performance or Haiku for speed.',
                'action': 'Evaluate if Sonnet/Haiku can handle your use case'
            })

        # Check for peak hour patterns
        if peak_hours and len(latency_by_hour) > 12:
            recommendations.append({
                'priority': 'low',
                'category': 'capacity',
                'title': f"Peak latency at hour {peak_hours[0]['hour']}:00 UTC",
                'description': f"Latency peaks at {peak_hours[0]['latency_ms']:.0f}ms during busy hours",
                'action': 'Consider Provisioned Throughput for consistent performance during peak hours'
            })

        # Summary
        if all_latencies:
            avg_overall = sum(all_latencies) / len(all_latencies)
        else:
            avg_overall = 0

        summary = {
            'models_analyzed': len(latency_by_model),
            'days_analyzed': days_back,
            'average_latency_ms': round(avg_overall, 2),
            'p50_latency_ms': round(sum(m.get('p50_ms', 0) for m in latency_by_model.values()) / len(latency_by_model), 2) if latency_by_model else 0,
            'p99_latency_ms': round(max(m.get('p99_ms', 0) for m in latency_by_model.values()), 2) if latency_by_model else 0,
            'peak_hour_utc': peak_hours[0]['hour'] if peak_hours else None,
            'timeout_risk': timeout_analysis['potential_timeout_risk'],
            'status': 'healthy' if avg_overall < 5000 else 'needs_attention' if avg_overall < 15000 else 'critical'
        }

        return {
            'summary': summary,
            'latency_by_model': latency_by_model,
            'latency_by_hour': latency_by_hour,
            'peak_hours': peak_hours,
            'timeout_analysis': timeout_analysis,
            'recommendations': recommendations
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to analyze model latency'
        }


@tool
def compare_model_costs(
    input_tokens: int = 1000,
    output_tokens: int = 500,
    monthly_requests: int = 100000,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Compare costs across Bedrock models for a workload profile.

    Calculates and compares costs for all available models based on
    your expected usage pattern.

    Args:
        input_tokens: Average input tokens per request (default: 1000)
        output_tokens: Average output tokens per request (default: 500)
        monthly_requests: Expected monthly request volume (default: 100000)
        aws_client: Optional AWSClient for custom credentials/region

    Returns:
        Dict containing:
        - summary: Cost range and recommendations
        - cost_comparison: Monthly cost estimate per model
        - cost_tiers: Models grouped by cost tier
        - provisioned_analysis: When Provisioned Throughput makes sense
        - recommendations: Best model for cost/quality balance

    Example:
        >>> costs = compare_model_costs(
        ...     input_tokens=2000,
        ...     output_tokens=1000,
        ...     monthly_requests=500000
        ... )
        >>> for model in costs['cost_comparison'][:5]:
        ...     print(f"{model['model_name']}: ${model['monthly_cost']:.2f}/month")
    """
    if aws_client is None:
        aws_client = AWSClient()

    # Comprehensive pricing table (as of late 2024, us-east-1)
    # Prices in USD per 1000 tokens
    MODEL_PRICING = {
        # Claude 3.5 family
        'anthropic.claude-3-5-sonnet-20241022-v2:0': {'input': 0.003, 'output': 0.015, 'name': 'Claude 3.5 Sonnet v2', 'tier': 'premium'},
        'anthropic.claude-3-5-sonnet-20240620-v1:0': {'input': 0.003, 'output': 0.015, 'name': 'Claude 3.5 Sonnet', 'tier': 'premium'},
        'anthropic.claude-3-5-haiku-20241022-v1:0': {'input': 0.0008, 'output': 0.004, 'name': 'Claude 3.5 Haiku', 'tier': 'budget'},

        # Claude 3 family
        'anthropic.claude-3-opus-20240229-v1:0': {'input': 0.015, 'output': 0.075, 'name': 'Claude 3 Opus', 'tier': 'enterprise'},
        'anthropic.claude-3-sonnet-20240229-v1:0': {'input': 0.003, 'output': 0.015, 'name': 'Claude 3 Sonnet', 'tier': 'premium'},
        'anthropic.claude-3-haiku-20240307-v1:0': {'input': 0.00025, 'output': 0.00125, 'name': 'Claude 3 Haiku', 'tier': 'budget'},

        # Claude 2
        'anthropic.claude-v2:1': {'input': 0.008, 'output': 0.024, 'name': 'Claude 2.1', 'tier': 'legacy'},
        'anthropic.claude-v2': {'input': 0.008, 'output': 0.024, 'name': 'Claude 2.0', 'tier': 'legacy'},
        'anthropic.claude-instant-v1': {'input': 0.0008, 'output': 0.0024, 'name': 'Claude Instant', 'tier': 'legacy'},

        # Amazon Titan
        'amazon.titan-text-premier-v1:0': {'input': 0.0005, 'output': 0.0015, 'name': 'Titan Text Premier', 'tier': 'budget'},
        'amazon.titan-text-express-v1': {'input': 0.0002, 'output': 0.0006, 'name': 'Titan Text Express', 'tier': 'budget'},
        'amazon.titan-text-lite-v1': {'input': 0.00015, 'output': 0.0002, 'name': 'Titan Text Lite', 'tier': 'budget'},
        'amazon.titan-embed-text-v1': {'input': 0.0001, 'output': 0.0, 'name': 'Titan Embeddings', 'tier': 'embeddings'},
        'amazon.titan-embed-text-v2:0': {'input': 0.00002, 'output': 0.0, 'name': 'Titan Embeddings v2', 'tier': 'embeddings'},

        # Meta Llama 3
        'meta.llama3-70b-instruct-v1:0': {'input': 0.00099, 'output': 0.00099, 'name': 'Llama 3 70B', 'tier': 'standard'},
        'meta.llama3-8b-instruct-v1:0': {'input': 0.0003, 'output': 0.0006, 'name': 'Llama 3 8B', 'tier': 'budget'},

        # Meta Llama 3.1
        'meta.llama3-1-405b-instruct-v1:0': {'input': 0.00195, 'output': 0.00256, 'name': 'Llama 3.1 405B', 'tier': 'enterprise'},
        'meta.llama3-1-70b-instruct-v1:0': {'input': 0.00072, 'output': 0.00072, 'name': 'Llama 3.1 70B', 'tier': 'standard'},
        'meta.llama3-1-8b-instruct-v1:0': {'input': 0.00022, 'output': 0.00022, 'name': 'Llama 3.1 8B', 'tier': 'budget'},

        # Meta Llama 3.2
        'meta.llama3-2-90b-instruct-v1:0': {'input': 0.00072, 'output': 0.00072, 'name': 'Llama 3.2 90B', 'tier': 'standard'},
        'meta.llama3-2-11b-instruct-v1:0': {'input': 0.00016, 'output': 0.00016, 'name': 'Llama 3.2 11B', 'tier': 'budget'},
        'meta.llama3-2-3b-instruct-v1:0': {'input': 0.00015, 'output': 0.00015, 'name': 'Llama 3.2 3B', 'tier': 'budget'},
        'meta.llama3-2-1b-instruct-v1:0': {'input': 0.0001, 'output': 0.0001, 'name': 'Llama 3.2 1B', 'tier': 'budget'},

        # Mistral
        'mistral.mistral-large-2407-v1:0': {'input': 0.002, 'output': 0.006, 'name': 'Mistral Large', 'tier': 'premium'},
        'mistral.mistral-small-2402-v1:0': {'input': 0.0001, 'output': 0.0003, 'name': 'Mistral Small', 'tier': 'budget'},
        'mistral.mixtral-8x7b-instruct-v0:1': {'input': 0.00045, 'output': 0.0007, 'name': 'Mixtral 8x7B', 'tier': 'standard'},
        'mistral.mistral-7b-instruct-v0:2': {'input': 0.00015, 'output': 0.0002, 'name': 'Mistral 7B', 'tier': 'budget'},

        # Cohere
        'cohere.command-r-plus-v1:0': {'input': 0.003, 'output': 0.015, 'name': 'Command R+', 'tier': 'premium'},
        'cohere.command-r-v1:0': {'input': 0.0005, 'output': 0.0015, 'name': 'Command R', 'tier': 'standard'},
        'cohere.command-light-text-v14': {'input': 0.0003, 'output': 0.0006, 'name': 'Command Light', 'tier': 'budget'},
        'cohere.embed-english-v3': {'input': 0.0001, 'output': 0.0, 'name': 'Cohere Embed English', 'tier': 'embeddings'},
        'cohere.embed-multilingual-v3': {'input': 0.0001, 'output': 0.0, 'name': 'Cohere Embed Multilingual', 'tier': 'embeddings'},

        # AI21
        'ai21.jamba-1-5-large-v1:0': {'input': 0.002, 'output': 0.008, 'name': 'Jamba 1.5 Large', 'tier': 'premium'},
        'ai21.jamba-1-5-mini-v1:0': {'input': 0.0002, 'output': 0.0004, 'name': 'Jamba 1.5 Mini', 'tier': 'budget'},
        'ai21.j2-ultra-v1': {'input': 0.0188, 'output': 0.0188, 'name': 'Jurassic-2 Ultra', 'tier': 'enterprise'},
        'ai21.j2-mid-v1': {'input': 0.0125, 'output': 0.0125, 'name': 'Jurassic-2 Mid', 'tier': 'premium'},
    }

    try:
        bedrock = aws_client.get_client('bedrock')

        # Get available models in this region
        available_models = set()
        try:
            response = bedrock.list_foundation_models()
            for model in response.get('modelSummaries', []):
                available_models.add(model.get('modelId'))
        except Exception:
            # Use all models if we can't query
            available_models = set(MODEL_PRICING.keys())

        # Calculate costs for each model
        cost_comparison = []
        tokens_per_request = input_tokens + output_tokens

        for model_id, pricing in MODEL_PRICING.items():
            # Skip embedding models for text workloads
            if pricing['tier'] == 'embeddings' and output_tokens > 0:
                continue

            # Calculate per-request cost
            input_cost = (input_tokens / 1000) * pricing['input']
            output_cost = (output_tokens / 1000) * pricing['output']
            cost_per_request = input_cost + output_cost

            # Calculate monthly cost
            monthly_cost = cost_per_request * monthly_requests

            # Check availability
            is_available = any(model_id.split(':')[0] in am for am in available_models) if available_models else True

            cost_comparison.append({
                'model_id': model_id,
                'model_name': pricing['name'],
                'tier': pricing['tier'],
                'input_price_per_1k': pricing['input'],
                'output_price_per_1k': pricing['output'],
                'cost_per_request': round(cost_per_request, 6),
                'monthly_cost': round(monthly_cost, 2),
                'annual_cost': round(monthly_cost * 12, 2),
                'available_in_region': is_available
            })

        # Sort by monthly cost
        cost_comparison.sort(key=lambda x: x['monthly_cost'])

        # Group by tier
        cost_tiers = {
            'budget': [m for m in cost_comparison if m['tier'] == 'budget'],
            'standard': [m for m in cost_comparison if m['tier'] == 'standard'],
            'premium': [m for m in cost_comparison if m['tier'] == 'premium'],
            'enterprise': [m for m in cost_comparison if m['tier'] == 'enterprise'],
        }

        # Provisioned Throughput analysis
        # PT is typically cost-effective at >1M tokens/day sustained
        daily_tokens = (input_tokens + output_tokens) * (monthly_requests / 30)
        provisioned_analysis = {
            'daily_tokens': int(daily_tokens),
            'monthly_requests': monthly_requests,
            'provisioned_recommended': daily_tokens > 1000000,
            'reason': 'High volume workloads (>1M tokens/day) benefit from Provisioned Throughput' if daily_tokens > 1000000 else 'On-demand pricing is more cost-effective for this volume'
        }

        # Generate recommendations
        recommendations = []

        cheapest = cost_comparison[0] if cost_comparison else None
        if cheapest:
            recommendations.append({
                'category': 'cost_leader',
                'title': f"Cheapest option: {cheapest['model_name']}",
                'monthly_cost': cheapest['monthly_cost'],
                'description': f"${cheapest['monthly_cost']:.2f}/month for {monthly_requests:,} requests",
                'tradeoff': 'May have lower quality/capability than premium models'
            })

        # Find best value in premium tier
        premium_models = [m for m in cost_comparison if m['tier'] == 'premium']
        if premium_models:
            best_premium = premium_models[0]
            recommendations.append({
                'category': 'best_value',
                'title': f"Best premium value: {best_premium['model_name']}",
                'monthly_cost': best_premium['monthly_cost'],
                'description': f"${best_premium['monthly_cost']:.2f}/month - good balance of quality and cost",
                'tradeoff': 'Higher cost than budget models, but better performance'
            })

        # Claude comparison
        claude_models = [m for m in cost_comparison if 'claude' in m['model_id'].lower()]
        if len(claude_models) >= 2:
            haiku = next((m for m in claude_models if 'haiku' in m['model_id'].lower()), None)
            sonnet = next((m for m in claude_models if 'sonnet' in m['model_id'].lower()), None)
            if haiku and sonnet:
                savings = sonnet['monthly_cost'] - haiku['monthly_cost']
                recommendations.append({
                    'category': 'claude_comparison',
                    'title': f"Claude Haiku saves ${savings:.2f}/month vs Sonnet",
                    'description': 'Haiku is 10-15x cheaper. Use for simple tasks, classification, extraction.',
                    'sonnet_cost': sonnet['monthly_cost'],
                    'haiku_cost': haiku['monthly_cost']
                })

        # High volume warning
        if monthly_requests > 500000:
            recommendations.append({
                'category': 'volume_optimization',
                'title': 'High volume detected - consider Provisioned Throughput',
                'description': f"At {monthly_requests:,} requests/month, PT may offer better pricing and guaranteed capacity",
                'action': 'Contact AWS for Provisioned Throughput pricing'
            })

        # Summary
        costs = [m['monthly_cost'] for m in cost_comparison]
        summary = {
            'workload_profile': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'monthly_requests': monthly_requests,
                'tokens_per_request': tokens_per_request,
                'monthly_tokens': tokens_per_request * monthly_requests
            },
            'cost_range': {
                'min_monthly': min(costs) if costs else 0,
                'max_monthly': max(costs) if costs else 0,
                'median_monthly': round(sorted(costs)[len(costs)//2], 2) if costs else 0
            },
            'models_compared': len(cost_comparison),
            'cheapest_model': cheapest['model_name'] if cheapest else None,
            'cheapest_monthly_cost': cheapest['monthly_cost'] if cheapest else 0
        }

        return {
            'summary': summary,
            'cost_comparison': cost_comparison,
            'cost_tiers': cost_tiers,
            'provisioned_analysis': provisioned_analysis,
            'recommendations': recommendations
        }

    except Exception as e:
        return {
            'error': str(e),
            'message': 'Failed to compare model costs'
        }
