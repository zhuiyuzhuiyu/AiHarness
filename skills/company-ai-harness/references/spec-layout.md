# Spec Layout

Use this structure for each initiative:

```text
specs/
  <initiative-slug>/
    <YYYY-MM-DD>-<iteration>/
      requirements.md
      design.md
      tasks.md
      review.md
      test-report.md
      handoff.md
```

## File Intent

`requirements.md`

- Source summary
- Problem statement
- Scope
- Constraints
- Acceptance criteria
- Open questions

`design.md`

- Current-state summary
- Proposed approach
- File and module impact
- Data and control flow
- Security and failure analysis
- Test plan

`tasks.md`

- Ordered task slices
- Owner model or agent
- Validation command
- Exit criteria

`review.md`

- Reviewer
- Findings by severity
- Disposition

`test-report.md`

- Commands run
- Pass or fail summary
- Failures and repro notes
- Risk acceptance if partial

`handoff.md`

- Summary of delivered behavior
- Docs updated
- Follow-up work

## Iteration Naming

Use:

- `2026-03-28-v1`
- `2026-03-28-v2`
- `2026-03-29-v1`

If the same feature is reopened later, create a new dated folder. Do not mutate old history into the newest state.
