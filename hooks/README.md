# Hooks

This directory stores automatic guardrails and event-driven checks for the AI harness.

Hooks are not explicit operator commands. They run at specific lifecycle points.

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
