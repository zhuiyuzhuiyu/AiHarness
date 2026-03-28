# /spec-run-team

## Purpose

根据 team orchestration 计划选择 provider、生成运行计划，并在可行时执行可用 agent。

## Inputs

- `.aiharness/orchestrator.json`
- `orchestration.md`
- `agent-results/*.md`

## Outputs

- `agent-results/run-plan.json`
- `agent-results/<agent>.<provider>.result.md`
- `agent-results/provider-summary.json`
- `agent-results/provider-summary.md`
- `agent-results/reviewer-summary.md`
- `agent-results/tester-summary.md`

## Rules

- 先做 provider 健康检查
- 不可用或未认证的 provider 自动跳过
- 默认只生成运行计划
- 传入 `--execute` 时，执行当前可运行的 provider
- 每次运行后都会更新 provider 汇总，供 `review.md` 和 `test-report.md` 引用
