# Task Manager API

A synchronous FastAPI service for task lists and their tasks. It uses PostgreSQL for
persistent storage, Alembic for schema changes, and `uv` for Python 3.11 dependencies.
Production modules and tests are grouped by cohesive responsibility. File length is a
review signal, not a fixed limit; splits follow responsibility boundaries.

The `src/task_manager/` package follows Domain, Application, and Infrastructure boundaries.
HTTP routes and schemas are grouped under `infrastructure/http/`; database records and stores
are grouped under `infrastructure/persistence/`. Tests stay divided into unit, integration,
and end-to-end levels, with shared fixtures under `tests/fixtures/` and scenarios grouped by
behavior.

## Local setup

Install `uv` and Docker with Compose, then prepare the ignored local configuration:

```sh
cp .env.example .env
```

Replace both password placeholders in `.env` with local-only values. Do not commit that
file. Install Python and dependencies, then start PostgreSQL and apply migrations before
the API starts:

```sh
uv python install 3.11
uv lock --check
uv sync --frozen
docker compose up --build -d --wait
curl --fail-with-body http://localhost:8000/health
```

Compose exposes the development database on port 55432 and the API on port 8000. PostgreSQL
data is stored in the named `postgres_data` volume. The one-shot migration service must
finish before the non-root API container starts. Runtime dependencies install from
`uv.lock` with `uv sync --frozen --no-dev`.

## Configuration

| Variable | Purpose |
|----------|---------|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Development Compose database credentials |
| `DATABASE_URL` | PostgreSQL psycopg URL for host-run Alembic/API commands |
| `TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`, `TEST_POSTGRES_DB` | Separate test database credentials |
| `TEST_DATABASE_URL` | Dedicated PostgreSQL URL used by integration tests |
| `DATABASE_SCHEMA` | Optional validated schema for a test or isolated runtime |

`DATABASE_URL` must use `postgresql+psycopg://`. Keep credentials out of source control,
images, and logs. Compose supplies its internal database hostname to the migration and API
containers.

## API

All resources are under `/api/v1`:

| Method | Path | Result |
|--------|------|--------|
| `POST` | `/task-lists` | Create list; 201 and `Location` |
| `GET` | `/task-lists` | Paginated lists (`limit`, `offset`) |
| `GET` | `/task-lists/{list_id}` | Retrieve one list |
| `PATCH` | `/task-lists/{list_id}` | Partially update list |
| `DELETE` | `/task-lists/{list_id}` | Delete list and its tasks; 204 |
| `POST` | `/task-lists/{list_id}/tasks` | Create task; 201 and `Location` |
| `GET` | `/task-lists/{list_id}/tasks` | Filter/page tasks and return completion summary |
| `GET` | `/task-lists/{list_id}/tasks/{task_id}` | Retrieve task within its list |
| `PATCH` | `/task-lists/{list_id}/tasks/{task_id}` | Update task, including status |
| `DELETE` | `/task-lists/{list_id}/tasks/{task_id}` | Delete task; 204 |

Text is trimmed before length checks; blank descriptions become null. Task status is
`pending`, `in_progress`, or `completed`; priority is `low`, `medium`, or `high`. Collection
pages are ordered by creation time then UUID. Task filters combine with AND, and the summary
always reflects the full list independently of filters and pagination.

## Development and migrations

Load `.env` when running host commands that need a database URL:

```sh
set -a
. ./.env
set +a
uv run --frozen alembic upgrade head
uv run --frozen uvicorn task_manager.infrastructure.http.api:create_app --factory
```

Schema changes are ordered Alembic revisions under `migrations/versions/`. Do not use
`Base.metadata.create_all()` as a runtime shortcut. The task foreign key references
`task_lists.id` and cascades when a parent list is deleted.

## Verification

Start the isolated test database and run the full suite:

```sh
docker compose --profile test up -d --wait db-test
set -a
. ./.env
set +a
uv run --frozen flake8 src tests migrations
uv run --frozen black --check src tests migrations
uv run --frozen mypy --strict src tests migrations
uv run --frozen pytest
```

The full pytest run enforces at least 75% statement coverage across `src/task_manager`.
Integration fixtures create a fresh PostgreSQL schema per test and apply the migrations;
they drop only their own schema afterward. Run one test level without the full-suite
coverage gate with `uv run --frozen pytest -m unit --no-cov` (replace `unit` with
`integration` or `e2e` as needed). Run lock, typing, lint, format, PostgreSQL tests,
coverage, and Docker build checks locally before delivery.

For the container smoke and restart workflow, see
[specs/001-manage-task-lists/quickstart.md](specs/001-manage-task-lists/quickstart.md).
Known limitations and architectural tradeoffs are in [DECISION_LOG.md](DECISION_LOG.md).
