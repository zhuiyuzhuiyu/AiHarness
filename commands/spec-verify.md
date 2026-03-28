# /spec-verify

## Purpose

Run validation and record results in `test-report.md`.

## Inputs

- Current code changes
- Project test commands

## Outputs

- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/test-report.md`

## Rules

- Run targeted tests before broad suites
- Include reproduction notes for failures
- Use browser-driven checks only when needed
