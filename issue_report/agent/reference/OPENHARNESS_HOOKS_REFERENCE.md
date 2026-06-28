# OpenHarness Hook 对标引用（vendored 摘录）

**用途**：Hook 计划 §5.1.2 / §5.1.3 / §5.4.1 / §13 / H0-07（HOOKS.md 须链到此文件）。

**计划路径**：[`../AIEcs_HOOK_IMPLEMENTATION_PLAN.md`](../AIEcs_HOOK_IMPLEMENTATION_PLAN.md)

---

## 0. 源码位置与版本

| 项 | 值 |
|----|-----|
| **Vendored 根目录** | `issue_report/new_function_request/OpenHarness/` |
| **Git HEAD（记录时）** | `9b2efd795c6aa09f88b0c257d269a9e518da6ae7` |
| **Hook 模块** | `src/openharness/hooks/{events,loader,executor,schemas,types}.py` |
| **Agent loop** | `src/openharness/engine/query.py` |
| **集成测试** | `tests/test_engine/test_query_engine.py`（`test_pre_tool_hook_blocks` 等） |
| **Manifest** | [openharness_refs.manifest](./openharness_refs.manifest) |
| **Verify script** | [verify_openharness_refs.sh](./verify_openharness_refs.sh)（**H0-07** / §13） |

更新摘录时：在 OpenHarness 目录执行 `git rev-parse HEAD`，更新 manifest + §0 HEAD，并刷新下文行号/片段；运行 verify 脚本通过后再合入。

**`.gitignore` 注意**：`issue_report/` 对 IDE/rg 可能不可见；vendored 树在磁盘上完整时 verify 仍应通过。

---

## 1. Priority 降序 + stable sort（AIEcs §5.1.2）

**文件**：`src/openharness/hooks/loader.py`

```python
def get(self, event: HookEvent) -> list[HookDefinition]:
    """Return hooks registered for an event, ordered by priority.

    Hooks with a higher ``priority`` run first. ``sorted`` is stable, so
    hooks sharing the same priority keep their registration order.
    """
    hooks = self._hooks.get(event, [])
    return sorted(hooks, key=lambda hook: -getattr(hook, "priority", 0))
```

**Schema**（`src/openharness/hooks/schemas.py` · `CommandHookDefinition`）：

```python
priority: int = Field(default=0)
"""Higher priority runs first within an event; ties keep registration order."""
```

**AIEcs 定稿**：与上式一致 — 数值 **越大越先**；tie → 注册顺序（stable sort）。

---

## 2. 同 event 串行执行（AIEcs §5.1.3）

**文件**：`src/openharness/hooks/executor.py` · `HookExecutor.execute`

```python
async def execute(self, event: HookEvent, payload: dict[str, Any]) -> AggregatedHookResult:
    """Execute all matching hooks for an event."""
    results: list[HookResult] = []
    for hook in self._registry.get(event):
        if not _matches_hook(hook, payload):
            continue
        if isinstance(hook, CommandHookDefinition):
            results.append(await self._run_command_hook(hook, event, payload))
        elif isinstance(hook, HttpHookDefinition):
            results.append(await self._run_http_hook(hook, event, payload))
        elif isinstance(hook, PromptHookDefinition):
            results.append(await self._run_prompt_like_hook(hook, event, payload, agent_mode=False))
        elif isinstance(hook, AgentHookDefinition):
            results.append(await self._run_prompt_like_hook(hook, event, payload, agent_mode=True))
    return AggregatedHookResult(results=results)
```

**要点**：`for` + `await` — **非** `asyncio.gather`；顺序由 §1 `get()` 决定。

---

## 3. `$ARGUMENTS` 模板替换（AIEcs §5.4.1 对标）

**文件**：`src/openharness/hooks/executor.py`

```python
def _inject_arguments(
    template: str, payload: dict[str, Any], *, shell_escape: bool = False
) -> str:
    serialized = json.dumps(payload, ensure_ascii=True)
    if shell_escape:
        serialized = shlex.quote(serialized)
    return template.replace("$ARGUMENTS", serialized)
```

| Hook type | Harness | AIEcs v1 |
|-----------|---------|----------|
| prompt/agent | `$ARGUMENTS` → JSON embed | **同 Harness**（§5.4.1） |
| command | `$ARGUMENTS` + `shlex.quote` + shell subprocess | **禁止** shell；payload **stdin JSON**（§12.3） |

---

## 4. matcher（AIEcs §5.5）

**文件**：`src/openharness/hooks/executor.py`

```python
def _matches_hook(hook: HookDefinition, payload: dict[str, Any]) -> bool:
    matcher = getattr(hook, "matcher", None)
    if not matcher:
        return True
    subject = str(payload.get("tool_name") or payload.get("prompt") or payload.get("event") or "")
    return fnmatch.fnmatch(subject, matcher)
```

---

## 5. PRE_TOOL block（AIEcs H1）

**文件**：`src/openharness/engine/query.py` · `_execute_tool_call`

```python
pre_hooks = await context.hook_executor.execute(
    HookEvent.PRE_TOOL_USE,
    {"tool_name": tool_name, "tool_input": tool_input, "event": HookEvent.PRE_TOOL_USE.value},
)
if pre_hooks.blocked:
    return ToolResultBlock(
        tool_use_id=tool_use_id,
        content=pre_hooks.reason or f"pre_tool_use hook blocked {tool_name}",
        is_error=True,
    )
```

| 项 | Harness | AIEcs v1 |
|----|---------|----------|
| block 后 POST_TOOL | **不** fire（early return） | **仍** fire H2 审计（§7.1.4 H2-block） |
| assistant 在 messages | 通常 **已** append（L802 后） | batch：整批 assistant append 后 per-tool H1（§7.6.1） |

---

## 6. POST_TOOL（AIEcs H2 成功路径）

**文件**：`src/openharness/engine/query.py` · `_execute_tool_call` 末尾

```python
if context.hook_executor is not None:
    await context.hook_executor.execute(
        HookEvent.POST_TOOL_USE,
        {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_result.content,
            "tool_is_error": tool_result.is_error,
            "event": HookEvent.POST_TOOL_USE.value,
        },
    )
```

AIEcs H2 另含 block/except/D13 非 execute 路径（§7.1.4 / §7.6.2）；Harness 无 POST on PRE block。

---

## 7. STOP（AIEcs H6 语义子集）

**文件**：`src/openharness/engine/query.py` · query loop（无 tool_uses 分支）

```python
if not final_message.tool_uses:
    if context.hook_executor is not None:
        await context.hook_executor.execute(
            HookEvent.STOP,
            {
                "event": HookEvent.STOP.value,
                "stop_reason": "tool_uses_empty",
            },
        )
    return
```

**AIEcs 差异**：H6 在 DAWP drain + H15 **之后**（§7.1.3）；`_dawp_drained_any` 时 **跳过** H6（§7.1.4 / H6-02）。Non-streaming **H2-01a** 内核 parity（§7.1.3.1 / DAWP-NS-01）**先于** H6 hook wiring。

---

## 8. 本 workspace 核对命令

**自动化（推荐 — H0-07 / CI）**：

```bash
# 从 python-middleware-dev 仓库根
bash issue_report/agent/reference/verify_openharness_refs.sh
```

校验项：OpenHarness checkout 存在；`git rev-parse HEAD` == `openharness_refs.manifest` 中 `HEAD=`；manifest 列出的 **全部 PATH** 存在；**ANCHOR** 字符串仍在源文件中（upstream 漂移时 fail，提示更新摘录行号）。

**手动抽查**（从 **python-middleware-dev 仓库根**）：

```bash
OH=issue_report/new_function_request/OpenHarness

git -C "$OH" rev-parse HEAD

# §5.1.2 priority
sed -n '20,29p' "$OH/src/openharness/hooks/loader.py"

# §5.1.3 serial execute
sed -n '64,78p' "$OH/src/openharness/hooks/executor.py"

# §5.4.1 $ARGUMENTS
sed -n '223,229p' "$OH/src/openharness/hooks/executor.py"

# H1 block
sed -n '893,903p' "$OH/src/openharness/engine/query.py"

# H6 STOP
sed -n '808,816p' "$OH/src/openharness/engine/query.py"

# POST_TOOL
sed -n '1007,1017p' "$OH/src/openharness/engine/query.py"
```

若 `OpenHarness/` 不存在：clone 或 submodule 到上述路径后再核对。

---

## 9. AIEcs 计划交叉引用

| Harness 行为 | 计划章节 | 验收 |
|--------------|----------|------|
| Priority 降序 | §5.1.2 | H0-02 loader |
| 串行 execute | §5.1.3 | Loader 单测 |
| `$ARGUMENTS` prompt | §5.4.1 | Prompt 单测 |
| PRE_TOOL block | §7.6 / H1 | H1 block |
| PRE block → no POST | §7.1.4 | H2-block-01（AIEcs **扩展**） |
| STOP | §7.1.3–§7.1.4 | H6-01 / H6-02；**DAWP-NS-01**（H2-01a 前置） |
