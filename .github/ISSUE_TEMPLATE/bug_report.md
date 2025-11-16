---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Describe the bug
A clear and concise description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1. Import '...'
2. Call function '...'
3. With parameters '...'
4. See error

## Expected behavior
A clear and concise description of what you expected to happen.

## Code Example
```python
# Minimal reproducible example
from strandkit.tools.cloudwatch import get_lambda_logs

result = get_lambda_logs("my-function")
# Error occurs here
```

## Error Message
```
Paste the full error message and stack trace here
```

## Environment
- **Python version**: [e.g., 3.9.7]
- **StrandKit version**: [e.g., 0.1.0]
- **OS**: [e.g., Ubuntu 22.04, macOS 13.0]
- **AWS Region**: [e.g., us-east-1]
- **boto3 version**: [run `pip show boto3`]

## Additional context
Add any other context about the problem here.

## Possible Solution
If you have ideas on how to fix this, please share them here.
