---
name: Bug Report
about: Report a problem or unexpected behavior
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

A clear and concise description of the problem.

## Steps to Reproduce

1. Configure environment with '...'
2. Run command '...'
3. Observe error '...'

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened.

## Error Logs

```
Paste relevant error logs here
```

## Environment

- **Python version**: [e.g., 3.11.0]
- **Package version**: [output of `rest2-ons --version`]
- **Operating System**: [e.g., Ubuntu 22.04]
- **Installation method**: [e.g., uv tool install, setup.sh, make install, Docker]
- **Docker** (if applicable): [e.g., yes/no, image version]

## Sample Data

If possible, attach or describe the data causing the problem (without sensitive information).

## Configuration File

Paste your `train.toml` or `infer.toml` if relevant. Remove bucket names and credentials first.

```toml
# Paste your sanitized train.toml or infer.toml
```

## Exit Code and Run Summary

The exit code of the command and the run-summary line it printed to standard output.

```
exit code:
run summary:
```

## Additional Context

Any other relevant information about the problem.
