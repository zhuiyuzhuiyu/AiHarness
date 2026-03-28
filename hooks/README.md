# Hooks

这个目录用于存放 AI Harness 的自动门禁和事件驱动检查。

Hooks 不是手动命令，而是在特定生命周期节点执行的检查。

每个 hook 目录下都有一个可执行的 `run` 包装脚本，最终会调用 `bin/aih`。

推荐的 hook 检查点：

- `pre-task/`
- `post-edit/`
- `pre-review/`
- `pre-verify/`
- `pre-close/`

Hooks 应该承担：

- gather context
- enforce safety and quality gates
- block unsafe automation when necessary

Hooks 不应静默改写代码。

## 示例

```bash
./hooks/pre-task/run
./hooks/post-edit/run
./hooks/pre-close/run --slug refund-approval
```
