# AWS Strands Agents Deep Dive: Integration Analysis

**Date**: 2025-11-17
**Repository Analyzed**: https://github.com/strands-agents/sdk-python
**Current StrandKit Version**: v1.0.0

---

## Executive Summary

After deep analysis of the AWS Strands Agents SDK, **StrandKit's current integration approach is incompatible with how Strands actually works**. We need significant architectural changes to properly integrate.

### The Problem

**What We Built:**
- Custom schema generation (`strandkit.strands.schemas`)
- Tool registry that returns dict schemas
- BaseAgent with custom Claude API integration
- Tools return plain dicts (compatible ✅)

**What Strands Actually Expects:**
- Functions decorated with `@tool` from strands package
- Direct function references, not schema dicts
- Agent class from strands handles Claude integration
- Tools return plain values (we're already doing this ✅)

**Compatibility Score: 30%**
- ✅ Tool return values: Compatible
- ❌ Tool decoration: Incompatible (we don't use @tool)
- ❌ Registry format: Incompatible (schemas vs functions)
- ❌ Agent integration: Incompatible (custom vs Strands Agent)

---

## How AWS Strands Actually Works

### 1. Tool Definition

**The Strands Way:**
```python
from strands import tool

@tool
def analyze_ec2_instance(instance_id: str) -> dict:
    """Analyze EC2 instance configuration and health.

    Args:
        instance_id: The EC2 instance ID to analyze

    Returns:
        dict: Instance details, metrics, and recommendations
    """
    # Implementation
    return {
        'instance_id': instance_id,
        'instance_type': 't3.micro',
        'health': 'healthy'
    }
```

**What the @tool decorator does:**
1. Extracts metadata from docstring and type hints
2. Auto-generates JSON schema for input validation
3. Handles async/sync execution
4. Formats results for the agent
5. Validates inputs against function signature

**Our Current Approach (Incompatible):**
```python
# We don't use @tool decorator
def analyze_ec2_instance(instance_id: str, aws_client=None) -> dict:
    """Analyze EC2 instance..."""
    # Implementation
    return {...}

# Then we manually generate schemas in registry.py
schemas.generate_tool_schema(analyze_ec2_instance)
```

### 2. Agent Creation

**The Strands Way:**
```python
from strands import Agent
from strandkit import analyze_ec2_instance, find_overpermissive_roles

# Create agent with decorated functions
agent = Agent(
    model="anthropic.claude-3-5-haiku",
    tools=[analyze_ec2_instance, find_overpermissive_roles],
    system_prompt="You are an AWS infrastructure analyst"
)

# Use the agent
response = agent("Are there any EC2 security issues?")
```

**Our Current Approach (Incompatible):**
```python
from strandkit import InfraDebuggerAgent

# Our custom agent using Anthropic SDK directly
agent = InfraDebuggerAgent(api_key="sk-ant-...")
result = agent.run("Are there any EC2 security issues?")
```

### 3. Tool Registration

**Strands supports multiple input formats:**

**A. Direct function references:**
```python
Agent(tools=[tool1, tool2, tool3])
```

**B. File paths:**
```python
Agent(tools=["./tools/analyze_ec2.py"])
```

**C. Module imports:**
```python
Agent(tools=["strandkit.tools.ec2:analyze_ec2_instance"])
```

**D. ToolProvider instances (Best for StrandKit!):**
```python
Agent(tools=[StrandKitToolProvider()])
```

**E. Tool directory auto-loading:**
```python
Agent(load_tools_from_directory=True)  # Loads from ./tools/
```

### 4. Tool Organization with ToolProvider

**ToolProvider Pattern** - Perfect for organizing StrandKit's 60 tools:

```python
from strands.tools import ToolProvider

class StrandKitToolProvider(ToolProvider):
    """Lazy-load StrandKit tools by category."""

    async def load_tools(self):
        """Return list of decorated tool functions."""
        from strandkit.tools import (
            cloudwatch, iam, cost, ec2, s3, ebs
        )

        # Return actual decorated functions
        return [
            cloudwatch.get_lambda_logs,
            cloudwatch.get_metric,
            iam.analyze_role,
            cost.get_cost_by_service,
            # ... all 60 tools
        ]

# Usage
agent = Agent(tools=[StrandKitToolProvider()])
```

---

## What Needs to Change in StrandKit

### ❌ BREAKING CHANGES REQUIRED

#### 1. Add strands-agents as Dependency

**File**: `requirements.txt`

```diff
 boto3>=1.26.0
 botocore>=1.29.0
+strands-agents>=0.1.0

 # Agent runtime (for Strands integration)
 anthropic>=0.18.0
```

#### 2. Decorate All 60 Tools with @tool

**Example**: `strandkit/tools/ec2.py`

```diff
+from strands import tool
 from typing import Dict, Any, Optional

-def analyze_ec2_instance(
+@tool
+def analyze_ec2_instance(
     instance_id: str,
-    aws_client = None,
+    aws_client = None,  # Strands supports dependency injection
     lookback_days: int = 7
 ) -> Dict[str, Any]:
     """
     Analyze EC2 instance configuration, health, and performance.

     Args:
         instance_id: EC2 instance ID (e.g., 'i-1234567890abcdef0')
+        aws_client: Optional AWS client (auto-injected by StrandKit)
         lookback_days: Days of CloudWatch metrics to analyze (default: 7)

     Returns:
-        dict: Instance analysis with health, metrics, and recommendations
+        Dict[str, Any]: Instance analysis with health, metrics, and recommendations
     """
     # Implementation stays the same!
     return {
         'instance_id': instance_id,
         'instance_type': 't3.micro',
         # ...
     }
```

**Impact**: Need to update all 60 tool functions across:
- `cloudwatch.py` (4 tools)
- `cloudformation.py` (1 tool)
- `iam.py` (3 tools)
- `iam_security.py` (8 tools)
- `cost.py` (4 tools)
- `cost_analytics.py` (6 tools)
- `cost_waste.py` (5 tools)
- `ec2.py` (5 tools)
- `ec2_advanced.py` (4 tools)
- `s3.py` (5 tools)
- `s3_advanced.py` (7 tools)
- `ebs.py` (6 tools)

#### 3. Replace Schema Generation with Function Export

**Current**: `strandkit/strands/schemas.py` (170 lines) - DELETE THIS

**New**: `strandkit/strands/provider.py`

```python
"""StrandKit ToolProvider for AWS Strands Agents."""

from strands.tools import ToolProvider
from typing import List, Any

class StrandKitToolProvider(ToolProvider):
    """
    Lazy-loading ToolProvider for all 60 StrandKit AWS tools.

    Usage:
        from strands import Agent
        from strandkit.strands import StrandKitToolProvider

        agent = Agent(tools=[StrandKitToolProvider()])
    """

    async def load_tools(self) -> List[Any]:
        """Load all StrandKit tools."""
        # Import all tool modules
        from strandkit.tools import (
            cloudwatch, cloudformation, iam, iam_security,
            cost, cost_analytics, cost_waste,
            ec2, ec2_advanced, s3, s3_advanced, ebs
        )

        # Return decorated functions
        return [
            # CloudWatch (4 tools)
            cloudwatch.get_lambda_logs,
            cloudwatch.get_metric,
            cloudwatch.get_log_insights,
            cloudwatch.get_recent_errors,

            # CloudFormation (1 tool)
            cloudformation.explain_changeset,

            # IAM (3 tools)
            iam.analyze_role,
            iam.explain_policy,
            iam.find_overpermissive_roles,

            # ... all 60 tools
        ]


class StrandKitCategoryProvider(ToolProvider):
    """
    ToolProvider that loads specific tool categories.

    Usage:
        # Security-focused agent
        agent = Agent(tools=[
            StrandKitCategoryProvider(['iam', 'iam_security', 'ec2'])
        ])

        # Cost optimization agent
        agent = Agent(tools=[
            StrandKitCategoryProvider(['cost', 'cost_analytics', 'cost_waste'])
        ])
    """

    def __init__(self, categories: List[str]):
        self.categories = categories

    async def load_tools(self) -> List[Any]:
        """Load tools from specified categories."""
        tools = []

        for category in self.categories:
            if category == 'cloudwatch':
                from strandkit.tools import cloudwatch
                tools.extend([
                    cloudwatch.get_lambda_logs,
                    cloudwatch.get_metric,
                    cloudwatch.get_log_insights,
                    cloudwatch.get_recent_errors,
                ])
            elif category == 'iam':
                from strandkit.tools import iam
                tools.extend([
                    iam.analyze_role,
                    iam.explain_policy,
                    iam.find_overpermissive_roles,
                ])
            # ... etc for all 12 categories

        return tools
```

#### 4. Replace Registry with Simple Function Lists

**Current**: `strandkit/strands/registry.py` (360 lines) - SIMPLIFY THIS

**New**: `strandkit/strands/registry.py`

```python
"""Tool registration for Strands integration."""

from typing import List, Any

def get_all_tools() -> List[Any]:
    """
    Get all 60 StrandKit tools as decorated functions.

    Usage:
        from strands import Agent
        from strandkit.strands import get_all_tools

        agent = Agent(tools=get_all_tools())

    Returns:
        List of 60 @tool-decorated functions
    """
    from strandkit.tools import (
        cloudwatch, cloudformation, iam, iam_security,
        cost, cost_analytics, cost_waste,
        ec2, ec2_advanced, s3, s3_advanced, ebs
    )

    return [
        # All 60 tools as decorated functions
        cloudwatch.get_lambda_logs,
        cloudwatch.get_metric,
        # ... etc
    ]


def get_tools_by_category(category: str) -> List[Any]:
    """
    Get tools for a specific category.

    Args:
        category: Tool category (cloudwatch, iam, cost, ec2, s3, ebs, etc.)

    Returns:
        List of tools for that category

    Example:
        # Security-focused agent
        agent = Agent(tools=(
            get_tools_by_category('iam') +
            get_tools_by_category('iam_security') +
            get_tools_by_category('ec2')
        ))
    """
    from strandkit.tools import (
        cloudwatch, cloudformation, iam, iam_security,
        cost, cost_analytics, cost_waste,
        ec2, ec2_advanced, s3, s3_advanced, ebs
    )

    CATEGORY_MAP = {
        'cloudwatch': [
            cloudwatch.get_lambda_logs,
            cloudwatch.get_metric,
            cloudwatch.get_log_insights,
            cloudwatch.get_recent_errors,
        ],
        'iam': [
            iam.analyze_role,
            iam.explain_policy,
            iam.find_overpermissive_roles,
        ],
        # ... all 12 categories
    }

    return CATEGORY_MAP.get(category, [])


def list_tool_categories() -> List[str]:
    """List all available tool categories."""
    return [
        'cloudwatch', 'cloudformation', 'iam', 'iam_security',
        'cost', 'cost_analytics', 'cost_waste',
        'ec2', 'ec2_advanced', 's3', 's3_advanced', 'ebs'
    ]
```

#### 5. Deprecate BaseAgent (Or Make It a Wrapper)

**Current**: `strandkit/core/base_agent.py` (425 lines) - DEPRECATE or WRAP

**Option A: Deprecate** (Recommended)
- Remove our custom agent implementation
- Users should use `strands.Agent` directly
- Update docs to show Strands usage

**Option B: Wrapper** (For backward compatibility)
```python
"""Backward-compatible wrapper for Strands Agent."""

from strands import Agent as StrandsAgent
from strandkit.strands import get_all_tools
import warnings

class BaseAgent:
    """
    DEPRECATED: Use strands.Agent directly.

    This class is maintained for backward compatibility but will be
    removed in v2.0.0. Please migrate to the official Strands SDK:

        from strands import Agent
        from strandkit.strands import get_all_tools

        agent = Agent(tools=get_all_tools())
    """

    def __init__(self, profile=None, region=None, api_key=None, **kwargs):
        warnings.warn(
            "BaseAgent is deprecated. Use strands.Agent instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # Wrap Strands Agent
        self._agent = StrandsAgent(
            tools=get_all_tools(),
            **kwargs
        )

    def run(self, query: str):
        """Run query through Strands agent."""
        return self._agent(query)
```

---

## Migration Path for Users

### Before (StrandKit v1.0.0)

```python
from strandkit import InfraDebuggerAgent

agent = InfraDebuggerAgent(api_key="sk-ant-...")
result = agent.run("Find security issues in my IAM roles")
print(result['answer'])
```

### After (StrandKit v2.0.0)

```python
from strands import Agent
from strandkit.strands import get_all_tools

# Full integration with Strands
agent = Agent(
    model="anthropic.claude-3-5-haiku",
    tools=get_all_tools(),  # All 60 StrandKit tools
    system_prompt="You are an AWS infrastructure security analyst"
)

response = agent("Find security issues in my IAM roles")
print(response)
```

**Or with categories:**
```python
from strands import Agent
from strandkit.strands import get_tools_by_category

# Specialized security agent
security_agent = Agent(
    tools=(
        get_tools_by_category('iam') +
        get_tools_by_category('iam_security') +
        get_tools_by_category('ec2')
    ),
    model="anthropic.claude-3-5-sonnet"
)
```

**Or with ToolProvider:**
```python
from strands import Agent
from strandkit.strands import StrandKitToolProvider

# Lazy-loaded tools
agent = Agent(tools=[StrandKitToolProvider()])
```

---

## Backward Compatibility Strategy

### Keep Standalone Usage Working

Tools should still work standalone without Strands:

```python
# This should still work!
from strandkit import find_overpermissive_roles

results = find_overpermissive_roles()
print(results)
```

**How?** The `@tool` decorator doesn't break standalone usage:
- Decorated functions are still callable normally
- Return values unchanged
- No Strands dependency required for direct calls

### Version the Breaking Changes

**v1.x (Current):**
- Custom BaseAgent
- Schema-based registry
- Example agents

**v2.0.0 (Future):**
- Full Strands integration
- @tool decorators on all functions
- BaseAgent deprecated with warnings
- StrandKitToolProvider as primary interface

**Migration Period:**
- v1.5.0: Add @tool decorators, keep both approaches
- v1.5.0: Add deprecation warnings to BaseAgent
- v2.0.0: Remove BaseAgent, schemas.py fully

---

## Recommended Action Plan

### Phase 1: Add @tool Decorators (v1.5.0)
1. ✅ Add `strands-agents` to requirements.txt
2. ✅ Decorate all 60 functions with `@tool`
3. ✅ Test standalone usage still works
4. ✅ Test with simple Strands agent

### Phase 2: Create ToolProviders (v1.5.0)
1. ✅ Create `StrandKitToolProvider`
2. ✅ Create `StrandKitCategoryProvider`
3. ✅ Update `get_all_tools()` to return functions
4. ✅ Update `get_tools_by_category()` to return functions
5. ✅ Keep old schema-based functions for backward compat

### Phase 3: Update Documentation (v1.5.0)
1. ✅ Update README with Strands examples
2. ✅ Add migration guide
3. ✅ Create Strands usage examples
4. ✅ Add deprecation warnings to BaseAgent docs

### Phase 4: Deprecate Old Approach (v2.0.0)
1. ✅ Remove BaseAgent
2. ✅ Remove schemas.py
3. ✅ Remove old registry format
4. ✅ Update all examples to use Strands

---

## Benefits of Proper Integration

### For Users
1. **Official AWS Framework**: Use AWS-supported Strands SDK
2. **Multi-Agent Support**: Leverage Strands' agent swarms, handoffs
3. **Model Agnostic**: Use Bedrock, OpenAI, Gemini, not just Claude
4. **Enterprise Features**: Memory, observability, guardrails from Strands
5. **MCP Integration**: Use Model Context Protocol tools alongside StrandKit

### For StrandKit
1. **Less Code to Maintain**: Remove 500+ lines of custom agent code
2. **Better Positioning**: True companion to Strands, not competitor
3. **Ecosystem Benefits**: Part of the Strands ecosystem
4. **Focus on Tools**: Concentrate on AWS integrations, not agent framework

---

## Conclusion

**Current State**: StrandKit has its own agent framework incompatible with Strands

**Required Changes**: Significant - need to decorate 60 functions, rewrite registry, deprecate BaseAgent

**Recommendation**:
- Implement in v1.5.0 as additive features
- Maintain backward compatibility during migration
- Full cutover in v2.0.0

**Effort Estimate**:
- Phase 1: 8-16 hours (decorate functions)
- Phase 2: 4-8 hours (create providers)
- Phase 3: 4-8 hours (documentation)
- Total: 16-32 hours of work

**Value**: Positions StrandKit as a true companion to AWS Strands Agents with proper integration
