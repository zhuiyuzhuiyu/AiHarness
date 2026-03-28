# RELIABILITY

## 目标

让 harness 在重复执行时稳定、可恢复、可追踪。

## 当前策略

- 所有主要步骤都落到 `specs/` 或 `docs/`
- 复杂任务使用 team orchestration
- review 和 verify 都有显式产物
- 聚合命令优先复用底层命令，避免分叉逻辑

## 后续提升

- provider 执行结果汇总
- 失败重试策略
- 更清晰的退出码约定
