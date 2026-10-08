# Tasks: Manage Task Lists and Tasks

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/README.md), [quickstart.md](quickstart.md).
**Branch**: `dev` | **Constitution**: v4.0.0 | **Status**: Complete
**Tests**: Required in every story: domain/use-case unit, PostgreSQL persistence integration, and running-API/PostgreSQL end-to-end. Test-first ordering in each phase is organizational; implementation may proceed with tests alongside each behavior change.
**Format**: `- [ ] TNNN [P?] [USn?] Action with exact file path`. `[P]` means separate files with no prerequisite among the other marked tasks in that set.

## Phase 1: Setup (Runnable Container First)

**Goal**: Boot a Python 3.11 FastAPI process with GET /health in a reproducible, non-root container; smoke-check it before resource work.

**Independent Test**: Build the image, start api with Compose, and receive 200 {"status":"ok"} from /health.

**Depends on**: None.

- [X] T001 Update pyproject.toml and .python-version for Python 3.11, distribution `task-manager`, and the `src/task_manager/` import package, runtime FastAPI/Pydantic/Uvicorn/SQLAlchemy/psycopg/Alembic and dev pytest/pytest-cov/coverage/httpx/Flake8/Black/mypy via uv; generate and retain uv.lock in the repository.
- [X] T002 Create src/task_manager/__init__.py and src/task_manager/infrastructure/__init__.py, and replace the starter main.py with the package entry point described in plan.md.
- [X] T003 Create src/task_manager/infrastructure/http/api.py with a synchronous create_app factory and GET /health returning a typed Pydantic response; no persistence dependency for health.
- [X] T004 Create Dockerfile and .dockerignore with pinned Python/uv images, uv sync --frozen --no-dev, excluded .env/.venv/secrets, and a non-root application user.
- [X] T005 Create compose.yaml and .env.example for api, PostgreSQL 17 db with a named persistent volume, and a separate test-profile db-test with distinct credentials/storage; api has a healthcheck.
- [X] T006 Run the Docker build and Compose health smoke described in specs/001-manage-task-lists/quickstart.md; fix Dockerfile, compose.yaml, or src/task_manager/infrastructure/http/api.py until the container serves /health as non-root.
- [X] T007 Configure pytest.ini markers and testpaths, .flake8, and Black/strict mypy/coverage settings in pyproject.toml, including source=src/task_manager, subprocess coverage patch, and the 75% all-source statement gate.

**Checkpoint**: Container image builds and /health responds; frozen dependency install and non-root execution verified.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Prepare the narrow application boundary, error mapping, database connections, and isolated PostgreSQL test foundation required by every story.

**Independent Test**: A typed application use case can receive a fresh transaction/store from dependency wiring, and a test cannot connect to the development database.

**Depends on**: Complete Phase 1.

- [X] T008 Create src/task_manager/application/__init__.py, src/task_manager/domain/__init__.py, and src/task_manager/application/errors.py with explicit business validation and missing-resource exceptions.
- [X] T009 Create src/task_manager/application/ports.py with TaskListStore/TaskStore and UnitOfWork protocols plus typed transaction factory; keep FastAPI, SQLAlchemy, and database imports out of Domain/Application.
- [X] T010 Create src/task_manager/infrastructure/persistence/database.py with environment-validated DATABASE_URL, per-invocation synchronous sessions, READ COMMITTED write and REPEATABLE READ READ ONLY collection factories, explicit commit/rollback/close, and optional safely validated test schema.
- [X] T011 Create src/task_manager/infrastructure/persistence/ skeleton implementing the application transaction/store ports with SQLAlchemy sessions; keep ORM records inside Infrastructure and wire adapters in src/task_manager/infrastructure/http/api.py.
- [X] T012 Add error handlers in src/task_manager/infrastructure/http/api.py mapping validation_error to 422, resource_not_found to 404, and unexpected exceptions to generic internal_error 500; src/task_manager/infrastructure/http/schemas/ defines typed error/detail and health responses without leaking input values.
- [X] T013 Add raw query-key validation in src/task_manager/infrastructure/http/api.py: reject unknown and repeated keys on every route before lookup; retain strict body/path validation with Pydantic schemas in src/task_manager/infrastructure/http/schemas/.
- [X] T014 Create PostgreSQL and Uvicorn fixtures under tests/fixtures/, register them from tests/conftest.py, and guard test database isolation with per-test schemas and graceful subprocess shutdown.

**Checkpoint**: Ports and wiring are usable, validation/error envelopes are defined, and dedicated test data cannot touch development storage.

---

## Phase 3: User Story 1 — Create and retrieve a durable list (P1)

**Goal**: Implement UC-01/UC-02: create and retrieve normalized lists from real PostgreSQL.

**Independent Test**: Create a list, follow its Location to GET, restart the application with retained database volume, and retrieve the same ID, attributes, and UTC timestamps.

**Depends on**: Phase 2. First working slice, not the complete MVP. Covers FR-001, FR-002, and relevant FR-015–FR-018/FR-020–FR-025; AS-01–AS-06 plus applicable AS-32–AS-35/AS-37–AS-38.

### Tests (required; draft in parallel after prerequisite phase)

Tests must exercise the linked scenarios and ship with the behavior.

- [X] T015 [P] [US1] Write grouped domain and use-case assertions for list creation, normalization, boundaries, duplicates, timestamps, invalid inputs, and missing lookup in tests/unit/test_task_list_domain.py and tests/unit/test_task_list_use_cases.py.
- [X] T016 [P] [US1] Write PostgreSQL list persistence, constraints, paging, and concurrency assertions in tests/integration/test_task_list_*.py modules.
- [X] T017 [P] [US1] Write running-API list workflows, validation/error responses, and restart persistence in behavior-focused tests/e2e/test_task_*.py modules.

### Implementation

- [X] T018 [US1] Implement stdlib-only Unicode text normalization/validation and aware UTC timestamp helpers in src/task_manager/domain/validation.py; no HTTP/ORM imports.
- [X] T019 [US1] Implement TaskList.create and immutable identity/created_at behavior in src/task_manager/domain/task_list.py using typed attributes and initial equal UTC timestamps.
- [X] T020 [US1] Define typed create/get commands and result DTOs in src/task_manager/application/commands.py; group list creation in task_lists/operations.py and retrieval in task_lists/queries.py using injected ports; commit before returning create result.
- [X] T021 [US1] Create SQLAlchemy TaskList record and indexes in src/task_manager/infrastructure/persistence/task_list_record.py and task_record.py; configure alembic.ini and migrations/env.py, and add reviewed first revision migrations/versions/0001_task_lists.py with nonnull/normalized-length/UTC timestamp checks.
- [X] T022 [US1] Implement TaskListStore create/get and domain mapping in src/task_manager/infrastructure/persistence/, using the per-request session from src/task_manager/infrastructure/persistence/database.py.
- [X] T023 [US1] Add strict create/list-response Pydantic schemas and before validators in src/task_manager/infrastructure/http/schemas/; reject numeric/bool text, unknown/system-managed fields, null/blank names, oversized text, and serialize UTC RFC 3339.
- [X] T024 [US1] Wire POST /api/v1/task-lists and GET /api/v1/task-lists/{list_id} in src/task_manager/infrastructure/http/api.py with 201 Location, 200 list without tasks, request validation before lookup, and safe errors.
- [X] T025 [US1] Use tests/fixtures/ to migrate each isolated schema and launch the real API; run the list unit, integration, and E2E scenarios and verify the documented first-slice smoke.

**Checkpoint**: UC-01/UC-02 and scoped tests pass against PostgreSQL; the first slice survives restart.

---

## Phase 4: User Story 2 — Maintain the list collection (P2)

**Goal**: Implement UC-03–UC-05: browse, patch, and delete lists with accurate pagination and no-op timestamps.

**Independent Test**: Seed several lists, page in created_at/UUID order, patch only supplied fields, clear a description, and delete one; verify the remainder and missing-resource behavior.

**Depends on**: Phase 3. Cascade-with-children AS-11 is deferred until the task table exists in US3. Covers FR-003–FR-005 and relevant FR-014–FR-019/FR-022/FR-024–FR-025; AS-07–AS-10/AS-12 and list portions of AS-22/AS-26–AS-27/AS-33/AS-36–AS-38.

### Tests (required; draft in parallel after prerequisite phase)

Tests must exercise the linked scenarios and ship with the behavior.

- [X] T026 [P] [US2] Cover TaskList.update and use-case behavior, omitted/null/unchanged fields, and validation boundaries in grouped list unit modules.
- [X] T027 [P] [US2] Cover locked updates/deletes, rollback, snapshot paging, stable order, and concurrent PATCH behavior in grouped list integration modules.
- [X] T028 [P] [US2] Cover list GET/PATCH/DELETE responses, strict queries, empty pages, and no-op timestamps in tests/e2e/test_task_lists.py.

### Implementation

- [X] T029 [US2] Add TaskList.update domain behavior in src/task_manager/domain/task_list.py: validate all supplied changes before mutation, compare after lock, advance updated_at only for persisted attribute changes.
- [X] T030 [US2] Add Unset-aware typed list PATCH and pagination commands to src/task_manager/application/commands.py; group list mutation operations in task_lists/operations.py and list reads in task_lists/queries.py.
- [X] T031 [US2] Implement TaskListStore lock/update/delete/page/count in src/task_manager/infrastructure/persistence/; SELECT FOR UPDATE before comparing PATCH fields, write only supplied changed columns, commit before success, and use one repeatable-read read-only snapshot for collection count/page.
- [X] T032 [US2] Add list PATCH and collection Pydantic schemas in src/task_manager/infrastructure/http/schemas/ using model_fields_set to preserve explicit null/default/presence, plus strict limit/offset parsing before lookup.
- [X] T033 [US2] Wire GET /api/v1/task-lists, PATCH/DELETE /api/v1/task-lists/{list_id} in src/task_manager/infrastructure/http/api.py; return ordered items/total/limit/offset, full 200 resource, and bodyless 204.
- [X] T034 [US2] Run the US2 unit, PostgreSQL integration, and running-API suites and update specs/001-manage-task-lists/quickstart.md only if verified command behavior differs; leave AS-11 child cascade pending until US3.

**Checkpoint**: List management works independently with PostgreSQL; only child-cascade acceptance remains deferred to US3.

---

## Phase 5: User Story 3 — Manage tasks and progress states (P3)

**Goal**: Implement UC-06–UC-10: parent-scoped task CRUD, defaults, atomic updates, all status transitions, and cascade integrity.

**Independent Test**: Seed two lists, create a task under one, complete/reopen it through PATCH, reject cross-list operations, delete it without deleting its parent, then delete a list with children atomically.

**Depends on**: Phase 4. Completes deferred AS-11. Covers FR-006–FR-010 and relevant FR-015–FR-020/FR-022–FR-025; AS-11/AS-13–AS-22, task portions of AS-32–AS-38.

### Tests (required; draft in parallel after prerequisite phase)

Tests must exercise the linked scenarios and ship with the behavior.

- [X] T035 [P] [US3] Cover Task.create/update/change_status defaults, all status combinations, validation, atomicity, clearing, and no-op timestamps in tests/unit/test_task_domain.py.
- [X] T036 [P] [US3] Cover task relationships, deletion rollback/races, and concurrent updates in grouped tests/integration/test_task_*.py modules.
- [X] T037 [P] [US3] Cover task CRUD, wrong-parent 404s, Location, all status transitions, and parent retention in tests/e2e/test_tasks.py.

### Implementation

- [X] T038 [US3] Implement TaskStatus/TaskPriority, Task.create/update/change_status, all invariants, immutable list_id and UTC timestamps in src/task_manager/domain/task.py; reuse src/task_manager/domain/validation.py.
- [X] T039 [US3] Add typed task creation/PATCH/status commands and scoped result DTOs in src/task_manager/application/commands.py; group related task create/delete, query, and update behavior under application/tasks/; UC-09 uses UpdateTaskUseCase.
- [X] T040 [US3] Add typed SQLAlchemy Task record, FK ON DELETE CASCADE, parent/order index and status/priority/check constraints to src/task_manager/infrastructure/persistence/task_list_record.py and task_record.py, and reviewed migration migrations/versions/0002_tasks.py.
- [X] T041 [US3] Implement TaskStore scoped create/get/lock/update/delete in src/task_manager/infrastructure/persistence/; lock parent FOR KEY SHARE before task FOR UPDATE, avoid stale ORM state, persist only supplied changed columns, and commit before returning.
- [X] T042 [US3] Add strict create/PATCH/task-response Pydantic schemas and presence/null/enum/Unicode validation in src/task_manager/infrastructure/http/schemas/; list_id comes only from path.
- [X] T043 [US3] Wire nested POST/GET/PATCH/DELETE task routes in src/task_manager/infrastructure/http/api.py; every task lookup uses parent and task IDs, status-only PATCH uses normal task update, and 204 has no body.
- [X] T044 [US3] Verify populated-list cascade behavior and rollback through grouped integration and E2E deletion scenarios.

**Checkpoint**: Task lifecycle and all nine status combinations work through the running API; parent FK, cascade, and controlled concurrency tests pass.

---

## Phase 6: User Story 4 — Browse tasks and trust completion summaries (P4)

**Goal**: Implement UC-11: combined filters, deterministic pagination, matched count, and unfiltered summary from one committed snapshot.

**Independent Test**: Seed the four-task fixture, filter pending AND high, verify one match with 4 total/2 completed/50%, then change pages, states, and tasks and verify whole-list results.

**Depends on**: Phase 5 and US2 pagination. Covers FR-011–FR-014/FR-024–FR-026; AS-23–AS-31/AS-39 and relevant AS-34/AS-37.

### Tests (required; draft in parallel after prerequisite phase)

Tests must exercise the linked scenarios and ship with the behavior.

- [X] T045 [P] [US4] Cover QueryTasksUseCase delegation in tests/unit/test_task_query_use_case.py and exercise zero/full/fractional completion through focused E2E query tests.
- [X] T046 [P] [US4] Cover filtering, pagination, ordering, and repeatable-read snapshots in grouped PostgreSQL query modules.
- [X] T047 [P] [US4] Cover individual/combined/no-match filters, invalid queries, pages, and filter-independent summaries in tests/e2e/test_task_queries.py and tests/e2e/test_task_completion.py.

### Implementation

- [X] T048 [US4] Add typed task query, page, and CompletionSummary projections at the application boundary in src/task_manager/application/ports.py and place QueryTasksUseCase under src/task_manager/application/tasks/; Decimal half-up percentage, zero for empty, no stored summary.
- [X] T049 [US4] Implement TaskStore filtered count, ordered page, and unfiltered total/completed aggregates in src/task_manager/infrastructure/persistence/; parent existence, counts and items share one short repeatable-read read-only transaction.
- [X] T050 [US4] Add task query and collection response schemas in src/task_manager/infrastructure/http/schemas/; numeric JSON percentage and limit 1–100/offset≥0 defaults 20/0, exact case-sensitive filters.
- [X] T051 [US4] Wire GET /api/v1/task-lists/{list_id}/tasks in src/task_manager/infrastructure/http/api.py with status/priority AND filtering before pagination and snapshot-consistent items/matched_tasks/summary.
- [X] T052 [US4] Run the full PostgreSQL-backed US4 tests and cross-check computed outputs against AS-23–AS-31 and AS-39 in specs/001-manage-task-lists/spec.md; retain summary for empty and beyond-end pages.

**Checkpoint**: All eleven use cases and all four stories are implemented; filtered/whole-list completion and snapshot tests pass.

---

## Phase 7: Polish and Delivery Gates

**Goal**: Prove the delivered monolith against the constitution, complete local verification/docs, and verify reproducible restarts.

**Independent Test**: A clean checkout passes the documented uv, pytest, quality, Docker/Compose, and persistence checks.

**Depends on**: All four user story phases complete.

- [X] T053 Removed by user scope decision: automated pipeline delivery is not required. Local verification remains required under T055–T057.
- [X] T054 Audit pytest.ini, pyproject.toml, and tests/fixtures/ so full-suite coverage includes unimported application modules and the gracefully stopped Uvicorn child; verify isolated schemas and independent test markers.
- [X] T055 Run uv run --frozen flake8 src tests migrations, uv run --frozen black --check src tests migrations, and uv run --frozen mypy --strict src tests migrations; correct issues in .flake8, pyproject.toml, and affected source files, and inspect local annotations, names, Any/suppressions.
- [X] T056 Run uv run --frozen pytest and verify tests/unit/, tests/integration/, and tests/e2e/ assert AS-01–AS-39, all 11 use cases, failure and concurrency paths, and aggregate >=75% coverage without excluding business logic; fix any failures in the affected test/source files.
- [X] T057 Build Dockerfile image and run compose.yaml health/restart checks from specs/001-manage-task-lists/quickstart.md; verify non-root user, frozen install, migration ordering, secret-free image/logs, and persisted resources after api/db restart with volume retained.
- [X] T058 Update README.md with tested uv setup, environment variables, API and Compose execution, migrations, all quality/test commands, expected responses, and known limitations; align specs/001-manage-task-lists/quickstart.md with actual commands.
- [X] T059 Review and update DECISION_LOG.md with actual architectural choices, tradeoffs, deviations, and measured limitations; compare generated API schema from src/task_manager/infrastructure/http/api.py against specs/001-manage-task-lists/contracts/openapi.json and reconcile any drift.
- [X] T060 Perform final principle-by-principle compliance review against .specify/memory/constitution.md and FR/AS traceability in specs/001-manage-task-lists/spec.md; record any remaining conflict and do not mark complete until all delivery gates pass.
- [X] T061 Superseded by Constitution v4.0.0: replace the former file-length cap with responsibility-based cohesion guidance and remove its enforcement test.
- [X] T062 Group related use cases by resource; organize routes, schemas, and HTTP support under src/task_manager/infrastructure/http/ and persistence under src/task_manager/infrastructure/persistence/; review cohesion at responsibility boundaries.
- [X] T063 Run unit, PostgreSQL integration, end-to-end, quality, and Docker checks after the module reorganization.
- [X] T064 Apply responsibility-based grouping to production and test modules; synchronize templates, AGENTS.md, README.md, plan.md, and this task list with Constitution v4.0.0.
- [X] T065 Group tests by domain/use case, persistence/concurrency/query behavior, and API workflow; move shared fixtures into tests/fixtures/ and review cohesion across src/ and tests/.
- [X] T066 Run the complete PostgreSQL-backed test suite, formatting, lint, and strict typing after test reorganization.

**Checkpoint**: Full local and clean-checkout verification pass, and docs accurately describe the delivered system.

---

## Dependencies and Execution Order

```text
Phase 1 Setup → Phase 2 Foundation → US1 list create/get → US2 list management
                                               → US3 task lifecycle + deferred cascade
                                               → US4 task queries/summaries → Phase 7 gates
```

- US1 needs the foundation and delivers the first working slice. It is not the complete MVP.
- US2 needs the list identity/persistence built in US1. Its populated cascade case waits for US3.
- US3 needs existing list routes and locks from US1/US2; it completes the deferred cascade test.
- US4 needs task persistence and status changes from US3 plus pagination from US2.
- Phase 7 needs all four stories. The complete MVP is US1–US4 with delivery gates, not US1 alone.
- Within each story, the three `[P]` test files can be drafted independently from the spec/contract once the prior phase is done. Merge them with implementation and fixtures before marking the story complete. Other tasks are sequential because they touch shared modules or depend on new behavior.

## Parallel Opportunities

| Story | Independent draft tasks | Join point |
|-------|-------------------------|------------|
| US1 | T015, T016, T017 (unit, integration, E2E tests in separate files) | Implement and run all three against the completed story |
| US2 | T026, T027, T028 (unit, integration, E2E tests in separate files) | Implement and run all three against the completed story |
| US3 | T035, T036, T037 (unit, integration, E2E tests in separate files) | Implement and run all three against the completed story |
| US4 | T045, T046, T047 (unit, integration, E2E tests in separate files) | Implement and run all three against the completed story |

These opportunities describe file-independent work; they do not remove the feature-level US1→US2→US3→US4 dependencies. A single implementer can complete them sequentially.

## Implementation Strategy

1. Finish Phase 1 and demonstrate a real non-root container health response.
2. Finish the shared foundation without creating unused task code ahead of US1.
3. Deliver US1 create/retrieve with PostgreSQL and restart evidence as the first working slice.
4. Extend in priority order: US2 list management, US3 task lifecycle and populated cascade, US4 filters and summaries. At each checkpoint, run that story’s unit, integration, and real-API tests.
5. Finish Phase 7 full-suite/local/container/docs/constitution gates before calling the full MVP complete.

## Notes

- Every checkbox references a repository-relative exact file path. Existing files are extended where appropriate; do not add generic framework modules.
- Implement only the tests needed to demonstrate behavior, but cover the acceptance scenarios and all three constitutional test levels. Controlled database concurrency tests use barriers and bounded waits, never timing sleeps.
- Do not use SQLite for persistence or the live development database for tests. Do not claim a phase complete while a listed check fails.
