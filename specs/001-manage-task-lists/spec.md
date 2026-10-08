# Feature Specification: Manage Task Lists and Tasks

**Feature Branch**: `dev`

**Feature Directory**: `specs/001-manage-task-lists`

**Created**: 2026-10-07

**Status**: Ready for planning — structured design review completed

**Input**: User-provided task-list/task scope, UC-01–UC-11, API contract, concurrency,
pagination, completion, delivery priorities, and acceptance requirements.

## Scope and Requirement Sources *(mandatory)*

Users organize work into named lists, manage tasks within each list, and inspect progress
without filters or pagination distorting the overall completion percentage.

The explicit user requirements in this specification refine the challenge referenced at
`docs/prueba.pdf`. [Constitution v4.0.0](../../.specify/memory/constitution.md) governs
architecture, typing, testing, coverage, configuration, and delivery. Explicit user
requirements take precedence over generic template guidance, including the requirement
to document API contracts and examples here.

Required scope: task-list CRUD; task CRUD within immutable parent lists; all supported
status transitions; status/priority filtering; limit/offset pagination for both collections;
and consistent, calculated list completion summaries.

Authentication, authorization roles, task assignment, invitations, UI, search, task moves,
soft deletion, audit history, bulk operations, cursor pagination, and version-based conflict
detection are excluded from this MVP. No optional bonus is a prerequisite for core behavior.
The API is evaluated as a single shared workspace without user accounts. No production
multi-tenant access model or unmeasured performance target is implied.

## Structured Design Review *(mandatory)*

The constitution requires the `grilling` skill ("grill me") for every specification and plan.
The supplied decisions and the user-confirmed review outcomes are recorded below.
Implementation design is reserved for the plan.

| Decision | Selected behavior from user input | Alternative/tradeoff |
|----------|-----------------------------------|----------------------|
| Resource ownership | Task parent is immutable; resolve by both IDs | Moving tasks is excluded; membership mistakes return 404 |
| Deletion | Permanent, atomic list/task cascade | No recovery or soft-delete lifecycle |
| Completion | Derived over the full parent list in one consistent snapshot | More demanding than independent reads, but no contradictory counts |
| Pagination | Limit/offset; creation time then ID ascending | Simple navigation; separate requests are not a frozen collection |
| Concurrent writes | Last-write-wins for supplied overlapping fields | No version conflicts; omitted fields must survive unrelated edits |
| Status | All transitions allowed through task PATCH | No approval workflow or separate status endpoint |
| Delivery | Four dependent increments | First working slice is not the complete MVP |

**Review completed 2026-10-07**: The user confirmed all three recommended rules.

| Review decision | Confirmed rule | Rationale and rejected alternative |
|-----------------|----------------|------------------------------------|
| Q1 — Concurrent no-op PATCH | All explicitly supplied fields participate in last-write-wins; compare values at the serialized write point to detect no-ops | Discarding fields equal to an earlier read can silently lose explicit client intent; omitted fields still remain untouched |
| Q2 — Strict inputs | Reject unknown/system-managed creation fields and unknown/repeated query parameters with 422, even repeated identical values | Catches client mistakes rather than ignoring unknown inputs or arbitrarily selecting a repeated value |
| Q3 — Text and rounding | Count Unicode code points after trimming Unicode whitespace; preserve internal whitespace; use case-sensitive enums and half-up percentage rounding | Gives deterministic validation/calculation; half-even rounding and implicit case normalization are not used |

No unresolved specification decisions remain. The user answers confirm shared understanding
of these choices; remaining architecture decisions belong to the plan and its own structured
review. Record consequential architectural decisions and rationale in `DECISION_LOG.md`.

## Verification Requirements *(mandatory)*

The implementation must meet Constitution v4.0.0 without restating it here. Map domain
normalization, invariants, transitions, and use cases to unit tests; persisted constraints,
rollback, snapshots, and concurrent writes to PostgreSQL integration tests; and each
critical user workflow to tests through a running API backed by PostgreSQL. Use isolated,
deterministic data and meaningful assertions. At least 75% statement coverage must include
all application source, including modules not imported by tests.

The plan and final review must verify inward dependencies, OO responsibilities and injected
persistence interfaces, explicit typing and descriptive names, uv/frozen installation,
Flake8, Black, strict mypy, all three test levels, Docker build/non-root execution,
persistent Compose storage, and reproducible README/decision-log documentation. Tests
accompany behavior changes; test-first sequencing is optional. These are future delivery
gates, not claims that the starter implementation currently passes them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and retrieve a durable list (Priority: P1)

As a user, I can create a named list and retrieve its saved attributes after a restart.

**Why this priority**: Establishes the first useful, persisted workflow.

**Independent Test**: Create a list, follow its Location, restart with retained database
storage, and retrieve the same identity and attributes.

**Dependencies**: Minimal containerized application/health smoke check and real persistence.
This increment covers UC-01 and UC-02, not the complete MVP.

**Acceptance Scenarios**:

- **AS-01**: Given valid padded name/description, when I create a list, then 201 returns
  trimmed values, a generated UUID, equal UTC timestamps, and a Location resolving to it.
- **AS-02**: Given a valid name, when description is omitted, null, empty, or whitespace-only,
  then creation succeeds with description null; duplicate names also succeed.
- **AS-03**: Given name lengths 1 and 100 after trimming, when created, then each succeeds;
  missing, null, blank, or 101-character names return 422 without creating a list.
- **AS-04**: Given descriptions of 1,000 and 1,001 characters after trimming, when created,
  then the former succeeds and the latter returns 422 without creating a list.
- **AS-05**: Given a saved list, when retrieved, then 200 returns all its attributes and no
  embedded tasks. A malformed ID returns 422; a valid nonexistent UUID returns 404.
- **AS-06**: Given successfully committed resources, when application/container processes
  restart with database storage retained, then their attributes and identities remain.

### User Story 2 - Maintain the list collection (Priority: P2)

As a user, I can browse, rename, describe, and permanently delete lists.

**Why this priority**: Completes list management before introducing task workflows.

**Independent Test**: Seed lists, browse and patch them, then delete one and verify absence.

**Dependencies**: P1 persistence/resource contracts. Covers UC-03–UC-05. Implement the
paginated list envelope here; P4 verifies shared pagination behavior across both collections.
Cascade-with-tasks scenarios require P3 task persistence and are final MVP acceptance gates.

**Acceptance Scenarios**:

- **AS-07**: Given no lists, when browsing, then 200 returns items=[], total=0, limit=20,
  offset=0. Given lists, total counts every list before pagination.
- **AS-08**: Given a list, when only its name changes, then omitted description is preserved
  and updated_at changes; when description=null is supplied, it is cleared.
- **AS-09**: Given a list, when PATCH is empty or includes an unknown/immutable field or
  name=null, then 422 leaves all persisted attributes unchanged. Invalid structure returns
  422 even if the syntactically valid list UUID does not exist.
- **AS-10**: Given a list, when normalized supplied values equal persisted values, then PATCH
  succeeds and updated_at remains exactly equal. Created_at and identity never change.
- **AS-11**: Given a list with tasks, when deleted, then 204 has no body and neither the list
  nor any child remains; subsequent valid retrieval/deletion returns 404. Given an injected
  failure before commit, then deletion returns a generic 500 and all original data remains.
- **AS-12**: Given an existing list, when name/description updates exercise AS-03/AS-04 length
  limits, blank and null rules, then the same validation applies atomically; whitespace-only
  description clears it. A valid PATCH of a missing list returns 404.

### User Story 3 - Manage tasks and progress states (Priority: P3)

As a user, I can create, read, edit, complete, reopen, and delete tasks in their original list.

**Why this priority**: Provides the task lifecycle on which filtering and completion depend.

**Independent Test**: Seed two lists, run task CRUD/status workflows under the correct parent,
and demonstrate that the wrong parent cannot retrieve, update, or delete the task.

**Dependencies**: P1 list existence and P2 list lifecycle/error contracts. Covers UC-06–UC-10.

**Acceptance Scenarios**:

- **AS-13**: Given an existing list, when a valid title-only task is created, then 201 returns
  description=null, status=pending, priority=medium, generated UUID, path-derived list_id,
  equal timestamps, and a Location resolving to the task. Duplicate titles are allowed.
- **AS-14**: Given task titles of 1 and 200 characters and descriptions of 2,000 characters
  after trimming, when created or patched, then they succeed. Missing create title, null or
  blank title, 201-character title, and 2,001-character description return 422 with no writes.
  Padded text is trimmed; empty/whitespace/null descriptions are stored as null.
- **AS-15**: Given each supported status and priority, when supplied on creation or PATCH,
  then it is accepted. Unsupported tokens or explicit null return 422; omitted creation
  enums use defaults and omitted PATCH enums preserve current values.
- **AS-16**: Given a task belonging to list A and existing list B, when GET, PATCH, or DELETE
  targets it through B, then 404 is returned and the task remains unchanged. Missing parent
  or task also returns 404; malformed parent/task UUIDs return 422.
- **AS-17**: Given a nonexistent parent, when a valid task is created, then 404 and no task
  result. Given any attempted orphan write, persisted integrity prevents an orphan task.
- **AS-18**: Given a task, when PATCH changes title and clears description, then both changes
  commit together, omitted fields remain, and only the task's updated_at changes. Empty,
  unknown-field, immutable-field (including list_id), or mixed valid/invalid updates return
  422 without partial changes. Task creation/update/deletion never changes parent updated_at.
- **AS-19**: Given each of pending, in_progress, and completed, when status-only PATCH chooses
  each of those three states, then all nine combinations succeed. The six actual transitions
  change updated_at; the three self-transitions preserve it. Pending can directly complete,
  and completed can reopen to pending or in_progress. Reads after commit see the new state.
- **AS-20**: Given a task, when all normalized PATCH values equal persisted values, then
  200 returns unchanged updated_at. Given any rejected update or pre-commit failure, then
  all old attributes/timestamps remain; no write-success response precedes commit.
- **AS-21**: Given an existing task, when deleted through its parent, then 204 has no body,
  the parent remains, and subsequent retrieval/deletion of the task returns 404.
- **AS-22**: Given two concurrent requests editing title and priority respectively, when both
  succeed in either order, then both supplied edits survive. Given overlapping field edits,
  then the last serialized successful write wins for those fields without overwriting omitted
  fields. Concurrent list name/description edits follow the same rule.

### User Story 4 - Browse tasks and trust completion summaries (Priority: P4)

As a user, I can narrow and page tasks while always seeing accurate whole-list completion.

**Why this priority**: Adds navigation and trustworthy progress after the underlying lifecycle.

**Independent Test**: Seed known statuses/priorities, filter and page results, and compare
items, matching counts, and whole-list summary against the committed fixture.

**Dependencies**: P3 task lifecycle; P2 pagination contract. Covers UC-11 and final shared
pagination/summary validation. All four stories and delivery gates constitute the MVP.

**Acceptance Scenarios**:

- **AS-23**: Given two completed/high tasks, one pending/high, and one in_progress/low, when
  filtering pending AND high, then exactly the pending/high task matches, matched_tasks=1,
  total_tasks=4, completed_tasks=2, and completion_percentage=50.
- **AS-24**: Given that fixture, when filtering only completed, then two tasks match; when
  filtering only high, three match; when filtering completed AND low, none match. Every
  response retains the same whole-list summary. With no filters all four tasks match.
- **AS-25**: Given an existing empty list, when querying tasks, then 200 returns empty items,
  matched_tasks=0, total_tasks=0, completed_tasks=0, completion_percentage=0. A valid missing
  list returns 404; malformed UUID, unsupported filters, or invalid pagination return 422
  before lookup, even for a nonexistent parent.
- **AS-26**: Given either collection, when pagination is omitted, then limit=20/offset=0.
  Limits 1 and 100 and offset 0 succeed; limits 0 or 101, negative offsets, fractional or
  nonnumeric pagination values return 422. Offset beyond results yields empty items while
  total/matched_tasks and completion remain accurate.
- **AS-27**: Given resources with different creation timestamps and deliberate timestamp
  ties, when paging an unchanged dataset, then created_at ascending and UUID ascending
  determine one stable order, with no duplicates or omissions across pages. Filtering
  happens before task pagination; editing updated_at never reorders a resource.
- **AS-28**: Given lists with no completed tasks, all completed tasks, one of three completed,
  and two of three completed, when queried, then percentages are respectively 0, 100, 33.33,
  and 66.67. Every task has equal weight regardless of priority.
- **AS-29**: Given two tasks with one completed (50%), when a pending task is created, then
  the next summary is 33.33%; completing it yields 66.67%; reopening it yields 33.33%;
  deleting the remaining completed task yields 0% over two tasks; deleting both yields
  the empty-list zero summary. Creating a completed task in an empty list yields 100%.
- **AS-30**: Given any populated list, when filters or page size/offset change, then the
  whole-list summary stays equal for an unchanged dataset, including pages with no items.
- **AS-31**: Given concurrent creation, deletion, completion, or reopening during a task
  query, when the response is produced, then items, matched_tasks, total_tasks, and
  completed_tasks correspond to one committed snapshot, never a mixture. With no filters,
  matched_tasks equals total_tasks; completed_tasks never exceeds total_tasks. A subsequent
  query started after a successful write sees that commit unless a later write supersedes it.

### Edge Cases

AS-01–AS-31 cover the required normalization, null/default distinctions, limits, missing
resources, membership, atomicity, transitions, pagination, completion, concurrency, and
restart cases. Additional common contract scenarios:

- **AS-32**: Given any mutating endpoint, when JSON is malformed, non-object, wrong-typed,
  or missing a required creation field, then 422 uses the error envelope and no data changes.
- **AS-33**: Given PATCH requests, when id, created_at, updated_at, or task list_id is supplied
  even with its existing value, then 422 rejects it. Supplied unknown PATCH fields are also
  rejected. Creation also rejects unknown/system-managed fields; query rules are covered by AS-37.
- **AS-34**: Given unexpected internal failure, when any endpoint responds, then 500 uses
  a generic message and exposes no stack traces, SQL, credentials, or internal paths.
  Expected missing-resource failures use the consistent 404 envelope; validation failures
  include field-level details without echoing secrets or raw invalid payloads.
- **AS-35**: Given successful creation, retrieval, update, and deletion, when responses are
  inspected, then status codes, resource fields, Location on 201, UTC RFC 3339 timestamps,
  and bodyless 204 match the API contract. List retrieval never embeds tasks or summaries.

- **AS-36**: Given title=A, request R1 supplies title=A, and R2 supplies title=B, when R2
  is serialized first and R1 second, then final title=A and R1 changes updated_at; when R1
  is serialized first, then R1 is a no-op and final title=B after R2. An unrelated priority
  edit survives in either order. Apply the equivalent test to list name/description.
- **AS-37**: Given any creation request with an unknown or system-managed field (id,
  created_at, updated_at, or task list_id), when submitted, then 422 creates nothing. Given
  either collection query with an unknown parameter or a repeated recognized parameter,
  even identical repeated values, then 422 occurs before lookup. Unsupported list filters
  such as status also return 422.
- **AS-38**: Given Unicode whitespace surrounding a valid text value, when created/patched,
  then surrounding whitespace is removed and internal whitespace preserved. A title of
  200 single-code-point emoji succeeds and 201 fails. A title of 100 repeated decomposed
  e-plus-combining-accent pairs counts as 200 code points and succeeds; 101 pairs fail.
  No Unicode composition normalization changes stored text. Given mixed/uppercase or
  whitespace-padded enum tokens such as Completed or " high ", then 422 is returned.
- **AS-39**: Given 32 tasks with one completed, when queried, then the exact percentage
  3.125 rounds half-up to 3.13. Filters and pagination do not change that result.

## Requirements *(mandatory)*

### Functional Requirements

Every requirement below is mandatory. Shared requirements apply in addition to each use case.

| ID | Use cases | Requirement | Acceptance |
|----|-----------|-------------|------------|
| FR-001 | UC-01 | Normalize/validate name and description; generate identity/timestamps; commit and return the new list | AS-01–04, AS-35 |
| FR-002 | UC-02 | Retrieve list attributes by UUID without embedding tasks; distinguish malformed from missing identity | AS-05 |
| FR-003 | UC-03 | Return items, total, limit, offset for all lists, including an empty successful collection | AS-07, AS-26–27 |
| FR-004 | UC-04 | Partially update only name/description; preserve omitted fields; support clearing description | AS-08–10, AS-12 |
| FR-005 | UC-05 | Permanently delete list and children atomically; missing/already-deleted lists return 404 | AS-11 |
| FR-006 | UC-06 | Create a task under an existing list with declared defaults and no possible persisted orphan | AS-13–15, AS-17 |
| FR-007 | UC-07 | Retrieve a task only using the correct parent and task UUIDs | AS-16 |
| FR-008 | UC-08 | Atomically patch only supplied title/description/status/priority; task parent is immutable | AS-14–15, AS-18, AS-20, AS-33 |
| FR-009 | UC-09 | Status-only task PATCH permits all transitions via task domain behavior; self-transitions are no-ops | AS-19–20 |
| FR-010 | UC-10 | Delete a correctly scoped task permanently, preserving the parent | AS-16, AS-21, AS-29 |
| FR-011 | UC-11 | Query one existing list; combine optional status and priority with AND before pagination | AS-23–25, AS-27 |
| FR-012 | UC-11 | Return matched_tasks before pagination and a whole-list calculated completion summary independent of filters/pages/priority | AS-23–25, AS-28–30 |
| FR-013 | UC-11 | Use one consistent committed snapshot for returned items, counts, and summary | AS-31 |
| FR-014 | UC-03, UC-11 | Apply integer limit 1–100 (default 20), nonnegative offset (default 0), created_at/UUID ascending order, and accurate beyond-end totals | AS-26–27 |
| FR-015 | UC-01,04,06,08 | Trim text before length validation; reject blank names/titles; normalize blank descriptions to null; allow duplicates | AS-01–04, AS-12–14 |
| FR-016 | UC-01,04,06,08,09 | Generate immutable UUID/created_at, initialize timestamps equally, change updated_at only with persisted attribute changes, and preserve parent timestamps on task changes | AS-01, AS-10, AS-13, AS-18–20, AS-33 |
| FR-017 | UC-01–11 | Validate identifiers and request structure before resource lookup; return defined statuses and consistent safe errors | AS-05, AS-09, AS-16, AS-25–26, AS-32–35 |
| FR-018 | UC-01,04–06,08–10 | Return success only after commit; rollback failures preserve integrity and prior data | AS-11, AS-17–20, AS-34 |
| FR-019 | UC-04,08,09 | Concurrent overlapping supplied fields use last-write-wins; omitted unrelated fields are never overwritten | AS-22, AS-36 |
| FR-020 | UC-01–11 | Retain committed data across application/container restart when database storage is retained | AS-06 |
| FR-021 | UC-01–11 | Use the /api/v1 resource paths, methods, response envelopes, and creation Location headers below | AS-35 |
| FR-022 | UC-04,08,09 | Reject empty PATCH, unknown fields, immutable fields, and null in nonnullable fields; unchanged normalized values succeed without timestamp change | AS-09–10, AS-15, AS-18–20, AS-33 |
| FR-023 | UC-01,06 | Reject unknown and system-managed creation fields with 422 | AS-37 |
| FR-024 | UC-03,11 | Reject unknown or repeated query parameters with 422 before lookup | AS-37 |
| FR-025 | UC-01,04,06,08,09,11 | Count Unicode code points after trimming Unicode whitespace; preserve internal text without Unicode normalization; enums are exact case-sensitive tokens | AS-38 |
| FR-026 | UC-11 | Round completion half-up to two decimal places | AS-28, AS-39 |

### Key Entities *(include if feature involves data)*

**TaskList**

| Attribute | Type | Default/source | Mutability and validation |
|-----------|------|----------------|---------------------------|
| id | UUID | System-generated | Immutable; never client-selected |
| name | string | Required | Mutable; 1–100 characters after trimming; not null/blank |
| description | string or null | null | Mutable; at most 1,000 characters after trimming; blank becomes null |
| created_at | UTC timestamp | System-generated | Immutable |
| updated_at | UTC timestamp | Same instant as created_at | System-managed; changes only for changed persisted list attributes |

**Task**

| Attribute | Type | Default/source | Mutability and validation |
|-----------|------|----------------|---------------------------|
| id | UUID | System-generated | Immutable; never client-selected |
| list_id | UUID | Parent resource path | Immutable; must reference an existing TaskList |
| title | string | Required | Mutable; 1–200 characters after trimming; not null/blank |
| description | string or null | null | Mutable; at most 2,000 characters after trimming; blank becomes null |
| status | pending, in_progress, completed | pending | Mutable; nonnull; all transitions allowed |
| priority | low, medium, high | medium | Mutable; nonnull |
| created_at | UTC timestamp | System-generated | Immutable |
| updated_at | UTC timestamp | Same instant as created_at | System-managed; changes only for changed persisted task attributes |

All timestamps serialize as UTC RFC 3339 (examples use `Z`). No-op updates preserve the
stored timestamp exactly, not merely its rendered precision. Attributes with system-managed
values cannot be client-overridden. PATCH rejects their presence. Task changes do not
modify list updated_at. Lists can have zero or more tasks; every task has exactly one parent.
Names/titles need not be unique. Descriptions are present in responses even when null.

**Collection and completion projections**

List collection: items (TaskList array), total (nonnegative integer), limit, offset.
Task collection: items (Task array), matched_tasks (nonnegative integer), limit, offset,
summary. Summary: total_tasks and completed_tasks (nonnegative integers),
completion_percentage (number between 0 and 100 inclusive).

Completion is `completed_tasks / total_tasks × 100`, rounded to two decimal places; zero
when total_tasks=0. It is calculated from persisted tasks and never stored as a percentage.
Numeric JSON need not contain trailing zeros: 50 and 50.00 represent the same result.
Use half-up rounding for ties (for example, 3.125 becomes 3.13).

### Use-Case Contracts

Common precondition: request identifiers and structure are valid. Validate before lookup;
then resolve scoped resources, apply domain rules, and execute the operation. Expected
validation failures return 422, missing or mismatched resources return 404, and unexpected
failures return a generic 500. All write operations commit before success, and failures
before commit must roll back. Unmentioned fields are preserved.

| Use case | Additional preconditions | Processing | Success postcondition | Failure outcomes |
|----------|--------------------------|------------|-----------------------|------------------|
| UC-01 Create list | Valid name; optional description | Normalize; validate; generate UUID/equal timestamps; persist; commit | 201 resource and Location; one list added | 422 creates nothing; 500 rollback |
| UC-02 Retrieve list | List exists | Resolve by UUID; return attributes only | 200 list without tasks | 404 missing; 422 malformed UUID; 500 safe error |
| UC-03 List lists | Valid pagination | Order all lists; count before pagination; select page | 200 items/total/limit/offset, including empty pages | 422 invalid pagination; 500 safe error |
| UC-04 Update list | List exists; nonempty valid patch | Normalize supplied name/description; validate all changes; compare persisted values; update supplied fields/timestamp if changed; commit | 200 updated resource; no-op preserves timestamp | 422 invalid/unknown/immutable/null fields; 404 missing; 500 rollback |
| UC-05 Delete list | List exists | Resolve; delete list and all children in one transaction; commit | 204; list and children absent | 404 missing/already deleted; 500 leaves all data intact |
| UC-06 Create task | Parent exists; valid title and optional fields | Validate; resolve parent; apply defaults/normalization; generate UUID/equal timestamps; persist with parent integrity; commit | 201 task and nested Location | 404 missing parent; 422 invalid input; 500 rollback; no orphans |
| UC-07 Retrieve task | Correct parent and task exist | Resolve using both UUIDs; return task attributes | 200 task | 404 absent/wrong parent; 422 malformed UUID; 500 safe error |
| UC-08 Update task | Correct parent/task exist; nonempty valid patch | Normalize; validate entire patch; resolve scope; change supplied fields and timestamp only when changed; commit | 200 task; parent/timestamps immutable; omitted fields survive | 422 invalid/null/unknown/immutable fields; 404 absent/wrong parent; 500 rollback |
| UC-09 Change status | Correct parent/task exist; supported nonnull status | Validate IDs/status; resolve in parent; invoke task status behavior; if changed update status/timestamp atomically; commit | 200 task; all transitions legal; self-transition no-op; subsequent summary reflects commit | 422 invalid; 404 absent/wrong parent; 500 rollback |
| UC-10 Delete task | Correct parent/task exist | Resolve scope; delete task; commit | 204; parent remains; subsequent summary excludes task | 404 missing/wrong parent/already deleted; 500 rollback |
| UC-11 Query tasks/completion | Parent exists; valid filters and pagination | Resolve parent; filter with AND; count matches; order/page items; calculate unfiltered counts/percentage from the same snapshot | 200 task collection and accurate whole-list summary, even when empty | 404 missing parent; 422 invalid ID/filter/page; 500 safe error |

### API Contract and Examples

All paths below are prefixed with `/api/v1`. JSON request bodies are objects; text fields
accept strings, not implicit numeric/boolean conversions. Nullable descriptions accept null.
Creation accepts only documented user fields; reject unknown and system-managed fields with 422.
Queries accept only documented parameters, each at most once; unknown or repeated parameters
return 422, even when repeated values agree. Enum values are exact, case-sensitive tokens.
A PATCH must contain at least one allowed field; omitted fields differ from explicit null.
Status changes use the existing task PATCH operation, without a dedicated status route.

| Path | Method | Request | Success |
|------|--------|---------|---------|
| /task-lists | POST | name; optional description | 201 TaskList + Location |
| /task-lists | GET | limit, offset | 200 list collection |
| /task-lists/{list_id} | GET | UUID path | 200 TaskList |
| /task-lists/{list_id} | PATCH | supplied name and/or description | 200 TaskList |
| /task-lists/{list_id} | DELETE | UUID path | 204, no body |
| /task-lists/{list_id}/tasks | POST | title; optional description, status, priority | 201 Task |
| /task-lists/{list_id}/tasks | GET | status, priority, limit, offset | 200 task collection |
| /task-lists/{list_id}/tasks/{task_id} | GET | UUID paths | 200 Task |
| /task-lists/{list_id}/tasks/{task_id} | PATCH | supplied title, description, status, priority | 200 Task |
| /task-lists/{list_id}/tasks/{task_id} | DELETE | UUID paths | 204, no body |

The task POST also returns Location. Invalid identifiers, JSON structure, field values,
filters, and pagination return 422 before lookup. Nonexistent/mismatched resources return
404. Unexpected failures return 500 with the generic message shown below. Error codes are
stable; examples define `validation_error`, `resource_not_found`, and `internal_error`.

**Create/retrieve a list**

```http
POST /api/v1/task-lists
Content-Type: application/json

{"name":"  Release work  ","description":"  Launch checklist  "}
```

```http
HTTP/1.1 201 Created
Location: /api/v1/task-lists/11111111-1111-4111-8111-111111111111
Content-Type: application/json

{"id":"11111111-1111-4111-8111-111111111111","name":"Release work","description":"Launch checklist","created_at":"2026-10-07T15:00:00Z","updated_at":"2026-10-07T15:00:00Z"}
```

GET of that Location returns 200 and the same resource. GET `/api/v1/task-lists?limit=1&offset=0`
returns the resource in items with total=1, limit=1, offset=0. An empty collection is:

```json
{"items":[],"total":0,"limit":20,"offset":0}
```

**Patch a list and clear its description**

```http
PATCH /api/v1/task-lists/11111111-1111-4111-8111-111111111111
Content-Type: application/json

{"description":null}
```

```json
{"id":"11111111-1111-4111-8111-111111111111","name":"Release work","description":null,"created_at":"2026-10-07T15:00:00Z","updated_at":"2026-10-07T15:01:00Z"}
```

Status is 200. Repeating this PATCH returns 200 with exactly the same updated_at.

**Create/retrieve a task with defaults**

```http
POST /api/v1/task-lists/11111111-1111-4111-8111-111111111111/tasks
Content-Type: application/json

{"title":"  Write release notes  "}
```

```http
HTTP/1.1 201 Created
Location: /api/v1/task-lists/11111111-1111-4111-8111-111111111111/tasks/22222222-2222-4222-8222-222222222222
Content-Type: application/json

{"id":"22222222-2222-4222-8222-222222222222","list_id":"11111111-1111-4111-8111-111111111111","title":"Write release notes","description":null,"status":"pending","priority":"medium","created_at":"2026-10-07T15:02:00Z","updated_at":"2026-10-07T15:02:00Z"}
```

GET of that Location returns 200 and the same task.

**Complete/reopen a task**

```http
PATCH /api/v1/task-lists/11111111-1111-4111-8111-111111111111/tasks/22222222-2222-4222-8222-222222222222
Content-Type: application/json

{"status":"completed"}
```

```json
{"id":"22222222-2222-4222-8222-222222222222","list_id":"11111111-1111-4111-8111-111111111111","title":"Write release notes","description":null,"status":"completed","priority":"medium","created_at":"2026-10-07T15:02:00Z","updated_at":"2026-10-07T15:03:00Z"}
```

Status is 200. PATCH `{"status":"pending"}` reopens it. PATCH
`{"title":"Publish release notes","description":null,"priority":"high"}` updates those
three fields atomically while preserving status. The response is the full task with updated
values/timestamp. The parent's updated_at remains unchanged for all these task operations.

**Filtered query**

For the four-task fixture in AS-23 (independent of the preceding examples):

```http
GET /api/v1/task-lists/11111111-1111-4111-8111-111111111111/tasks?status=pending&priority=high&limit=20&offset=0
```

```json
{
  "items": [
    {
      "id": "33333333-3333-4333-8333-333333333333",
      "list_id": "11111111-1111-4111-8111-111111111111",
      "title": "Publish announcement",
      "description": null,
      "status": "pending",
      "priority": "high",
      "created_at": "2026-10-07T15:04:00Z",
      "updated_at": "2026-10-07T15:04:00Z"
    }
  ],
  "limit": 20,
  "offset": 0,
  "matched_tasks": 1,
  "summary": {"total_tasks": 4, "completed_tasks": 2, "completion_percentage": 50}
}
```

The same query with offset=1 returns items=[] and retains matched_tasks=1 and that summary.
An existing empty list produces:

```json
{"items":[],"limit":20,"offset":0,"matched_tasks":0,"summary":{"total_tasks":0,"completed_tasks":0,"completion_percentage":0}}
```

**Delete a task or list**

DELETE the relevant resource URI, with no request body. Success is `204 No Content` with
no response body. Repeating the same valid request returns the 404 envelope below.

**Errors**

PATCH `{"title":null}` or a malformed UUID returns 422 with field-level details:

```json
{"code":"validation_error","message":"Request validation failed.","details":[{"field":"body.title","message":"Must be a nonblank string."}]}
```

A malformed path ID uses a field such as `path.list_id`; invalid pagination uses
`query.limit`. Details is always an array of objects with string field/message values.
For non-field errors it is empty. Missing or incorrectly scoped resources return 404:

```json
{"code":"resource_not_found","message":"Resource not found.","details":[]}
```

Unexpected failures return 500:

```json
{"code":"internal_error","message":"An unexpected error occurred.","details":[]}
```

Validation detail wording may vary while the shape, error code, and field location remain
stable. Errors must not disclose stack traces, SQL, credentials, internal paths, or raw
sensitive values. A structurally invalid request with a well-formed but nonexistent UUID
returns 422, not 404.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 11 use cases pass their linked acceptance scenarios; a user can complete
  the create-list → create-task → complete → reopen → delete workflow using returned IDs.
- **SC-002**: Every rejected request and simulated pre-commit write failure in acceptance
  testing leaves the previous data intact; no orphan or partial cascade remains.
- **SC-003**: All nine status combinations behave as specified, and 100% of unchanged-value
  update cases preserve timestamps while actual attribute changes update only that resource.
- **SC-004**: All completion fixtures produce exact expected counts and rounded percentages;
  changing filters/pages never changes the summary for an unchanged list.
- **SC-005**: Paging an unchanged collection visits each matching resource exactly once in
  the specified order; beyond-end pages retain accurate counts.
- **SC-006**: In both controlled write orders, unrelated concurrent edits are preserved and
  overlapping edits follow last-write-wins; controlled concurrent reads never mix snapshots.
- **SC-007**: After restarting application/container processes with retained storage, 100%
  of committed fixture identities and attributes remain retrievable.
- **SC-008**: All defined invalid-input and missing-resource cases produce the specified
  error classification, and no tested failure response contains internal or sensitive data.

## Assumptions

- Single shared workspace, without authentication or ownership boundaries, is sufficient
  for this MVP; optional challenge bonuses are excluded, not silently deferred prerequisites.
- Fields accept their declared JSON types; numeric/boolean-to-text coercion is rejected.
  Explicit null enum values are invalid even during creation; defaults apply only to omission.
- UUIDs are supplied as UUID strings and generated by the system; no particular UUID version
  is a feature requirement. ID ordering is ascending UUID value for deterministic ties.
- UTC RFC 3339 allows fractional seconds; no fixed fractional precision is promised.
- Last-write-wins refers to successful serialized writes, not client send/response order.
  Preserving unrelated fields applies to task and list updates. Explicitly supplied values equal to an earlier read still
  participate in last-write-wins; only the serialized persisted state determines a no-op.
- Offset paging is stable for an unchanged dataset. Separate requests can see new committed
  data; no cross-request frozen snapshot or cursor guarantee is provided. UC-11 requires
  consistency within each response. The plan must select a way to honor that guarantee.
- Completion is numeric, not a formatted percent string; exact rounding ties use half-up rounding.
- Error code tokens, details shape, and root-relative Location values are explicit contract
  defaults chosen here; they do not prescribe internal exception types or persistence tools.
- The reviewed strict-input, Unicode text, enum case, and rounding decisions are normative
  requirements FR-023–FR-026, rather than assumptions left to implementation.
- Acceptance fault/concurrency fixtures use isolated data and controlled interleavings;
  implementation must not expose fault-injection or test-only endpoints to ordinary clients.
- No throughput, latency, user-count, cloud deployment, or database-size target is claimed.
