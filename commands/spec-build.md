# /spec-build

## Purpose

Execute the highest-priority implementation task.

## Inputs

- `tasks.md`
- Current repository state

## Outputs

- Code changes
- Updated task state

## Rules

- Validate the narrowest proof first
- Stop and escalate if risk gates are hit
- Prefer one reviewable slice at a time
