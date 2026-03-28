# AiHarness

This repository is a Git-managed home for reusable AI workflow skills, templates, and operating conventions.

## Layout

- `skills/`: Codex skills managed in Git
- `templates/`: reusable spec templates
- `commands/`: explicit workflow entrypoints
- `hooks/`: automatic guardrails and checkpoints
- `docs/`: workflow and operating notes

## Current Skill

- `company-ai-harness`

## Workflow Interfaces

- Commands define the explicit operator entrypoints for each stage.
- Hooks define the automatic checks that run around those stages.

## CLI

Use the shared CLI through `bin/aih` or the wrappers in `commands/` and `hooks/`.

Examples:

```bash
./commands/spec-intake --title "Add refund approval flow" --source "JIRA-123"
./commands/spec-design --slug refund-approval
./commands/spec-plan --slug refund-approval
./commands/spec-build --slug refund-approval
./hooks/post-edit/run
```

## Codex Integration

Point Codex at the skill in this repo by linking:

```bash
ln -s /Users/zyh/Desktop/AiHarness/skills/company-ai-harness /Users/zyh/.codex/skills/company-ai-harness
```
