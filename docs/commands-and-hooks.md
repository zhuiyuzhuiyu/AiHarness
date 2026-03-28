# Commands And Hooks

## Purpose

This document explains the difference between explicit workflow entrypoints and automatic guardrails.

## Commands

Commands are user-invoked actions. They are the operator interface for starting a stage in the workflow.

Recommended lifecycle:

1. `/spec-intake`
2. `/spec-design`
3. `/spec-plan`
4. `/spec-build`
5. `/spec-review`
6. `/spec-verify`
7. `/spec-close`

In this repository, those commands are implemented as executable wrappers under `commands/` and all route through `bin/aih`.

## Hooks

Hooks run automatically at lifecycle checkpoints.

Recommended checkpoints:

1. `pre-task`
2. `post-edit`
3. `pre-review`
4. `pre-verify`
5. `pre-close`

In this repository, each hook checkpoint has a `run` wrapper inside its folder. A scheduler, slash-command runner, or external orchestrator can invoke those wrappers directly.

## Design Rule

Use commands to start work.

Use hooks to enforce process quality and safety.

Do not use hooks for hidden implementation changes.
