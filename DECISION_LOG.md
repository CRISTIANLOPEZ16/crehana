# Decision Log

## 2026-10-07 — Task management implementation plan

Status: implementation complete; all delivery gates below pass. Source:
[specs/001-manage-task-lists/plan.md](specs/001-manage-task-lists/plan.md).
User confirmed all three structured planning review recommendations.

| Decision | Rationale | Alternatives / consequences |
|----------|-----------|-----------------------------|
| One `src/task_manager/` import root | Names the application in imports such as `task_manager.domain.task` while preserving the three layers | Company/repository branding remains independent; no extra package root |
| Group use cases by resource; group infrastructure under `http/` and `persistence/` | Keeps routes, schemas, and stores discoverable by responsibility while avoiding infrastructure-root clutter | Split at responsibility boundaries when comprehension, testing, or independent change benefits; avoid one-file-per-function fragmentation |
| Separate list/task migration revisions; explicitly named task foreign key | Task lifecycle depends on lists and deleting a list must cascade in PostgreSQL | A third revision names the FK after its initial creation; tests migrate isolated schemas from zero |
| SQLAlchemy 2.x + psycopg 3 + Alembic | Typed mapping and reviewed ordered migrations; ORM confined to Infrastructure | Direct SQL reduces packages but adds mapping/migration work; no generic repository framework |
| Synchronous handlers and database access | Matches bounded CRUD scope with one programming model | Async deferred absent throughput evidence; sessions belong to individual use cases |
| READ COMMITTED writes with row locks | Compare PATCH after locking; preserve explicit intent, omitted fields, and no-op timestamps | No optimistic version conflicts; overlapping writes use serialized last-write-wins |
| Parent key-share lock before child mutations; FK cascade | Consistent lock order and atomic integrity through deletion races | Parent FOR UPDATE everywhere would unnecessarily serialize siblings |
| Read-only repeatable-read collections | Existence, items, counts, and summary share a snapshot across simple queries | More round trips than one combined statement; keep transactions short |
| Narrow store ports and UnitOfWork | Required inward dependencies plus explicit commit/rollback and snapshot boundaries | Small transaction abstraction is justified; no DI container or generic repository base |
| Pydantic boundary schemas and plain domain behavior | Validates before lookup without making domain correctness depend on HTTP | Explicit typed PATCH presence avoids dropping null/default/unchanged supplied values |
| Real Uvicorn E2E subprocess with coverage instrumentation | Meets running-API requirement and includes executed server lines in aggregate coverage | TestClient alone is insufficient; graceful shutdown required for coverage collection |
| PostgreSQL-only isolated test database/schemas | Same constraints/isolation as runtime; separate credentials and per-test state | SQLite and shared development databases rejected; migrations must support test search_path |
| uv lock freshness check plus frozen install | Checks both committed dependency agreement and reproducible installation | Frozen alone does not verify freshness; image versions/digests pinned during implementation |
| One-shot migration service before non-root API | Avoids each worker racing to migrate | No create_all fallback; upgrade failure blocks API startup |
| Publish expected error responses in generated OpenAPI | Keeps documented 404/422/500 envelopes aligned with runtime handlers and the checked-in contract | A small FastAPI response metadata map uses `Any` only at the framework's OpenAPI extension boundary |
| Group production modules and tests by cohesive responsibility | File length is a review signal rather than a hard limit; preserve related behavior together | Supersedes the former fixed cap; split for comprehension, testing, or independent change |

Known limitations: shared workspace without authentication; no task moves, recovery, conflict
versions, or pagination snapshots across requests. Offset paging and exact aggregate counts
cost more as data grows. No throughput promise, speculative cache/indexes, or async rewrite.
Parent/row locks can wait; tests bound waits, and unexpected failures remain generic errors.
An uncertain network failure at commit cannot guarantee whether the DB committed; the API
must never claim success without confirmation, and retries of creation are not idempotent.
This inherent limitation does not permit returning success before commit or skipping rollback
of confirmed pre-commit failures.

Detailed primary sources and rationale: [research.md](specs/001-manage-task-lists/research.md).
Constitution v4.0.0 and the completed specification remain authoritative; no exception was added.
HTTP routing, schemas, and shared support live under
`infrastructure/http/`, and persistence adapters live under `infrastructure/persistence/`.
Historical verification after test organization (before removing the file-length test): 52 tests pass with 96.00% total source coverage; Flake8, Black check,
strict mypy, generated route/status parity, the Docker image build, and Compose health pass.
The API restart check confirms a created list remains readable afterward. PostgreSQL
integration and real-Uvicorn end-to-end checks run against isolated per-test schemas.

## 2026-10-07 — Local assessment verification

The user removed CI/CD from assessment scope because it is not required by the challenge.
The GitHub Actions workflow was removed and Constitution v3.0.0 replaces pipeline/merge
requirements with local pre-delivery checks. Tests, coverage, strict mypy, Flake8, Black,
lockfile verification, and Docker checks remain required. The previous all-gates-pass
statement is historical: the latest review found two strict mypy errors in
`tests/e2e/test_api_errors.py`; removing the pipeline does not resolve those errors.

## 2026-10-07 — Cohesion instead of a file-length cap

The user approved replacing the fixed file-length cap with responsibility-based review.
Constitution v4.0.0 keeps related production behavior and test scenarios together and uses
file length only as a review signal. The line-count test was removed. Existing module
boundaries remain; no application refactor is needed for this policy amendment.
Behavioral tests, coverage, strict typing, linting, and formatting remain required.
