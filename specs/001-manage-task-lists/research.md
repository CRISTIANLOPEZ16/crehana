# Research: Manage Task Lists and Tasks

**Date**: 2026-10-07
**Status**: Resolved; planning review Q1–Q3 confirmed by the user.

The decisions below combine official documentation with project-specific design inferences.
Exact Python-3.11-compatible dependency releases are resolved and committed in `uv.lock`
during implementation; no unverified “latest” release is prescribed.

## R1. Persistence and execution

**Decision**: SQLAlchemy 2.x synchronous ORM, psycopg 3, and Alembic; synchronous FastAPI
handlers. Use typed infrastructure records and explicit conversion to plain domain objects.

**Rationale**: The user chose established mapping/migration tools and a synchronous execution
model. Typed mappings support strict typing. FastAPI executes ordinary route functions in a
thread pool; blocking DB work stays in those functions, not in an async handler. One session
belongs to one use-case invocation and is never shared between requests or threads.

**Alternatives considered**: Direct psycopg with handwritten SQL/migrations has fewer
packages but adds mapping/migration work; async introduces an unneeded second programming
model; generic repository frameworks add no present value.

Sources: [SQLAlchemy typed mappings](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html),
[psycopg dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#psycopg),
[Alembic migration review](https://alembic.sqlalchemy.org/en/latest/autogenerate.html),
[FastAPI execution model](https://fastapi.tiangolo.com/async/).

## R2. Concurrent PATCH and transaction boundaries

**Decision**: READ COMMITTED writes. Lock the target row with SELECT FOR UPDATE before
reading its editable state. Apply every supplied field to that freshly loaded domain object;
compare normalized values there. Update only supplied changed columns plus updated_at.
Commit inside the use case before returning detached data. Roll back every pre-commit failure.

**Rationale**: A waiting locking read receives the latest committed row, satisfying the
user-confirmed concurrent no-op semantics and preserving unrelated fields. No application
cache or earlier ORM identity-map load may replace the locked state. Use a fresh session,
or explicitly refresh a previously loaded record when locking. Domain methods own behavior;
infrastructure owns locking/mapping. Do not commit in a dependency's post-response cleanup.

**Alternatives considered**: Optimistic version checks are excluded; global locks serialize
unrelated resources; comparing before locking drops client intent. Blind full-object writes
risk overwriting omitted fields.

Sources: [PostgreSQL isolation](https://www.postgresql.org/docs/current/transaction-iso.html),
[SQLAlchemy sessions](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

## R3. Parent integrity and deletion races

**Decision**: FK ON DELETE CASCADE; acquire a parent FOR KEY SHARE lock before task creation,
and before task writes that also lock a child. Always parent before child. List PATCH/DELETE
lock the list FOR UPDATE. Parent key-share locks are compatible with sibling task operations.

**Rationale**: A deleted parent becomes a controlled 404 before child insertion; the FK is
still the integrity authority. A consistent lock order avoids a parent/child lock inversion.
Deleting a list is one database cascade, never a Python loop of independent deletions.

**Alternatives considered**: Existence check without a lock races with deletion; exclusive
parent locks for all task changes unnecessarily serialize sibling tasks; manual cascades
add writes and rollback opportunities. No automatic broad retry hides unexpected failures.

Sources: [PostgreSQL row locks](https://www.postgresql.org/docs/current/explicit-locking.html),
[constraints](https://www.postgresql.org/docs/current/ddl-constraints.html).

## R4. Snapshot-consistent collections

**Decision**: Short REPEATABLE READ, READ ONLY transactions for list and task collections.
Set transaction characteristics before the first SELECT; task parent existence, filtered
count, page, and unfiltered aggregate all share that transaction. Use simple SQL aggregates,
never load every task into Python. Compute the percentage with Decimal ROUND_HALF_UP.

**Rationale**: The user selected several simple queries over one combined SQL statement.
The snapshot makes empty pages, counts, and parent existence agree even during concurrent
writes. A new request uses a new transaction. Pagination is not frozen across requests.

**Alternatives considered**: Multiple READ COMMITTED queries can mix snapshots. A single
statement is viable but more complex for a missing parent and beyond-end page. SERIALIZABLE
adds unnecessary retry semantics; stored percentage risks drift.

Sources: [PostgreSQL SET TRANSACTION](https://www.postgresql.org/docs/current/sql-set-transaction.html),
[SQLAlchemy isolation](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#setting-transaction-isolation-levels-dbapi-autocommit),
[Python Decimal rounding](https://docs.python.org/3.11/library/decimal.html).

## R5. Validation and partial updates

**Decision**: Pydantic v2 with extra=forbid, strict string fields, and before validators that
strip strings before length checks. Domain constructors/methods independently enforce the
same invariants using stdlib-only normalization helpers. Track model_fields_set; convert
explicitly into typed application commands with an explicit unset sentinel. Null clears a
description but is invalid for names, titles, status, and priority. Do not use exclude_none
or exclude_defaults for PATCH. Reject raw repeated query keys before collapsing query data.

**Rationale**: HTTP omission, null, default, and explicit unchanged values have different
meanings. Query values arrive as strings: validate integer syntax/range rather than enabling
blanket strict Python-int mode. Validate all request structure before use-case resource lookup.
Use one small shared infrastructure query guard, including an empty allowed-key set on routes
without query parameters. Exact enum values remain case-sensitive and untrimmed.

**Alternatives considered**: Permissive coercion, duplicate-key collapsing, or experimental
missing-value features weaken the agreed contract. Pydantic is not imported by Domain.

Sources: [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/),
[serialization/presence](https://docs.pydantic.dev/latest/concepts/serialization/),
[FastAPI partial updates](https://fastapi.tiangolo.com/tutorial/body-updates/),
[query models](https://fastapi.tiangolo.com/tutorial/query-param-models/),
[Starlette requests](https://starlette.dev/requests/).

## R6. All-source coverage and real E2E

**Decision**: pytest unit/integration/e2e tests; PostgreSQL-only persistence tests. E2E fixtures
launch a real Uvicorn subprocess on a loopback port, wait for readiness, exercise HTTP with
httpx, then shut it down gracefully and wait. pytest-cov >=7 with compatible coverage >=7.10
uses coverage patch=["subprocess"]; source=["src/task_manager"] counts unimported modules.

**Rationale**: Current pytest-cov delegates child-process instrumentation to coverage.py.
A separately launched Docker server is not automatically covered. The instrumented host
server and Docker smoke check serve different purposes. Merge child data before enforcing
the aggregate 75% gate. Put pytest configuration in pytest.ini; coverage configuration in
pyproject.toml. Partial test selections can disable the aggregate gate locally only.

**Alternatives considered**: In-process TestClient alone is not E2E; SQLite is not PostgreSQL;
import-only coverage excludes missing tests; killing the server can lose coverage data.

Sources: [source discovery](https://coverage.readthedocs.io/en/latest/source.html),
[pytest-cov subprocess support](https://pytest-cov.readthedocs.io/en/stable/subprocess-support.html),
[coverage subprocess management](https://coverage.readthedocs.io/en/latest/subprocess.html).

## R7. Reproducible delivery

**Decision**: uv exclusively; Python 3.11; PostgreSQL 17 as the initial supported major.
Commit uv.lock. Local verification runs uv lock --check then uv sync --frozen; Docker uses
uv sync --frozen --no-dev. Pin concrete Python/uv/PostgreSQL image versions and digests
when implementation verifies availability. Run application and migrations as a non-root user.

**Rationale**: Frozen installation does not verify lockfile freshness, so local verification checks both.
One-shot migration service precedes application startup, avoiding migrations in every worker.
Compose development storage is a named volume; tests use a separate ephemeral DB service.

**Alternatives considered**: Floating latest tags, startup dependency resolution, per-worker
migrations, and a shared development/test database undermine reproducibility or isolation.

Sources: [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/),
[uv CLI](https://docs.astral.sh/uv/reference/cli/),
[uv Docker](https://docs.astral.sh/uv/guides/integration/docker/).
