# Commands

这个目录用于存放 AI Harness 的显式工作流入口。

你可以通过这些命令直接启动某个阶段，而不需要每次重复整段提示词。

可执行入口与 markdown 说明文件并存：

- `commands/spec-intake`
- `commands/spec-design`
- `commands/spec-plan`
- `commands/spec-build`
- `commands/spec-review`
- `commands/spec-verify`
- `commands/spec-close`
- `commands/discover-commands`
- `commands/spec-team`
- `commands/spec-run-team`
- `commands/spec-start`
- `commands/spec-execute`
- `commands/spec-finish`

所有命令包装脚本最终都会调用 `bin/aih`，再由 `scripts/harness.py` 执行。

推荐命令集合：

- `spec-start`
- `spec-execute`
- `spec-finish`

底层调试命令：

- `spec-intake`
- `spec-design`
- `spec-plan`
- `spec-build`
- `spec-review`
- `spec-verify`
- `spec-close`
- `spec-team`
- `spec-run-team`

每个命令应说明：

- Purpose
- Expected input
- Required context
- Output files
- Escalation rules

这些命令是显式入口，不会自动执行。

## 示例

```bash
./commands/spec-start --title "Add refund approval flow" --source "JIRA-123"
./commands/spec-execute --slug refund-approval
./commands/spec-finish --slug refund-approval
```
