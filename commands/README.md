# Commands

This directory stores operator-invoked workflow entrypoints for the AI harness.

Use commands to start a specific stage of the delivery flow without retyping the full prompt every time.

Recommended command set:

- `spec-intake.md`
- `spec-design.md`
- `spec-plan.md`
- `spec-build.md`
- `spec-review.md`
- `spec-verify.md`
- `spec-close.md`

Each command should define:

- Purpose
- Expected input
- Required context
- Output files
- Escalation rules

Commands are explicit entrypoints. They do not run automatically.
