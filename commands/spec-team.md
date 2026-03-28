# /spec-team

## Purpose

生成多 agent 编排计划，并为每个 agent 生成输入说明与输出路径。

## Inputs

- `requirements.md`
- `design.md`
- `tasks.md`
- 当前仓库 diff 与风险信号

## Outputs

- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/orchestration.md`
- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/agent-results/*.md`

## Rules

- 根据 `.aiharness/orchestrator.json` 计算是否自动启用 agents team
- 达到阈值时返回成功状态并生成 team plan
- 未达到阈值时仍生成计划，但返回非 0 作为“暂不建议启用”的信号
- 当前版本只生成 orchestration 计划，不直接调用真实 provider
