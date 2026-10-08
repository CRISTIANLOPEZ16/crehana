# Data Model: Manage Task Lists and Tasks

**Source**: [spec.md](spec.md), FR-001–FR-026.
**Design**: Plain domain objects; separate typed SQLAlchemy infrastructure records.

## TaskList / task_lists

| Attribute | Domain type | PostgreSQL | Rules |
|-----------|-------------|------------|-------|
| id | UUID | uuid PRIMARY KEY | Generated uuid4; immutable; no caller override |
| name | str | text NOT NULL | Unicode trim, 1–100 code points, duplicates allowed |
| description | str or None | text NULL | Default null; Unicode trim; blank becomes null; <=1,000 code points |
| created_at | datetime (aware UTC) | timestamptz NOT NULL | Generated once; immutable |
| updated_at | datetime (aware UTC) | timestamptz NOT NULL | Initially created_at; only actual list attribute changes advance it |

## Task / tasks

| Attribute | Domain type | PostgreSQL | Rules |
|-----------|-------------|------------|-------|
| id | UUID | uuid PRIMARY KEY | Generated uuid4; immutable |
| list_id | UUID | uuid NOT NULL REFERENCES task_lists(id) ON DELETE CASCADE | Existing parent; immutable |
| title | str | text NOT NULL | Unicode trim; 1–200 code points; duplicates allowed |
| description | str or None | text NULL | Default null; Unicode trim; blank becomes null; <=2,000 code points |
| status | TaskStatus string enum | text NOT NULL DEFAULT 'pending' | CHECK in ('pending','in_progress','completed') |
| priority | TaskPriority string enum | text NOT NULL DEFAULT 'medium' | CHECK in ('low','medium','high') |
| created_at | datetime (aware UTC) | timestamptz NOT NULL | Generated once; immutable |
| updated_at | datetime (aware UTC) | timestamptz NOT NULL | Initially created_at; only actual task attribute changes advance it |

Use string enums with exact wire values; Python Domain has no Pydantic, FastAPI, SQLAlchemy,
or database imports. TaskList.create/update and Task.create/update/change_status own business
behavior. Validate all proposed attribute values before mutating an existing object.
A task never modifies its parent's updated_at. No stored percentage, completion flag,
version counter, uniqueness constraint on user text, or task-move behavior is added.

## Normalization and integrity

Apply Python Unicode whitespace stripping before counting characters. Count code points,
not encoded bytes or grapheme clusters; preserve internal whitespace and Unicode composition.
Descriptions normalize to None when empty after trimming. Name/title cannot be null/blank.
The HTTP schema validates these rules before lookup, and Domain independently enforces them.

Database checks protect nonnull values, normalized length bounds, enum membership, FK integrity,
and updated_at >= created_at. Use char_length for bounds; nullable descriptions must be null
or have length 1..maximum. To make stored trimming/blank checks agree with Python's Unicode
whitespace semantics, migrations can use a fixed explicit trim-character set (generated and
reviewed from Python 3.11 str.isspace) with btrim; plain btrim(text) removes only spaces and
must not be assumed equivalent. Keep the canonical set documented and tested against Domain.
Reject rows whose name/title differs from its trimmed value or is empty; likewise nonnull
descriptions must be nonempty and already trimmed. These checks complement application rules.

Application-generated UUIDs and timestamps are passed explicitly. The timestamp value is
chosen once per creation; both timestamp columns receive the identical instant. Changed
updates use max(now_utc, previous_updated_at + 1 microsecond), preserving order if the clock
has insufficient resolution or moves backward. No-op updates issue no attribute-changing
UPDATE. Immutable attributes have no application update path; direct DBA mutation is outside
the public contract and does not justify a trigger framework.

## Relationships, indexes, and migrations

TaskList 1 → 0..many Task; Task has exactly one TaskList. Parent deletion cascades in one
transaction and rolls back fully on failure. Individual task deletion preserves the list.

Indexes beyond primary keys:

- task_lists(created_at, id) for deterministic list paging.
- tasks(list_id, created_at, id) for parent-scoped paging, FK parent deletes, and counts.

No extra status/priority indexes until query evidence warrants them. Task filters use AND;
counts and aggregates may scan the parent's tasks. Offset cost grows with skipped rows.

Alembic revisions create named checks/FK/indexes and are reviewed before commit. P1 creates
lists; P3 adds tasks/FK if not already needed. Upgrade runs before API startup; no create_all
fallback. Tests apply the same revisions to unique schemas within the dedicated test database;
version tables and application tables use the configured schema/search_path consistently.

## Transaction lifecycle

| Operation | Isolation and locks | Completion |
|-----------|---------------------|------------|
| Create list | READ COMMITTED transaction | Commit inserted row before returning 201 |
| Patch/delete list | READ COMMITTED; parent FOR UPDATE | Compare/update or cascade; commit before 200/204 |
| Create task | READ COMMITTED; parent FOR KEY SHARE | Insert only under existing parent; commit before 201 |
| Patch/delete task | READ COMMITTED; parent FOR KEY SHARE then scoped task FOR UPDATE | Compare all supplied fields with locked state; commit before 200/204 |
| Get resource | Short read transaction; task resolved with both IDs | Return detached object |
| List/query collections | REPEATABLE READ READ ONLY set before first query | Existence, counts, aggregates, page from same snapshot |

For task writes acquire parent before child everywhere. A missing parent/child after waiting
returns 404. ORM records must not retain stale state from a pre-lock read. No writes occur in
read-only snapshots. Roll back on error and always close the session. Never return a success
and then attempt the commit later in response cleanup.

## State transitions and PATCH presence

All nine transitions among pending/in_progress/completed are valid, including the three
self-transitions. Task.change_status handles them without approval/intermediate state.
Self-transitions preserve updated_at; actual transitions advance it. UpdateTaskUseCase applies
other supplied fields atomically in the same transaction.

A typed Unset sentinel distinguishes omission from explicit null. For name/title/status/
priority: omitted means preserve, null means reject. Description: omitted means preserve,
null/blank means clear. Empty patches, unknown keys, and immutable keys return 422. Retain
supplied values even if equal to a prior read: a concurrent writer may have changed the
field before the lock is acquired. Only comparison with serialized persisted state determines
whether a request is a no-op.

## Read projections

ListPage: items:list[TaskList], total:int, limit:int, offset:int.
TaskPage: items:list[Task], matched_tasks:int, limit:int, offset:int, summary:CompletionSummary.
CompletionSummary: total_tasks:int, completed_tasks:int, completion_percentage:Decimal.

Count all parent tasks and completed tasks in the snapshot; count filtered tasks separately;
order matching tasks by created_at ASC, id ASC before limit/offset. Empty pages do not erase
counts. Percentage = 0 for zero tasks; otherwise Decimal(completed)*100/Decimal(total),
quantized to 0.01 with ROUND_HALF_UP. Set sufficient Decimal precision for the count digits.
Serialize the result as a JSON number, not a Decimal string. No filter, page, or priority
weight enters the summary denominator. The OpenAPI schema and spec examples define the wire
projection independently of these application dataclasses.
