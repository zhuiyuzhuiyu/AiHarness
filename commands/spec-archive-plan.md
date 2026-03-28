# /spec-archive-plan

## Purpose

把 `docs/exec-plans/active/` 下的执行计划归档到 `completed/`。

## Inputs

- `--slug`
- `--date`
- `--iteration`

## Behavior

- 查找对应的 active 执行计划
- 移动到 `docs/exec-plans/completed/`
- 更新 execution index
