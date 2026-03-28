# Team Orchestrator

团队编排配置位于：

- `.aiharness/orchestrator.json`

## 目标

`spec-team` 用于在复杂需求下自动切换到多 agent 工作模式。

当前版本先做这些事：

- 判断是否应启用 agents team
- 生成 orchestration 计划
- 为每个 agent 生成输入说明和输出路径
- 把结果落到 `specs/<slug>/<date-v1>/agent-results/`

## 默认角色

- `architect`
- `builder`
- `reviewer`
- `tester`

## 自动启用条件

默认会综合以下信号：

- 高风险类别命中数量
- 子系统数量
- 任务数
- 是否需要 review 和 verify 并行

满足阈值后，会自动生成 team 计划。
