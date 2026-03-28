# SECURITY

## 默认原则

- 高风险改动必须显式标记
- 鉴权、计费、迁移、基础设施相关变更需要额外 review
- 不在 skill 或脚本里硬编码敏感凭据

## 当前执行点

- `spec-review` 会基于风险规则生成 findings
- `hooks/post-edit/run` 会提示高风险改动
- provider 执行前先做健康检查

## 后续补强

- secret scanning
- 更细粒度的审批门
- 对高风险路径的强制测试要求
