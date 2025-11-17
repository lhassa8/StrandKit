#!/usr/bin/env python3
"""
Test the InfraDebuggerAgent with a real query.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strandkit import InfraDebuggerAgent

def test_agent():
    print("="*80)
    print("Testing InfraDebuggerAgent with Claude")
    print("="*80)

    # Create agent with verbose mode to see tool calls
    agent = InfraDebuggerAgent(verbose=True)

    # Test with a simple query that checks account resources
    query = """
    Can you check if there are any Auto Scaling Groups or Load Balancers
    in my AWS account? Just give me a quick summary of what you find.
    """

    print(f"\nQuery: {query.strip()}\n")
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

        if result['tool_calls']:
            print("\nTool calls made:")
            for i, call in enumerate(result['tool_calls'], 1):
                print(f"  {i}. {call['tool']}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent()
    sys.exit(0 if success else 1)
