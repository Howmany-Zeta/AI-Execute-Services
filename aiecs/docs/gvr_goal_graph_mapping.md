# GVR GoalGraph field mapping (A-3 / D-GVR-04a)

Maps aiecs `AgentGoal` / `GoalGraph` nodes to python-middleware host `WorkState` / `GoalNode`.

## Canonical vs GVR alias fields (D1-A1)

| Host / GVR name | aiecs canonical (JSON export) | Read alias | Notes |
|-----------------|-------------------------------|------------|-------|
| `id` | `goal_id` | `@property id` | Deserialize accepts `id` or `goal_id` |
| `parent_id` | `parent_goal_id` | `@property parent_id` | Deserialize accepts `parent_id` or `parent_goal_id` |
| `description` | `description` | — | |
| `status` | `status` | — | `GoalStatus` enum |
| `success_criteria` | `success_criteria` | — | `str` legacy OR `list[AcceptanceCriterion]` |
| `depends_on` | `depends_on` | — | List of goal IDs |
| `verdict_history` | `verdict_history` | — | Append-only list of `Verdict` dicts |
| `origin` | `origin` | — | `root` \| `decompose` \| `exploration` \| `expand` |
| `priority`, `progress`, `deadline`, timestamps | unchanged | — | rc4 fields retained |

## success_criteria rules

| Layer | Behavior |
|-------|----------|
| `set_goal(description, success_criteria=str)` | Stores string unchanged (rc4) |
| `GoalGraph.add_goal(..., success_criteria=[...])` | Requires structured list; rejects strings |
| Verifier / Gate read | `normalize_acceptance_criteria(goal)` coerces string at read time only |

## GoalGraph API → host WorkState

| GoalGraph method | Host mapping |
|------------------|--------------|
| `add_goal` | Create `GoalNode` in WorkState graph |
| `close_goal` | Mark host node terminal (`ACHIEVED` / etc.) |
| `next_open_goal` | Host DECIDE picks next open node with satisfied `depends_on` |
| `spawn_subgoals(missing)` | EXPAND — one sub-goal per missing criterion |
| `record_verdict` | Append to `GoalNode.verdict_history` (append-only) |
| `to_json` / `from_json` | Session resume / checkpoint handoff |
| `decompose(..., decomposer=)` | Host L1 DECOMPOSE only — engine does not auto-call |

## Configuration

```yaml
goal_graph:
  default_decomposer: none   # only allowed value in 2.1 GA
```

Built-in LLM decomposer is deferred; host MUST pass `decomposer=` to `GoalGraph.decompose`.

## Tool loop integration

- `BaseAIAgent.set_goal(AgentGoal)` and `set_goal_graph(GoalGraph)` register goals for GVR context.
- `HybridAgent._current_goal_for_gvr()` reads `get_current_goal()` — **does not** write goal state into MasterController system prompt.
