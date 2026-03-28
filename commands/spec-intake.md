# /spec-intake

## Purpose

Turn a user request or issue URL into `requirements.md`.

## Inputs

- Natural language requirement
- Jira, Linear, or GitHub issue URL
- Existing project docs and code

## Required Context

- `.docs/ARCHITECTURE.md`
- `.docs/SECURITY.md`
- `.docs/CODING_GUIDELINES.md`
- `.docs/docs.md`

## Outputs

- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/requirements.md`

## Rules

- Capture scope and non-goals
- Record acceptance criteria
- Note assumptions and open questions
- Mark security or approval-sensitive items
