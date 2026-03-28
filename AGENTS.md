# AGENTS

这是仓库的入口地图，不是百科全书。

默认原则：

- 除非用户明确要求其他语言，所有说明、计划、review 和测试结论默认使用中文。
- 优先阅读结构化文档，不要依赖单个超长说明文件。
- 把代码仓库视为记录系统：需求、设计、计划、执行结果和技术债都应落盘并版本化。

## 先读哪里

1. [README.md](README.md)
2. [docs/index.md](docs/index.md)
3. [docs/PLANS.md](docs/PLANS.md)
4. [docs/QUALITY_SCORE.md](docs/QUALITY_SCORE.md)
5. [docs/SECURITY.md](docs/SECURITY.md)

## 工作流入口

- 日常使用三步法：
  - `./commands/spec-start`
  - `./commands/spec-execute`
  - `./commands/spec-finish`
- 底层调试入口在 [commands/README.md](commands/README.md)

## 记录系统

- 需求与交付产物：`specs/<slug>/<date-v1>/`
- 长期计划与台账：`docs/exec-plans/`
- 设计与原则：`docs/design-docs/`
- 产品与工作流规范：`docs/product-specs/`
- 外部参考与 LLM 友好资料：`docs/references/`

## 更新规则

- 新能力落地后，补对应 `docs/` 文档，而不是只改命令或脚本。
- 复杂需求优先生成执行计划，并归档到 `docs/exec-plans/active/` 或 `completed/`。
- 如果发现文档过时，应在交付时一并修正。
