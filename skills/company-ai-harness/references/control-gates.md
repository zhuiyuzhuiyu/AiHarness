# Control Gates

## Review Policy

Every non-trivial code change should pass through:

1. Self-review by the implementation agent
2. Parallel review by at least one additional reviewer
3. Fix loop for accepted findings

Focus review on:

- Behavioral regressions
- Security impact
- Missing tests
- Interface compatibility
- Documentation drift

## Verification Policy

Run the narrowest proof first, then expand:

1. Targeted tests for changed code
2. Related spec or unit tests
3. Integration tests
4. E2E tests

Prefer deterministic commands with saved output. If browser validation is used, record the path taken and the observed result in `test-report.md`.

## Approval Gates

Pause for human input when any of these appear:

- Unclear requirement that changes product behavior
- Data deletion or irreversible migration
- Security model changes
- Secrets handling
- Third-party billing side effects

## Slash Commands

Slash commands are optional, but useful if you want a thin operator UX around this skill.

Suggested commands:

- `/spec-intake`: create `requirements.md`
- `/spec-design`: create `design.md`
- `/spec-plan`: create `tasks.md`
- `/spec-build`: execute the current highest-priority task
- `/spec-review`: run parallel review and append `review.md`
- `/spec-verify`: run validation and write `test-report.md`
- `/spec-close`: update docs and write `handoff.md`

## Hooks

Hooks are optional. Add them only if your runtime supports them cleanly.

Useful hook points:

- Before task execution: sync issue context and local docs
- After file edits: check whether docs drift likely increased
- Before merge or handoff: run secret scan, tests, and approval checks

Avoid hooks that mutate code silently. Hooks should gather context, enforce gates, or block unsafe automation.
