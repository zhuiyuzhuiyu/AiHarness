# AiHarness

这个仓库用于用 Git 管理可复用的 AI 工作流技能、模板、命令入口和自动化门禁。

## 目录结构

- `skills/`: 由 Git 管理的 Codex skill
- `templates/`: 可复用的 spec 模板
- `commands/`: 显式触发的工作流入口
- `hooks/`: 自动执行的检查点和门禁
- `docs/`: 长期知识、计划和记录系统

## 当前 Skill

- `company-ai-harness`

## Record System

这个仓库现在采用“短入口 + 结构化 docs”的方式组织知识：

- 仓库入口地图：[AGENTS.md](/Users/zyh/Desktop/AiHarness/AGENTS.md)
- 文档索引：[docs/index.md](/Users/zyh/Desktop/AiHarness/docs/index.md)
- 执行计划：[docs/exec-plans/index.md](/Users/zyh/Desktop/AiHarness/docs/exec-plans/index.md)
- 设计原则：[docs/design-docs/index.md](/Users/zyh/Desktop/AiHarness/docs/design-docs/index.md)

## 工作流接口

- `commands/` 定义每个阶段的显式入口
- `hooks/` 定义围绕这些阶段自动执行的检查

## CLI

统一通过 `bin/aih` 或 `commands/`、`hooks/` 下的包装脚本调用。

示例：

```bash
./commands/spec-start --title "Add refund approval flow" --source "JIRA-123"
./commands/spec-execute --slug refund-approval
./commands/spec-finish --slug refund-approval
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
./commands/spec-start --source "https://github.com/owner/repo/issues/123"
```

如果 URL 可读取，就会自动提取标题、正文、状态、标签和评论摘要，并写入 `requirements.md`。

## Agents Team

复杂需求可以通过 `spec-team` 进入多 agent 编排模式：

```bash
./commands/spec-execute --slug refund-approval --team
```

当前版本会根据 spec、风险和任务数生成 team 计划，并把每个 agent 的执行说明写入 `agent-results/`。

如果要继续到 provider 选择和执行阶段，可以运行：

```bash
./commands/spec-execute --slug refund-approval --team
./commands/spec-execute --slug refund-approval --team --execute-team
```

当前版本会先做 provider 健康检查，不可用或未认证的 provider 会自动跳过。

执行 `spec-run-team` 后还会自动生成：

- `agent-results/provider-summary.json`
- `agent-results/provider-summary.md`
- `agent-results/reviewer-summary.md`
- `agent-results/tester-summary.md`

其中 `review.md` 和 `test-report.md` 会自动引用 reviewer/tester 的 provider 汇总。

## 执行计划与索引

- `spec-team` 会自动在 `docs/exec-plans/active/` 下生成执行计划
- `spec-finish` 会自动把对应计划归档到 `docs/exec-plans/completed/`
- `spec-start`、`spec-execute`、`spec-run-team`、`spec-finish` 会自动更新：
  - `docs/exec-plans/execution-index.json`
  - `docs/exec-plans/execution-index.md`
  - `docs/exec-plans/execution-by-status.md`
  - `docs/exec-plans/execution-by-slug.md`

如果需要单独归档，也可以运行：

```bash
./commands/spec-archive-plan --slug feature-slug
```

## Codex 接入

将 Codex 指向这个仓库中的 skill：

```bash
ln -s /Users/zyh/Desktop/AiHarness/skills/company-ai-harness /Users/zyh/.codex/skills/company-ai-harness
```
