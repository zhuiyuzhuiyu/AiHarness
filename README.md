# AiHarness

这个仓库用于用 Git 管理可复用的 AI 工作流技能、模板、命令入口和自动化门禁。

## 目录结构

- `skills/`: 由 Git 管理的 Codex skill
- `templates/`: 可复用的 spec 模板
- `commands/`: 显式触发的工作流入口
- `hooks/`: 自动执行的检查点和门禁
- `docs/`: 工作流与配置说明

## 当前 Skill

- `company-ai-harness`

## 工作流接口

- `commands/` 定义每个阶段的显式入口
- `hooks/` 定义围绕这些阶段自动执行的检查

## CLI

统一通过 `bin/aih` 或 `commands/`、`hooks/` 下的包装脚本调用。

示例：

```bash
./commands/spec-intake --title "Add refund approval flow" --source "JIRA-123"
./commands/spec-design --slug refund-approval
./commands/spec-plan --slug refund-approval
./commands/spec-build --slug refund-approval
./commands/discover-commands --apply
./hooks/post-edit/run
```

## 配置

- 配置文件：`.aiharness/config.json`
- 默认语言：中文
- `spec-review` 和 `spec-verify` 会读取配置中的真实命令

示例：

- 在 `review.commands` 中启用 `npm run lint`
- 在 `verify.commands` 中启用 `pytest` 或 `npx playwright test`
- 也可以先运行 `./commands/discover-commands --apply` 自动发现并写入

## Issue URL 输入

`spec-intake` 支持直接读取 GitHub issue URL：

```bash
./commands/spec-intake --source "https://github.com/owner/repo/issues/123"
```

如果 URL 可读取，就会自动提取标题、正文、状态、标签和评论摘要，并写入 `requirements.md`。

## Codex 接入

将 Codex 指向这个仓库中的 skill：

```bash
ln -s /Users/zyh/Desktop/AiHarness/skills/company-ai-harness /Users/zyh/.codex/skills/company-ai-harness
```
