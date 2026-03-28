# /spec-design

## Purpose

Generate `design.md` from the approved requirement and the current repository state.

## Inputs

- `requirements.md`
- Current codebase
- Project docs

## Outputs

- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/design.md`

## Rules

- Map to the current repo, not a greenfield solution
- List affected files and modules
- Include security, failure, and rollback considerations
- Split into slices if the change spans multiple subsystems
