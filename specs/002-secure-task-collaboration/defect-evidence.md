# Carried MVP Defect Evidence

Observed 2026-10-07 against current source and the existing local API. Inspection used
read-only GETs, local schema/OpenAPI evaluation, pre-persistence invalid PATCH evaluation,
and strict mypy. No migrations, fixture setup, SQL writes, or valid mutation requests ran.
This is baseline evidence, not evidence that fixes or regression gates already pass.

## DEF-01 — Pagination overflow: confirmed HTTP failure

Reproduction: GET `/api/v1/task-lists?offset=1000000000000000000000000000000`;
GET `/api/v1/task-lists/{existing_list_id}/tasks` with the same query. Both returned 500:

```json
{"code":"internal_error","message":"An unexpected error occurred.","details":[]}
```

Baseline list GET returned 200 and total=2. Retrieve an existing ID from that baseline to
repeat the task GET; no new resource is needed. The database exception was not inspected,
so this evidence confirms the symptom rather than independently proving the exact DB error.
Both persistence stores pass arbitrary Python integer offsets directly to SQLAlchemy:
`task_list_store.py:62`, `task_query_store.py:58`; HTTP parsing is `http/validation.py:28`.

Controls: offset=-1 returns 422/query.offset/“Must be non-negative.”; offset=1.2 returns
422/query.offset/“Must be an integer.” Repeated offset and unknown keys remain rejected.

Expected / regression: Given existing list/task collections, when offsets include 2^63,
10^30 and larger accepted decimal values, then 200 contains empty items and correct totals;
task summaries match an unfiltered baseline. No artificial maximum may replace the contract.
Repeat negative/noninteger, unknown/repeated controls, empty lists and beyond-end offsets.

## DEF-02 — Unsupported text: validation confirmed; persisted 500 not replayed

The four request schemas below accept `a\u0000b` in name/title and description, and both
shared domain text normalizers preserve it. Source: `domain/validation.py:6,17` and request
schemas. This confirms missing validation. The reported persistence 500 was not replayed
because the user prohibits database alterations during specification.

Expected / regression: Given each create/PATCH text field, when it contains embedded NUL
(or another string unrepresentable in the configured PostgreSQL text encoding), then 422
identifies the exact field and explains safely; no create occurs and PATCH preserves all
prior data. Recheck valid Unicode, trimming, blank/null descriptions, length boundaries and
atomic multi-field updates. Full persisted-state verification runs later in an isolated DB.

## DEF-03 — OpenAPI gaps: confirmed

Current `create_app().openapi()` yields no query parameters for list collection GET and only
`list_id` path for task collection GET; limit/offset/status/priority are missing. Query parsing
is inside route bodies (`routes/task_list_collection.py:34`, `routes/task_queries.py:26`).
Existing response statuses include list 200/422/500 and tasks 200/422/500/404: the finding
concerns parameter/schema parity, not a claim that every response declaration is absent.

Expected / regression: Given generated OpenAPI, when inspected, then both collections expose
limit default20/min1/max100 and offset default0/min0/no maximum; tasks also expose optional
status and priority enums. Check parameter location, defaults, bounds, enum values, request
and response schemas, expected error envelopes and future security requirements against
runtime. Preserve unknown/repeated query rejection with behavioral checks.

## DEF-04 — Validation locations: confirmed without DB access

TestClient PATCH requests supplying name/title/status/priority=null fail before persistence
with 422 but report `details=[{"field":"body","message":"Invalid value."}]`.
Model-level validators in `schemas/task_list.py:61` and `schemas/task_requests.py:49` produce
the body location; `http/api.py:24` replaces the reason with the generic text.

Expected / regression: Given null or invalid individual fields, when validation fails,
then details identify body.name/body.title/body.status/body.priority and a useful safe reason.
Empty PATCH may identify body. Future password/token errors must never echo values; preserve
code/message/details envelope and safe body/path/query locations.

### Repeatable no-database schema/OpenAPI/location probe

Run through `uv run --frozen python` from the repository; it does not call valid write paths:

```python
from fastapi.testclient import TestClient
from task_manager.infrastructure.http.api import create_app
from task_manager.infrastructure.http.schemas.task_list import (
    CreateTaskListRequest, UpdateTaskListRequest,
)
from task_manager.infrastructure.http.schemas.task_requests import (
    CreateTaskRequest, UpdateTaskRequest,
)
from task_manager.domain.validation import (
    normalize_required_text, normalize_description,
)

app = create_app()
for path in ("/api/v1/task-lists", "/api/v1/task-lists/{list_id}/tasks"):
    print(path, app.openapi()["paths"][path]["get"].get("parameters", []))
for model, payload in (
    (CreateTaskListRequest, {"name": "a\0b", "description": "a\0b"}),
    (UpdateTaskListRequest, {"name": "a\0b", "description": "a\0b"}),
    (CreateTaskRequest, {"title": "a\0b", "description": "a\0b"}),
    (UpdateTaskRequest, {"title": "a\0b", "description": "a\0b"}),
):
    print(model.__name__, repr(model.model_validate(payload).model_dump()))
print(repr(normalize_required_text("a\0b", "name", 100)))
print(repr(normalize_description("a\0b", "description", 1000)))
client = TestClient(app)
list_path = "/api/v1/task-lists/00000000-0000-0000-0000-000000000001"
task_path = list_path + "/tasks/00000000-0000-0000-0000-000000000002"
for path, field in (
    (list_path, "name"), (task_path, "title"),
    (task_path, "status"), (task_path, "priority"),
):
    response = client.patch(path, json={field: None})
    print(field, response.status_code, response.json())
```

## DEF-05 — Strict typing: confirmed

Command: `uv run --frozen mypy --strict src tests migrations`; exit1, 72 files checked:

```text
tests/e2e/test_api_errors.py:90: error: Need type annotation for "invalid_updates" [var-annotated]
tests/e2e/test_api_errors.py:98: error: Incompatible types in assignment (expression has type "dict[str, None] | dict[str, Any] | dict[str, str] | dict[Any, Any]", variable has type "dict[str, str] | dict[str, object]") [assignment]
Found 2 errors in 1 file (checked 72 source files)
```

The second failure reuses request_body from a preceding loop. Bare mypy defaults to only
`task_manager` via pyproject and therefore does not establish that tests pass.

Expected / regression: The full command passes without broad Any, suppressions, or exclusions.
Manual annotation review also enforces constitution IV: strict mypy does not itself enforce
all explicit locals. Examples requiring review: normalized_value in domain/validation.py:7,20;
normalized values and timestamp in domain/task_list.py:25–27; locals in application/task_lists/
operations.py:18,37–49; session/config locals in infrastructure/persistence/database.py:28,49–53.
No accepted inference exception was found in the current constitution, plan, AGENTS or decision
log. This specification retains the written explicit-annotation rule unless the user explicitly
resolves a competing agreement and authorizes the required amendment.

## Migration facts affecting the pending review

Compose migrate runs `uv run --frozen --no-dev alembic upgrade head`; API startup waits for
successful completion. Current revisions 0001–0003 contain no users/bootstrap mechanism.
An HTTP registration call cannot supply an owner before migration completes. The plan must
therefore define secure offline bootstrap or equivalent staged provisioning. Existing revisions
and historical rows must remain intact. No DB-backed tests were run: fixtures create/drop schemas
and the existing error-path E2E test drops a table, violating this invocation's read-only boundary.
