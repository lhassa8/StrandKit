"""
Infrastructure Debugger Agent for StrandKit.

This module re-exports the working Strands-powered InfraDebuggerAgent.
For the actual implementation, see strandkit.strands.agents.infra_debugger.

Example usage:
    >>> from strandkit import InfraDebuggerAgent
    >>> agent = InfraDebuggerAgent(profile="dev", region="us-east-1")
    >>>
    >>> # Diagnose Lambda errors
    >>> response = agent.run("Why is my auth-api Lambda failing?")
    >>> print(response['answer'])
    >>>
    >>> # Check for metric spikes
    >>> response = agent.run("Show me error spikes in the last 2 hours")
"""

# Re-export the working Strands agent
from strandkit.strands.agents.infra_debugger import InfraDebuggerAgent

__all__ = ['InfraDebuggerAgent']
