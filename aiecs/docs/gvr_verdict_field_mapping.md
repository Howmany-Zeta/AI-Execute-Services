# GVR Verdict field mapping (A-1)

1:1 mapping between **python-middleware** `work_state.Verdict` and **aiecs** `aiecs.domain.agent.verification.models.Verdict`.

Shared fixture: `tests/fixtures/gvr_verdict_v1.json`

| Host `work_state.Verdict` | aiecs `Verdict` | Notes |
|---------------------------|-----------------|-------|
| `passed` | `passed` | bool |
| `kind` | `kind` | `PASS` \| `FAIL` \| `PARTIAL` \| `NA` |
| `score` | `score` | Optional float 0..100 |
| `failed_criteria` | `failed_criteria` | `list[str]` |
| `feedback` | `feedback` | REFINE summary string |
| `feedback_items` | `feedback_items` | list of `{criterion_id, gap, fix, severity}` |
| `missing` | `missing` | EXPAND structural gaps |
| `evidence` | `evidence` | list of `{criterion_id, pass, artifact_ref, quote}`; quote ≤ 120 |

## Sub-types

| Host (dict shape) | aiecs type |
|-------------------|------------|
| feedback item dict | `FeedbackItem` |
| evidence item dict | `EvidenceItem` |
| acceptance criterion | `AcceptanceCriterion` |

## Serialization

```python
from aiecs.domain.agent.verification.models import Verdict

host_payload = {...}  # work_state.Verdict.to_dict()
verdict = Verdict.from_dict(host_payload)
round_trip = verdict.to_dict()
```

Evidence field `pass` serializes as JSON key `"pass"` (Pydantic alias on `EvidenceItem.pass_`).

## Criteria normalization (D1-A)

Host legacy string criteria on `AgentGoal` are **not** auto-upgraded in storage. At verification read boundary:

```python
from aiecs.domain.agent.verification import normalize_acceptance_criteria

criteria = normalize_acceptance_criteria(goal)  # read-only coercion
```
