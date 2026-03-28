# /spec-review

## Purpose

Run structured review on the current diff and write `review.md`.

默认使用中文输出审查结果。

## Inputs

- Current diff
- `requirements.md`
- `design.md`
- `tasks.md`

## Outputs

- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/review.md`

## Rules

- Focus on regressions, security, and test gaps
- Prefer parallel review passes
- Record severity and disposition for each finding
- Execute real commands from `.aiharness/config.json` when enabled
- Synthesize structured findings from spec completeness, command failures, risk hits, and doc drift hints
