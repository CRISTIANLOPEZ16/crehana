# Carried Defect Evidence

Baseline checked before feature implementation on 2026-10-08 using the repository
`.venv` tools. Initially no `TEST_DATABASE_URL` was exported and Docker/socket access was
restricted; after starting the isolated test service, the pre-change tracked source was
extracted to `/tmp/crehana-baseline` and run against one disposable PostgreSQL schema. The
schema was removed after the run.

| Defect | Baseline evidence | Expected regression |
| --- | --- | --- |
| DEF-01 pagination overflow | Pre-change API against disposable PostgreSQL: `GET /api/v1/task-lists?offset=1000000000000000000000000000000` returned 500. Both stores unconditionally sent the offset to PostgreSQL. | Huge nonnegative offsets return 200 with empty items and accurate counts/summary. |
| DEF-02 unsupported NUL text | Pre-change API against disposable PostgreSQL: NUL list-name and task-title creates both returned 500. The normalizers did not reject NUL. | NUL in every persisted text field returns field-level 422 without changing data. |
| DEF-03 OpenAPI gaps | Pre-change generated list/task collection operations contained no query parameter declarations because routes read values only through `Request`. | OpenAPI parameters and schemas match runtime validation. |
| DEF-04 validation locations | Pre-change error mapping returned domain field `name` rather than `body.name`; Pydantic validation locations included the request source but did not provide useful safe reasons. | Safe, useful errors identify `body.<field>`; empty PATCH remains body-level. |
| DEF-05 strict typing | `.venv/bin/mypy --strict src tests migrations` exited 1: `tests/e2e/test_api_errors.py:90` needed annotation for `invalid_updates`; line 98 had incompatible reassignment. | The same command passes without broad suppressions. |

Baseline commands and outcomes:

```text
pre-change source in disposable schema -> huge_offset=500 nul_list=500 nul_task=500
.venv/bin/pytest -q -> 1 failed, 27 passed, 23 skipped; coverage 62.86%
  failing check: test_health_through_running_uvicorn_process (loopback bind permission denied)
.venv/bin/mypy --strict src tests migrations -> 2 errors in tests/e2e/test_api_errors.py
UV_CACHE_DIR=/tmp/crehana-uv-cache uv run --frozen pytest -q -> uv platform panic
```

The failed loopback test is an environment restriction, not an application assertion.
Post-fix focused regressions were run against the isolated test DB:

```text
TEST_DATABASE_URL=<ignored .env test URL> .venv/bin/pytest -q \
  tests/unit/test_task_domain.py tests/unit/test_task_list_domain.py \
  tests/unit/test_openapi_contract.py tests/integration/test_task_query_results.py \
  tests/integration/test_task_list_queries.py tests/e2e/test_api_errors.py \
  tests/e2e/test_task_queries.py tests/e2e/test_task_lists.py --no-cov
-> 41 passed in 37.42s
.venv/bin/mypy --strict src tests migrations -> Success, 72 source files
.venv/bin/flake8 src tests migrations -> passed
```

Final verification (2026-10-08), on the implemented feature:

```text
.venv/bin/pytest -q -> 98 passed in 98.22s; 92.27% total application-source coverage
.venv/bin/mypy --strict src tests migrations -> passed (119 source files)
.venv/bin/black --check src tests migrations -> passed (119 files unchanged)
.venv/bin/flake8 src tests migrations -> passed
uv lock --check -> passed; uv sync --frozen -> passed
Docker build -> passed; docker run --rm --entrypoint id task-manager:local
  -> uid=10001(appuser)
```

Fresh and populated Compose rehearsals used isolated projects and retained volumes. Fresh
startup migrated through 0005, health passed, and the API remained healthy after restart.
The populated rehearsal stopped at 0004 without mapping, then completed after explicit
owner selection; historical list/task IDs and persisted attributes were preserved, the task
remained unassigned, and the selected owner could access the list through the protected API.
