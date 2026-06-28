# Agent Hook 计划 — 引用文档

本目录存放 [AIEcs Hook 实现计划](../AIEcs_HOOK_IMPLEMENTATION_PLAN.md) 的外部对标摘录，供 OpenSpec / HOOKS.md 引用。

| 文件 | 用途 |
|------|------|
| [OPENHARNESS_HOOKS_REFERENCE.md](./OPENHARNESS_HOOKS_REFERENCE.md) | OpenHarness vendored 源码摘录 + 核对命令（§5.1.2、§5.1.3、§13） |
| [openharness_refs.manifest](./openharness_refs.manifest) | 记录 HEAD + 必存在路径 + anchor 字符串（**H0-07**） |
| [verify_openharness_refs.sh](./verify_openharness_refs.sh) | CI/doc 校验：paths exist @ recorded HEAD |

**OpenHarness 源码树（同 repo，需本地 checkout）**：

`issue_report/new_function_request/OpenHarness/`

**说明**：父目录 `issue_report/` 默认在 `.gitignore` 中 — workspace **rg/IDE 索引** 可能搜不到 vendored 树；`reference/` 子目录已通过 negation **纳入 git**。校验脚本从 repo 根运行：

```bash
bash issue_report/agent/reference/verify_openharness_refs.sh
```
