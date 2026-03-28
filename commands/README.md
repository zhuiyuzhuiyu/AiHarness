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

所有命令包装脚本最终都会调用 `bin/aih`，再由 `scripts/harness.py` 执行。

推荐命令集合：

- `spec-intake.md`
- `spec-design.md`
- `spec-plan.md`
- `spec-build.md`
- `spec-review.md`
- `spec-verify.md`
- `spec-close.md`

每个命令应说明：

- Purpose
- Expected input
- Required context
- Output files
- Escalation rules

这些命令是显式入口，不会自动执行。

## 示例

```bash
./commands/spec-intake --title "Add refund approval flow" --source "JIRA-123"
./commands/spec-design --slug refund-approval
./commands/spec-plan --slug refund-approval
./commands/discover-commands --apply
./commands/spec-team --slug refund-approval
```
