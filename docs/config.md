# 配置说明

AI Harness 的运行配置位于：

- `.aiharness/config.json`

## 语言约束

默认语言配置：

- `language.default = zh-CN`
- `language.instruction` 用于约束 skill 描述、命令说明、测试报告、review 结论和对用户的回答默认使用中文

除非用户明确要求其他语言，否则统一使用中文。

## Review 命令

在 `review.commands` 中配置真实 review 命令，例如：

- `npm run lint`
- `npm run typecheck`
- `pytest -q`

字段说明：

- `name`: 命令标识
- `enabled`: 是否启用
- `command`: 实际执行的 shell 命令
- `description`: 中文说明

## Verify 命令

在 `verify.commands` 中配置真实验证命令，例如：

- `npm test -- --runInBand`
- `pytest`
- `npx playwright test`

`./commands/spec-review` 会执行所有已启用的 `review.commands`。  
`./commands/spec-verify` 会执行所有已启用的 `verify.commands`。

如果任一命令返回非零退出码，对应步骤会返回失败状态。

## 自动发现命令

可以运行：

```bash
./commands/discover-commands
./commands/discover-commands --apply
```

自动扫描当前仓库中的：

- `package.json` 脚本
- `pytest.ini` / `pyproject.toml` 等 pytest 配置
- `playwright.config.*`

`--apply` 会把发现到的命令直接写回 `.aiharness/config.json`。

## Issue URL 读取

当前优先支持 GitHub issue URL，依赖本机 `gh` 已登录。

例如：

```bash
./commands/spec-intake --source "https://github.com/owner/repo/issues/123"
```

如果 URL 可读取，系统会自动把这些信息写入 `requirements.md`：

- 标题
- 正文
- 状态
- 标签
- 负责人
- 评论摘要
