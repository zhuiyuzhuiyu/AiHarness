# /spec-execute

## Purpose

用一个命令完成执行阶段，包括 team 运行计划、review 和 verify。

## Behavior

- 自动执行 `spec-build`
- 自动根据条件决定是否走 `spec-team` / `spec-run-team`
- 自动执行 `hooks/post-edit/run`
- 自动执行 `spec-review`
- 自动执行 `spec-verify`
