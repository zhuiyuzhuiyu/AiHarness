# Workflow Patterns

This skill maps directly to Google Cloud's agent design pattern guidance.

## Recommended Composite Pattern

Use a composite workflow instead of one pattern everywhere.

### 1. Sequential Backbone

Best for:

- Requirement intake
- Design generation
- Task decomposition
- Build
- Verify
- Doc updates

This is the default control plane because the main engineering flow is ordered and repeatable.

### 2. Parallel Review Fan-Out

Best for:

- Diff review by multiple models
- Running lint, typecheck, and unit tests together
- Comparing alternative implementation ideas

Use parallel fan-out when tasks are independent and speed matters.

### 3. Loop For Refinement

Best for:

- Review -> fix -> targeted retest
- E2E stabilization
- Prompt or test tuning

Keep a hard stop:

- Max iterations
- Budget cap
- Human escalation condition

### 4. Human-In-The-Loop

Use for:

- Security-sensitive work
- Requirement ambiguity
- Architecture-breaking changes
- Approvals that belong to humans

### 5. Custom Logic

Use when routing depends on change type.

Examples:

- Backend-only changes skip browser e2e
- Security-sensitive changes add mandatory approval
- Small doc-only changes collapse directly to a light path

## Model Routing Guidance

Use stronger reasoning for:

- Requirement clarification
- Architecture tradeoffs
- Complex refactors

Use faster models for:

- Broad review passes
- Reformatting or checklist verification
- Large but shallow search tasks

Use tool-capable coding agents for:

- Repo inspection
- File edits
- Running tests
- Capturing artifacts
