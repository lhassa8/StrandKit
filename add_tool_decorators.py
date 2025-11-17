#!/usr/bin/env python3
"""
Script to add @tool decorators to all StrandKit tool functions.

This script:
1. Finds all tool files in strandkit/tools/
2. Adds 'from strands import tool' import if not present
3. Adds @tool decorator before each function definition
"""

import re
from pathlib import Path

# Tool files to process
TOOL_FILES = [
    'strandkit/tools/cloudformation.py',
    'strandkit/tools/iam.py',
    'strandkit/tools/iam_security.py',
    'strandkit/tools/cost.py',
    'strandkit/tools/cost_analytics.py',
    'strandkit/tools/cost_waste.py',
    'strandkit/tools/ec2.py',
    'strandkit/tools/ec2_advanced.py',
    'strandkit/tools/s3.py',
    'strandkit/tools/s3_advanced.py',
    'strandkit/tools/ebs.py',
]

def add_tool_decorator(filepath):
    """Add @tool decorator to all functions in a file."""
    print(f"\nProcessing {filepath}...")

    path = Path(filepath)
    if not path.exists():
        print(f"  ❌ File not found: {filepath}")
        return False

    content = path.read_text()

    # Check if already has strands import
    has_strands_import = 'from strands import tool' in content

    # Add import if needed
    if not has_strands_import:
        # Find the last import line
        import_pattern = r'(from .+ import .+|import .+)\n'
        imports = list(re.finditer(import_pattern, content))

        if imports:
            # Add after the last import
            last_import = imports[-1]
            insert_pos = last_import.end()
            content = (
                content[:insert_pos] +
                'from strands import tool\n' +
                content[insert_pos:]
            )
            print(f"  ✅ Added 'from strands import tool' import")
        else:
            print(f"  ⚠️  Could not find import section")
            return False
    else:
        print(f"  ℹ️  Already has strands import")

    # Find all function definitions and add @tool decorator
    # Pattern: "def function_name(" at start of line (no @tool before it)
    pattern = r'\n(def \w+\()'

    functions_decorated = 0

    def add_decorator(match):
        nonlocal functions_decorated
        # Check if there's already a @tool decorator
        start_pos = match.start()
        # Look back up to 50 chars to see if @tool is there
        lookback = content[max(0, start_pos-50):start_pos]
        if '@tool' in lookback:
            # Already decorated
            return match.group(0)

        functions_decorated += 1
        return '\n@tool\n' + match.group(1)

    content = re.sub(pattern, add_decorator, content)

    if functions_decorated > 0:
        # Write back
        path.write_text(content)
        print(f"  ✅ Added @tool to {functions_decorated} functions")
        return True
    else:
        print(f"  ℹ️  No functions needed decoration")
        return False

def main():
    """Process all tool files."""
    print("=" * 60)
    print("Adding @tool decorators to StrandKit tools")
    print("=" * 60)

    success_count = 0
    total_count = 0

    for filepath in TOOL_FILES:
        total_count += 1
        if add_tool_decorator(filepath):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"✅ Processed {success_count}/{total_count} files successfully")
    print("=" * 60)

if __name__ == '__main__':
    main()
