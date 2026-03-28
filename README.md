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

## Codex Integration

Point Codex at the skill in this repo by linking:

```bash
ln -s /Users/zyh/Desktop/AiHarness/skills/company-ai-harness /Users/zyh/.codex/skills/company-ai-harness
```
