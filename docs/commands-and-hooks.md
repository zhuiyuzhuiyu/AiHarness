# Commands 与 Hooks

## 目的

这份文档解释显式工作流入口与自动门禁之间的区别。

## Commands

Commands 是用户主动触发的动作，用来启动工作流中的某个阶段。

Recommended lifecycle:

1. `/spec-intake`
2. `/spec-design`
3. `/spec-plan`
4. `/spec-build`
5. `/spec-review`
6. `/spec-verify`
7. `/spec-close`

在这个仓库里，这些命令通过 `commands/` 下的可执行包装脚本实现，并统一转发给 `bin/aih`。

## Hooks

Hooks 会在生命周期检查点自动运行。

Recommended checkpoints:

1. `pre-task`
2. `post-edit`
3. `pre-review`
4. `pre-verify`
5. `pre-close`

在这个仓库里，每个 hook 检查点目录下都有一个 `run` 包装脚本。调度器、slash command 运行器或外部 orchestrator 可以直接调用它们。

## 设计原则

用 commands 启动工作。

用 hooks 保障流程质量与安全。

不要把 hooks 用于隐藏式代码修改。
