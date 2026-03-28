---
name: company-ai-harness
description: Use when building or running a company engineering harness that turns internal requirements, architecture docs, coding rules, and issue URLs into a repeatable spec-to-code workflow. This skill is for generating `requirements.md`, `design.md`, `tasks.md`, orchestrating multiple models and agents, running review and test loops, updating project docs after delivery, and deciding when to escalate to multi-agent execution or human approval.
---

# Company AI Harness

## Overview

Use this skill to run a disciplined engineering workflow for feature delivery. It standardizes requirement intake, design generation, task decomposition, implementation, review, verification, and documentation updates.

Default to a mixed orchestration model:

1. `Sequential` for the main pipeline.
2. `Parallel` for review, analysis, and test fan-out.
3. `Loop` for review-fix-test cycles.
4. `Human-in-the-loop` for risky or approval-bound changes.
5. `Custom logic` when routing depends on repo state, risk, or subsystem type.

## Output Layout

Store working specs under:

`specs/<initiative-slug>/<YYYY-MM-DD>-<iteration>/`

Required files:

- `requirements.md`
- `design.md`
- `tasks.md`

Recommended files:

- `review.md`
- `test-report.md`
- `handoff.md`

Use a short English initiative slug. Keep every iteration in a dated folder instead of overwriting prior specs.

## Intake Rules

Build `requirements.md` from one or more of the following:

- Direct user description
- Internal issue URL such as Jira, Linear, or GitHub issue
- Existing code and tests
- Local project docs

When project guidance exists, read these in priority order:

1. `.docs/ARCHITECTURE.md`
2. `.docs/SECURITY.md`
3. `.docs/CODING_GUIDELINES.md`
4. `.docs/docs.md`

If the same guidance exists outside `.docs`, use the nearest project-owned version and note the fallback in `requirements.md`.

Capture in `requirements.md`:

- Business goal
- User-visible behavior
- Non-goals
- Constraints and dependencies
- Security or compliance impact
- Acceptance criteria
- Open questions and assumptions

## Design Rules

Generate `design.md` only after requirements are concrete enough to implement. The design should map the requirement to the current repo, not invent a greenfield architecture.

Always include:

- Relevant current-state summary
- Files and modules likely to change
- Data flow and integration points
- Security considerations
- Failure modes
- Test strategy
- Rollback or mitigation notes for risky changes

If the requirement touches multiple bounded contexts, split the design into implementation slices instead of one monolithic plan.

## Task Planning Rules

Generate `tasks.md` as executable slices. Each task should be independently reviewable and testable.

Use this shape:

1. Context
2. Task list
3. Validation plan
4. Risks and blockers

Each task should include:

- Goal
- Target files or subsystems
- Assigned model or agent
- Expected output
- Validation command or test
- Done criteria

## Orchestration Policy

Use this default pipeline:

1. Intake agent creates `requirements.md`.
2. Design agent creates `design.md`.
3. Planning agent creates `tasks.md`.
4. Build agent implements the highest-priority slice.
5. Review agents run in parallel on the diff.
6. Fix agent resolves findings.
7. Verification agents run spec, unit, integration, and e2e checks.
8. Documentation agent updates project docs after behavior or architecture changes.

Suggested model roles:

- Strong reasoning model for requirements, design, and complex edits
- Fast model for task expansion, lint-style review, and broad diff scanning
- Tool-using coding agent for implementation and test execution

Treat model names as configurable. Prefer capabilities over hard-coding a vendor unless the user explicitly requires one.

## Review And Fix Loop

Use a loop when implementation is non-trivial.

Minimum loop:

1. Implement
2. Review
3. Fix
4. Re-run targeted tests

Escalate to a broader loop when any of these are true:

- Cross-cutting refactor
- Security-sensitive code
- Schema or migration changes
- Failing e2e or flaky integration tests
- More than one reviewer model disagrees with the current patch

Stop the loop when one of these is true:

- Acceptance criteria are met
- Remaining issues are explicitly deferred
- The run hits a budget, time, or iteration cap and needs human choice

## Human Approval Gates

Require explicit human approval before merge or auto-apply when work includes:

- Auth, permissions, secrets, or security controls
- Production infra or deployment config
- Database migrations with destructive potential
- Billing, legal, compliance, or privacy-impacting logic
- Changes where requirements are still ambiguous

## Multi-Agent Escalation

Escalate from a single coding agent to an agents team when complexity is high. Trigger escalation if two or more apply:

- More than 3 subsystems change
- Frontend, backend, and infra all move together
- The design contains branching implementation paths
- The task needs separate research, coding, and verification tracks
- The change likely exceeds one clean review-fix cycle

Recommended team shape:

- `architect` agent for decomposition and guardrails
- `builder` agent for implementation
- `reviewer` agent for diff critique
- `tester` agent for validation and reproduction

## E2E Guidance

Prefer deterministic tool-driven verification over free-form browsing.

Recommended order:

1. Project-native spec or unit tests
2. Integration tests
3. Playwright or equivalent browser automation
4. Remote debugging or MCP-backed browser workflows for flows that require live inspection

Use browser-driven e2e when:

- The feature is UI-heavy
- Multiple browser states matter
- Reproduction requires console, network, or DOM inspection

## Documentation Update Rule

After a completed change, update the docs that drifted:

- `README.md` for user-facing setup or usage changes
- `.docs/ARCHITECTURE.md` for structural changes
- `.docs/SECURITY.md` for trust boundaries, auth, or data handling changes
- `.docs/CODING_GUIDELINES.md` for newly established implementation rules
- `.docs/docs.md` for local conventions or feature notes

Do not update every doc blindly. Update only the ones changed by the delivered behavior or technical design.

## References

Read these only when needed:

- For folder conventions and file templates: [references/spec-layout.md](references/spec-layout.md)
- For orchestration choices and mapping to Google patterns: [references/workflow-patterns.md](references/workflow-patterns.md)
- For approval gates, review rules, and test policy: [references/control-gates.md](references/control-gates.md)
