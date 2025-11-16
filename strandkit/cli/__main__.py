"""
Main CLI entry point for StrandKit.

Usage:
    strandkit init
    strandkit run debugger
    strandkit run debugger --profile dev --region us-east-1
"""

import sys
import argparse
from typing import Optional


def cmd_init():
    """Initialize a new StrandKit agent project."""
    print("🚀 Initializing StrandKit project...")
    # TODO: Implement project scaffolding
    pass


def cmd_run(agent_name: str, profile: Optional[str], region: Optional[str]):
    """Run a StrandKit agent interactively."""
    print(f"🤖 Starting {agent_name} agent...")
    # TODO: Implement interactive agent runner
    pass


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="StrandKit - AWS Strands Companion SDK"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init command
    subparsers.add_parser("init", help="Initialize a new project")

    # run command
    run_parser = subparsers.add_parser("run", help="Run an agent")
    run_parser.add_argument("agent", help="Agent name (e.g., 'debugger')")
    run_parser.add_argument("--profile", help="AWS profile")
    run_parser.add_argument("--region", help="AWS region")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "run":
        cmd_run(args.agent, args.profile, args.region)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
