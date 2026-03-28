# Commands

This directory stores operator-invoked workflow entrypoints for the AI harness.

Use commands to start a specific stage of the delivery flow without retyping the full prompt every time.

Executable entrypoints live alongside the markdown specs:

- `commands/spec-intake`
- `commands/spec-design`
- `commands/spec-plan`
- `commands/spec-build`
- `commands/spec-review`
- `commands/spec-verify`
- `commands/spec-close`

All command wrappers call `bin/aih`, which dispatches to `scripts/harness.py`.

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

## Examples

```bash
./commands/spec-intake --title "Add refund approval flow" --source "JIRA-123"
./commands/spec-design --slug refund-approval
./commands/spec-plan --slug refund-approval
```
