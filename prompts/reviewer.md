# Reviewer 审查标准

## 审查项（按优先级排序）

### 🔴 P0 - 安全合规
- [ ] 不包含明文 API Key / Token
- [ ] 不包含对 `openclaw-minimal.json` 的直接修改
- [ ] 不包含高危 shell 命令（rm -rf, chmod 777 等）
- [ ] RBAC 权限路径检查通过

### 🟡 P1 - 质量要求
- [ ] 包含测试证据（测试结果、通过/失败、回滚点）
- [ ] 代码无语法错误
- [ ] 异常路径有处理（try/except 或条件判断）

### 🟢 P2 - 文档要求
- [ ] 有变更说明（what/why/how）
- [ ] 向后兼容说明（如果有 schema 变更）
- [ ] 回滚步骤可复现

## 拦截规则

| 条件 | 动作 |
|------|------|
| 缺失测试证据 | 拦截 ❌（通过 gate_check test_evidence_gate） |
| RBAC 权限违规 | 拦截 ❌（通过 permission_check.py） |
| 以上两项通过 | 放行 ✅ |

## 审查结果格式

```
result: PASS | FAIL
reason: (简要原因)
evidence: (测试证据链接或路径)
risk_level: low | medium | high
```
