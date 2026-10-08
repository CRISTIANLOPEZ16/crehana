# Quickstart Validation Guide

**Status**: Commands verified in the current workspace. Run from the repository root.

## Prerequisites and configuration

Install uv and Docker with Compose. Use Python 3.11 through uv. Implementation supplies
`.env.example` documents POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, DATABASE_URL,
TEST_DATABASE_URL, and test database credentials. Copy it to an ignored `.env` and replace
password placeholders with local values; never commit `.env` or bake it into the image.

The Compose development DB exposes localhost:55432, test DB localhost:55433, API localhost:8000.
DATABASE_URL for host commands uses the development port; Compose overrides its app/migration
URL to the internal db:5432 host using the same credentials. TEST_DATABASE_URL points only
to db-test and its separate credentials/database. Fixtures reject development URLs and create
unique test schemas. DATABASE_SCHEMA is optional for development and set safely by fixtures.

```sh
cp .env.example .env
```

Edit `.env`, then load its shell-compatible values in a trusted local shell:

```sh
set -a
. ./.env
set +a
uv python install 3.11
uv lock --check
uv sync --frozen
```

An out-of-date/missing lockfile is a failure to resolve during implementation; do not silently
regenerate it during verification. New dependency changes are resolved with uv and their lock diff reviewed.

## Container execution and persistence

```sh
docker compose up --build -d --wait
curl --fail-with-body http://localhost:8000/health
```

Expected: db is healthy, migrate completed successfully, api serves `{"status":"ok"}` as
non-root. The migration service uses the same built image and finishes before api starts.
Application startup itself does not create tables. Docker build installs via
`uv sync --frozen --no-dev`; runtime starts through uv without dependency changes.

Create a list and inspect its 201/Location response:

```sh
curl --fail-with-body -i http://localhost:8000/api/v1/task-lists \
  -H 'Content-Type: application/json' \
  -d '{"name":"  Release work  ","description":"  Launch checklist  "}'
```

Store the returned UUID in a shell variable (replace the sample below with that response):

```sh
TASK_LIST_ID=11111111-1111-4111-8111-111111111111
curl --fail-with-body "http://localhost:8000/api/v1/task-lists/$TASK_LIST_ID"
docker compose restart api
curl --fail-with-body "http://localhost:8000/api/v1/task-lists/$TASK_LIST_ID"
```

Wait for /health after restart before the final GET if necessary. Expected: same ID, trimmed
attributes, and timestamps. Also restart db and api with the named volume retained, wait for
health, and repeat retrieval. Do not remove development volumes during verification.

## Host development (alternative to container API)

Stop the container API before binding the same port. The host DATABASE_URL uses localhost.

```sh
docker compose stop api
docker compose up -d --wait db
uv run --frozen alembic upgrade head
uv run --frozen uvicorn task_manager.infrastructure.http.api:create_app --factory --host 127.0.0.1 --port 8000
```

## Workflow checks

Using the created list:

```sh
curl --fail-with-body -i "http://localhost:8000/api/v1/task-lists/$TASK_LIST_ID/tasks" \
  -H 'Content-Type: application/json' -d '{"title":"Write release notes"}'
```

Expected: 201, nested Location, pending/medium defaults, null description, equal timestamps.
Set TASK_ID to the returned ID. Complete and reopen the task:

```sh
TASK_ID=22222222-2222-4222-8222-222222222222
curl --fail-with-body -X PATCH \
  "http://localhost:8000/api/v1/task-lists/$TASK_LIST_ID/tasks/$TASK_ID" \
  -H 'Content-Type: application/json' -d '{"status":"completed"}'
curl --fail-with-body "http://localhost:8000/api/v1/task-lists/$TASK_LIST_ID/tasks?limit=1&offset=0"
curl --fail-with-body -X PATCH \
  "http://localhost:8000/api/v1/task-lists/$TASK_LIST_ID/tasks/$TASK_ID" \
  -H 'Content-Type: application/json' -d '{"status":"pending","description":null}'
```

For a list containing only that task: completion changes 0 → 100 → 0; parent updated_at
stays unchanged. Repeating the final PATCH preserves the task's updated_at. Invalid text,
unknown fields, duplicate query keys, and incorrect membership must follow the contract.
The complete four-task fixture and exact error examples are in [spec.md](spec.md).

## Automated verification and isolation

Start only the dedicated test database for tests. Fixtures create a unique schema per test,
apply Alembic revisions there, and clean up only that schema. E2E starts its own API process
on a loopback port and passes its isolated schema/URL; it does not target the manually
started development API. Tests terminate their own server gracefully and wait for coverage.

```sh
docker compose --profile test up -d --wait db-test
uv run --frozen pytest
```

Expected: unit, integration, and e2e suites pass; aggregate statement coverage >=75% over
all src/task_manager modules, including unimported modules and the real API subprocess. Test data
must not appear in the development database. Include controlled lock/snapshot interleavings,
all nine transitions, cascade rollback, Unicode limits, and the 1/32 → 3.13% rounding tie.

Each test level is independently runnable; the coverage gate applies to the complete suite:

```sh
uv run --frozen pytest -m unit --no-cov
uv run --frozen pytest -m integration --no-cov
uv run --frozen pytest -m e2e --no-cov
```

Partial invocations do not satisfy delivery. All tests use pytest.ini for pytest settings;
coverage settings in pyproject.toml include source discovery and subprocess instrumentation.

## Full merge gates

```sh
uv lock --check
uv sync --frozen
uv run --frozen flake8 src tests migrations
uv run --frozen black --check src tests migrations
uv run --frozen mypy --strict src tests migrations
uv run --frozen pytest
docker build -t task-manager:local .
docker compose up --build -d --wait
```

Expected: every command succeeds, documented health/restart workflow succeeds, and review
finds all 39 acceptance scenarios covered. Use the dedicated local PostgreSQL test database and provide its credentials through
environment variables when executing these checks. Review generated migrations manually;
strict typing includes migration functions, with any necessary library exception narrowly
documented rather than globally ignored.

Record measured outcomes and known limits in README.md and DECISION_LOG.md after implementation.
See [data-model.md](data-model.md) for constraints and [contracts](contracts/README.md) for the
API. No destructive reset of development data is a validation prerequisite.
