# /spec-intake

## Purpose

Turn a user request or issue URL into `requirements.md`.

## Inputs

- Natural language requirement
- Jira, Linear, or GitHub issue URL
- Existing project docs and code

如果 `source` 是 GitHub issue URL，可以不传 `title`，系统会自动读取 issue 标题和正文。

## Required Context

- `.docs/ARCHITECTURE.md`
- `.docs/SECURITY.md`
- `.docs/CODING_GUIDELINES.md`
- `.docs/docs.md`

## Outputs

- `specs/<initiative-slug>/<YYYY-MM-DD>-v1/requirements.md`

## Rules

- Capture scope and non-goals
- Record acceptance criteria
- Note assumptions and open questions
- Mark security or approval-sensitive items
- 如果 `source` 是 GitHub issue URL，自动提取标题、正文、状态、标签和评论摘要
