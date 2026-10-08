# Implementation Plan: Manage Task Lists and Tasks

**Branch**: `dev` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-manage-task-lists/spec.md`
**Status**: Implemented; local verification is required before delivery.

## Summary

Deliver one Python API monolith for all eleven use cases, in four dependent increments.
Plain domain classes own normalization, invariants, and task transitions; application classes
group short related operations by resource through narrow persistence ports. Infrastructure supplies
FastAPI/Pydantic HTTP contracts, SQLAlchemy/psycopg adapters, and Alembic migrations.

Serialize writes per affected row, compare PATCH values after locking, commit before success,
and read each collection from one repeatable-read snapshot. The plan preserves every
user-confirmed specification rule, including Unicode normalization semantics, strict query
parameters, and half-up completion rounding. Research and limitations are in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11 (`requires-python = ">=3.11,<3.12"`; .python-version=3.11)

**Primary Dependencies**: FastAPI, Pydantic v2, Uvicorn, SQLAlchemy 2.x, psycopg 3 binary
extra, Alembic. Resolve compatible stable releases through uv; commit exact resolution.

**Dependency Management**: uv; pyproject.toml; committed uv.lock. Local verification checks lock freshness
then uses frozen installation. Runtime installation excludes dev dependencies.

**Storage**: PostgreSQL 17; two tables, FK cascade, checks, deterministic ordering indexes.
No SQLite fallback. Concrete image tags/digests are pinned during implementation.

**Testing**: pytest, pytest-cov >=7, coverage >=7.10, httpx; unit/integration/e2e markers in
pytest.ini. Coverage across all src/task_manager, including Uvicorn subprocess execution.

**Quality Tools**: .flake8; Black and strict mypy in pyproject.toml; aligned line length 88.
Explicit annotations also cover local variables (strict mypy alone does not enforce this).

**Target Platform**: Linux application container; Docker Compose; non-root application;
environment configuration; persistent development database volume and isolated ephemeral tests.

**Project Type**: One deployable monolith; src-layout package `task_manager` with Domain,
Application/UseCases, and Infrastructure layers. The distribution name in pyproject.toml
will be `task-manager`; the import package is `task_manager`.

**Module Cohesion**: Production behavior and tests stay grouped by responsibility.
File length prompts review, not an automatic split; there is no mandatory line limit.

**Performance Goals**: No latency/throughput target. Bound pages to 100; aggregate in SQL.
Avoid table-wide application locks or loading all matching rows to calculate counts.

**Constraints**: 26 functional requirements and AS-01–AS-39; no optional bonuses. At least
75% statement coverage, safe errors, deterministic concurrent-write/snapshot verification.

**Scale/Scope**: Shared workspace, no accounts; four resource paths, ten HTTP method/path
operations representing eleven use cases (status changes reuse PATCH), plus GET /health.

## Constitution Check

*Pre-research review found no incompatible choices. Persistence/isolation were research
questions; the required user review was open until Q1–Q3 below were answered. Post-design
review passes for planned compliance; these results do not assert implementation completion.*

| Gate | Before research | After design / evidence |
|------|-----------------|-------------------------|
| I. Stack and dependency management | PASS: prescribed stack accepted | PASS: Python 3.11, uv, lock checks/frozen installs, Docker/Compose in technical context and quickstart |
| II. Architecture | PASS: monolith and inward boundaries retained | PASS: explicit use-case classes, two narrow stores and transactional boundary below |
| III. Object-oriented responsibilities and cohesion | PASS: cohesive classes and grouped behavior required | PASS: application, HTTP, persistence, and test scenarios are grouped by responsibility; file length is reviewed without a fixed cap |
| IV. Typing and naming | PASS: explicit annotations/strict mypy accepted | PASS: typed commands, sentinel, records, ports; strict project checks and manual local-annotation review |
| V. Correctness/security | PASS: spec validation/transaction rules retained | PASS: FK/checks, locks/snapshots, pre-lookup schemas, safe errors and no credentials in artifacts |
| VI. Tests and coverage | PASS: all levels required | PASS: deterministic PostgreSQL races, actual API process, all-source child coverage and 75% aggregate gate |
| VII. Delivery | PASS: local/container/docs gates required | PASS: exact planned commands, migration ordering, persistent storage, non-root image and decision log |
| Scope and governance | PASS: core-first scope retained | PASS: four increments, no bonuses, final review and spec traceability |
| Structured review | OPEN: Q1–Q3 awaiting user | PASS: all three recommendations explicitly selected by user |

No amendment or exception is required. Local lint, formatting, strict typing, PostgreSQL,
running-API, coverage, Docker/Compose, restart, and Alembic drift checks have been exercised;
The latest review found strict mypy errors; local quality gates must pass before delivery.

## Structured Design Review *(mandatory)*

Completed 2026-10-07 using the `grilling` skill. Existing specification decisions stand.

| Question | User decision | Tradeoff / alternative |
|----------|---------------|------------------------|
| Q1 Persistence | SQLAlchemy + psycopg + Alembic | Additional proven dependencies instead of handwritten mapping/migrations |
| Q2 Concurrency | Row locks + repeatable-read queries | Several clear SQL queries per collection instead of one complex statement |
| Q3 Execution | Synchronous handlers/database and real Uvicorn E2E | Thread-pool execution instead of async complexity; no async throughput claim |

No unresolved review question remains. [DECISION_LOG.md](../../DECISION_LOG.md) records
these choices, rejected alternatives, and known limitations.

## Project Structure

### Documentation (this feature)

```text
specs/001-manage-task-lists/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.json
│   └── README.md
└── checklists/requirements.md
```

`tasks.md` is generated next by speckit-tasks, not by this planning command.

### Source Code (repository root)

```text
src/task_manager/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── task_list.py
│   ├── task.py
│   └── validation.py
├── application/
│   ├── __init__.py
│   ├── commands.py
│   ├── ports.py
│   ├── errors.py
│   ├── task_lists/
│   │   ├── operations.py
│   │   └── queries.py
│   └── tasks/
│       ├── operations.py
│       ├── queries.py
│       ├── update.py
│       └── __init__.py
└── infrastructure/
    ├── __init__.py
    ├── http/
    │   ├── __init__.py
    │   ├── api.py
    │   ├── support.py
    │   ├── validation.py
    │   ├── routes/
    │   │   ├── __init__.py
    │   │   ├── task_list_collection.py
    │   │   ├── task_lists.py
    │   │   ├── task_queries.py
    │   │   └── tasks.py
    │   └── schemas/
    │       ├── __init__.py
    │       ├── common.py
    │       ├── task.py
    │       ├── task_list.py
    │       └── task_requests.py
    └── persistence/
        ├── __init__.py
        ├── base.py
        ├── database.py
        ├── task_list_record.py
        ├── task_list_store.py
        ├── task_query_store.py
        ├── task_record.py
        └── task_store.py
migrations/versions/
tests/
├── conftest.py
├── fixtures/             # API process and isolated PostgreSQL fixtures
├── unit/                 # Domain behavior, use cases, and contract checks
├── integration/          # Persistence, concurrency, and snapshot scenarios
└── e2e/                  # API workflows grouped by resource and behavior
```

**Structure Decision**: Use `src/task_manager/` as the one import root because it names
the application, so imports such as `task_manager.domain.task` describe the code’s role.
Keep the repository/challenge name independent of the import package. Group related use cases
in descriptive resource modules; split at responsibility boundaries when this improves
comprehension, testing, or independent changes. Group test scenarios by behavior within their unit, integration, and E2E levels. Keep
HTTP routing, schemas, and persistence under their infrastructure packages.
Ordinary packages include __init__.py for coverage discovery. Replace the starter main.py
during implementation; the application entry point is
`task_manager.infrastructure.http.api:create_app` (Uvicorn --factory). Add only modules needed by the
current increment; this tree defines boundaries, not advance scaffolding.

Root delivery artifacts: pyproject.toml, uv.lock, .python-version, pytest.ini, .flake8,
alembic.ini, Dockerfile, .dockerignore, compose.yaml, .env.example, README.md,
and DECISION_LOG.md.

## Application and Persistence Boundaries

Domain TaskList and Task objects contain stdlib-typed attributes and explicit create/update
behavior. Task status-only changes route through Task.change_status. Normalize/validate all
supplied changes before applying any; update timestamps only on actual attribute changes.
Use uuid4 and UTC datetime values generated once at creation. For changed updates, choose
max(current UTC time, prior updated_at + one microsecond), ensuring even a same-clock-tick
change receives a distinct timestamp. No-op updates retain the exact stored value.

Application classes: CreateTaskListUseCase, GetTaskListUseCase, ListTaskListsUseCase,
UpdateTaskListUseCase, DeleteTaskListUseCase, CreateTaskUseCase, GetTaskUseCase,
UpdateTaskUseCase, DeleteTaskUseCase, QueryTasksUseCase. Group related classes in descriptive
modules under `application/task_lists/` or `application/tasks/`. UC-09 uses UpdateTaskUseCase and
Task.change_status; a separate class or endpoint for an identical operation adds no behavior.

Define TaskListStore and TaskStore as small application protocols with only required typed
create/get/lock/update/delete/page/count operations. Domain objects and typed projection
dataclasses cross these ports, never ORM models, sessions, HTTP responses, or Pydantic models.
A UnitOfWork protocol exposes the stores, context enter/exit, and explicit commit. Each use
case receives a Callable producing a fresh UnitOfWork. This transactional abstraction is
justified by atomic writes, locking, and read snapshots, not generic repository extensibility.
Infrastructure wires write factories to READ COMMITTED and collection factories to
REPEATABLE READ READ ONLY before first statement. Rollback/close on context exit; successful
writes explicitly commit before returning detached application data. Unit tests provide small
fakes for these existing boundaries; do not introduce a DI container or generic base repository.

Commands retain omission through one application Unset enum sentinel, using unions such as
str | Unset and str | None | Unset for descriptions. Nullable PATCH schema fields are checked
against model_fields_set before conversion; explicit null for nonnullable fields fails.
Never discard explicitly supplied defaults or unchanged values before acquiring locks.

All task mutations lock parent FOR KEY SHARE before child FOR UPDATE where applicable;
list mutations lock the list FOR UPDATE. Load the child using both IDs. Only supplied changed
columns are persisted, not a stale full entity. ON DELETE CASCADE handles list removal.
Direct DB constraints protect integrity even when application validation is bypassed.
No shared Session or long-lived ORM identity map; no post-commit lazy attribute access.

Collection existence, aggregates, and ordered page queries run in one short read-only snapshot.
Counts use SQL; percentage uses Decimal with sufficient integer-derived precision and
ROUND_HALF_UP, then a numeric response serializer (Pydantic Decimal's default string output
must not leak into the API). The maximum page size is 100, and no response streams after
its transaction is closed.

## HTTP Validation and Errors

[contracts/openapi.json](contracts/openapi.json) describes the public interface. Because
normalization precedes length checking, raw JSON Schema maxLength alone cannot express the
wire contract; normalization metadata/descriptions and behavioral tests specify those rules.

Pydantic v2 before validators call stdlib-only text helpers; strict text types reject bools
and numbers. Domain constructors/methods repeat invariant enforcement independently of HTTP.
Use one raw-query guard for allowed and duplicate keys on every route; collection models
supply defaults/ranges. Validate integer query syntax (reject fractional forms such as 1.0)
before int conversion. FastAPI path UUID parsing remains enabled; blanket strict model mode
must not reject ordinary UUID/query strings. Validate body/path/query structure before opening
the use-case persistence work. Empty PATCH and explicitly forbidden nulls fail at this boundary.

Translate request validation and domain validation to validation_error/422, scoped missing
resources to resource_not_found/404, and unexpected exceptions to internal_error/500. Format
details as field/message objects without raw values. Never echo SQL/paths/credentials in
responses or logs. Known integrity races use expected errors only when positively identified;
unknown database/commit errors roll back and remain generic 500. JSON serialization uses UTC
RFC 3339, numeric percentages, full response schemas, Location on 201, and no body on 204.

## Verification and Delivery Sequence

0. Minimal containerized FastAPI factory and GET /health; freeze dependencies, non-root
   runtime, initial lint/type/test configuration, Docker build and health smoke.
1. P1: list create/get through real PostgreSQL; initial reviewed Alembic migration; validate
   normalization/defaults/errors and persistence across restart. This is a working slice.
2. P2: list collection/PATCH/delete and list pagination. Add locked updates, no-op timestamps,
   isolated write tests, and list lifecycle E2E. Final cascade-with-children acceptance waits
   for P3; it must not be falsely marked complete here.
3. P3: task persistence/CRUD/status domain behavior and second migration if needed. Verify
   all nine transitions, membership, FK/cascade, commit failures, and controlled concurrent
   supplied/omitted/no-op writes. Complete the deferred cascade tests.
4. P4: task filters and snapshot-consistent summaries; verify fractional/tie rounding,
   unfiltered totals, empty/beyond-end pages, and controlled snapshot races. Finish all
   39 scenarios, documentation, restart check, local quality gates, and final constitution review.

Use threading events/barriers plus independent DB connections to orchestrate races, not
arbitrary sleeps. Test both serialized update orders. Lock waits need bounded timeouts so
failures do not hang verification. Test snapshot reads with a writer committed between the internal
read statements. Fault injection remains inside test adapters/fixtures, never public routes.

Use a dedicated test database service/credentials and per-test unique schemas, with safe
identifier quoting and guardrails rejecting a development URL. Migrations run per schema;
all test connections, including the child API, receive that schema's search_path. Tests
clean up only their own schema. No reliance on an outer uncommitted transaction that the
separate HTTP server cannot see. Development and production URLs are never truncation targets.

pytest.ini defines testpaths/markers and aggregate coverage options. pyproject.toml defines
coverage source=src/task_manager, subprocess patching, parallel data and the 75% gate; tests stop
and wait for Uvicorn before pytest-cov combines data. Verify coverage includes both an
unimported application module and actual E2E-only lines. Partial tests may run with --no-cov;
Final local verification always runs the full suite with coverage.

Local verification: uv lock --check; uv sync --frozen; Flake8; Black --check; mypy --strict over src/tests;
unit/integration/e2e and aggregate coverage; Docker build; Compose health/restart validation.
Include reviewed migrations in lint/format/type checks where applicable. Annotate locals
explicitly and document any necessary Any/suppression; no blanket ignores. Runtime env has
DATABASE_URL and optional DATABASE_SCHEMA for isolated tests, with values validated safely.

Compose services: db (persistent named volume), migrate (same app image, one-shot Alembic),
api (starts only after healthy DB and completed migration), and db-test (test profile,
ephemeral storage, separate port/credentials). Migrations are explicit, never implicit ORM
create_all on application startup. Uvicorn runs through uv run --frozen --no-dev; Docker
installs dependencies once, uses pinned images, and excludes local environments/secrets.

See [quickstart.md](quickstart.md) for planned commands. Copy tested commands into README
when implementation exists. Update DECISION_LOG for real deviations; reopen affected design
review if a decision changes the contract.

## Complexity Tracking

No constitutional violations. Two store ports and a transaction boundary are required by
inward dependencies, unit testing, locking, and atomicity. Read snapshots add multiple SQL
queries deliberately; optimize only with measured evidence while retaining snapshot semantics.
Offset pagination and aggregate scans have dataset-size costs; no speculative indexes,
cache, async conversion, or stored completion percentage is included.
