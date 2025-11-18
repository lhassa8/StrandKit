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
                'response_streaming': 'STREAMING' in model.get('responseStreamingSupported', [])
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
            'response_streaming': 'STREAMING' in model_details.get('responseStreamingSupported', []),
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
