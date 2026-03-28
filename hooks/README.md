# Hooks

This directory stores automatic guardrails and event-driven checks for the AI harness.

Hooks are not explicit operator commands. They run at specific lifecycle points.

Each hook folder contains an executable `run` wrapper. The wrapper delegates to `bin/aih`.

Recommended hook points:

- `pre-task/`
- `post-edit/`
- `pre-review/`
- `pre-verify/`
- `pre-close/`

Hooks should:

- gather context
- enforce safety and quality gates
- block unsafe automation when necessary

Hooks should not silently rewrite code.

## Examples

```bash
./hooks/pre-task/run
./hooks/post-edit/run
./hooks/pre-close/run --slug refund-approval
```
