# /spec-verify

## Purpose

Run validation and record results in `test-report.md`.

默认使用中文输出测试结果。

## Inputs

- Current code changes
- Project test commands

## Outputs

- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/test-report.md`

## Rules

- Run targeted tests before broad suites
- Include reproduction notes for failures
- Use browser-driven checks only when needed
- Execute real commands from `.aiharness/config.json` when enabled
