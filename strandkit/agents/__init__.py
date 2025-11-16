"""
Prebuilt agent templates for StrandKit.

This package contains ready-to-use agent templates:
- InfraDebuggerAgent: Debug AWS infrastructure issues
- (Future) IAMReviewerAgent: Review IAM policies
- (Future) CostAnalystAgent: Analyze AWS costs

Each agent is a subclass of BaseAgent with:
- Curated system prompt
- Pre-configured tools
- Domain-specific processing
"""

from strandkit.agents.infra_debugger import InfraDebuggerAgent

__all__ = ["InfraDebuggerAgent"]
