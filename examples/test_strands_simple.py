#!/usr/bin/env python3
"""
Simple test of InfraDebuggerAgent - pass API key as argument.

Usage:
    python3 test_strands_simple.py YOUR_API_KEY
"""
import sys
import os

if len(sys.argv) < 2:
    print("Usage: python3 test_strands_simple.py YOUR_API_KEY")
    sys.exit(1)

api_key = sys.argv[1]

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strandkit import InfraDebuggerAgent

def test_agent(api_key):
    print("="*80)
    print("Testing InfraDebuggerAgent with Claude")
    print("="*80)

    # Create agent with API key and verbose mode
    agent = InfraDebuggerAgent(api_key=api_key, verbose=True)

    # Simple query
    query = "What tools do you have available for debugging AWS infrastructure?"

    print(f"\nQuery: {query}\n")
    print("="*80)
    print("Agent working...")
    print("="*80)

    try:
        result = agent.run(query)

        print("\n" + "="*80)
        print("RESULT")
        print("="*80)
        print(f"\nAnswer:\n{result['answer']}\n")
        print(f"Tools called: {len(result['tool_calls'])}")
        print(f"Iterations: {result['iterations']}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent(api_key)
    sys.exit(0 if success else 1)
