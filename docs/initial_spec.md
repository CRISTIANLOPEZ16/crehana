## Scope

Include task-list CRUD, task CRUD within lists, status changes, task
filtering, pagination, and completion summaries.

## Entities

TaskList:
- id: system-generated UUID; immutable.
- name: required string, 1–100 characters.
- description: nullable string, maximum 1,000 characters; default null.
- created_at: system-generated UTC timestamp; immutable.
- updated_at: system-generated UTC timestamp.

Task:
- id: system-generated UUID; immutable.
- list_id: UUID of an existing parent list; immutable.
- title: required string, 1–200 characters.
- description: nullable string, maximum 2,000 characters; default null.
- status: pending, in_progress, or completed; default pending.
- priority: low, medium, or high; default medium.
- created_at: system-generated UTC timestamp; immutable.
- updated_at: system-generated UTC timestamp.

Text rules:
- Trim surrounding whitespace before validating length.
- Reject blank names and titles.
- Normalize blank descriptions to null.
- Permit duplicate list names and task titles.

Timestamp rules:
- created_at and updated_at are initially equal.
- Change updated_at only when the resource's persisted attributes change.
- Task changes do not modify the parent list's updated_at.
- Serialize timestamps in UTC using RFC 3339.

## Use Cases

### UC-01: Create a task list

Accept name and optional description.
Validate and normalize input, generate identity and timestamps, persist,
and return the created resource.
Invalid requests must not create data.

### UC-02: Retrieve a task list

Resolve a list by its ID and return its attributes.
Return 404 when it does not exist.
Do not embed tasks; expose them through the task collection.

### UC-03: List task lists

Return a paginated collection with items, total, limit, and offset.
An empty collection is a successful response.

### UC-04: Update a task list

Allow partial updates to name and description.
Preserve omitted fields.
Allow description=null to clear it.
Reject name=null, empty updates, unknown fields, and immutable fields.
An unchanged-value update succeeds without changing updated_at.
Apply valid changes atomically.

### UC-05: Delete a task list

Permanently delete the list and all its tasks in one transaction.
A failure must not leave partially deleted data.
Return 404 for a missing or already deleted list.

### UC-06: Create a task

Accept title and optional description, status, and priority.
Validate input and confirm that the parent list exists.
Apply defaults, generate identity and timestamps, and persist.
Return 404 for a missing parent.
Database integrity must prevent orphan tasks.

### UC-07: Retrieve a task

Resolve the task using both task ID and parent-list ID.
Return 404 if either resource is missing or the task belongs to another list.

### UC-08: Update a task

Allow partial updates to title, description, status, and priority.
Preserve omitted fields.
Allow description=null to clear it.
Reject null for title, status, and priority.
Reject empty updates, unknown fields, and immutable fields.
Tasks cannot move between lists.
Validate all changes before applying them atomically.
Unchanged-value updates succeed without changing updated_at.

### UC-09: Change task status

Use the task update operation with a status-only request.
Allow every transition between pending, in_progress, and completed,
including pending directly to completed and reopening completed tasks.

Processing:
1. Validate identifiers and the requested status.
2. Resolve the task within the specified list.
3. Apply the status change through the task's domain behavior.
4. If status is unchanged, succeed without changing updated_at.
5. Otherwise update status and updated_at atomically.
6. Commit before returning the updated task.

Completion summaries must reflect the committed status on subsequent reads.
No approval, intermediate status, or partial completion is required.

### UC-10: Delete a task

Resolve the task within its parent list and permanently delete it.
Keep the parent list.
Return 404 for a missing task or incorrect parent relationship.
Subsequent completion summaries must reflect the deletion.

### UC-11: Query tasks and completion

Return tasks from one existing list.
Support optional status and priority filters, combined using AND.
Apply filters before pagination.

Return:
- items: matching tasks for the requested page.
- limit and offset: effective pagination.
- matched_tasks: matching count before pagination.
- summary.total_tasks: all tasks in the parent list.
- summary.completed_tasks: all completed tasks in that list.
- summary.completion_percentage: list completion.

Completion rules:
- Calculate completed_tasks / total_tasks × 100.
- Return 0 for an empty list.
- Round to two decimal places.
- Every task has equal weight; priority does not affect completion.
- Filters and pagination do not affect the summary.
- Calculate from persisted tasks; do not store the percentage.
- Items, counts, and summary must represent a consistent database snapshot.
- Creation, deletion, completion, and reopening affect subsequent summaries.

Return 404 for a missing list.
An existing empty list or a filter with no matches returns 200 with
empty items and accurate counts.

Example:
A list contains two completed/high tasks, one pending/high task,
and one in_progress/low task.
Filtering pending and high returns one matching task, matched_tasks=1,
total_tasks=4, completed_tasks=2, and completion_percentage=50.

## Pagination

Apply limit/offset pagination to both list and task collections:
- limit: default 20, minimum 1, maximum 100.
- offset: default 0, minimum 0.
- Order by created_at ascending, then ID ascending for deterministic ties.
- An offset beyond the results returns empty items and accurate totals.

## API Contract

Use /api/v1 with these resource paths:
- /task-lists
- /task-lists/{list_id}
- /task-lists/{list_id}/tasks
- /task-lists/{list_id}/tasks/{task_id}

Use POST for creation, GET for retrieval, PATCH for partial updates,
and DELETE for deletion.

Responses:
- 201 with the created resource and Location header for creation.
- 200 for retrieval and updates.
- 204 without a body for deletion.
- 404 for missing resources or incorrect task/list membership.
- 422 for invalid identifiers, inputs, filters, or pagination.
- 500 with a generic public message for unexpected failures.

Use a consistent error object containing:
- code: stable machine-readable identifier.
- message: readable explanation.
- details: field-level validation information where relevant.

Validate request structure before looking up resources.
Do not expose stack traces, SQL, credentials, or internal paths.

## Persistence and Concurrent Updates

- Return write success only after the transaction commits.
- Failed operations must preserve existing data and integrity.
- Persist data across application/container restarts when database storage
  is retained.
- Concurrent updates use last-write-wins for overlapping fields.
- Update only supplied fields so unrelated concurrent edits are preserved.
- Version-based conflict detection is outside the MVP.

## Delivery Priorities

1. Create and retrieve task lists with real persistence.
2. Complete task-list management.
3. Task CRUD and status changes.
4. Filtering, pagination, and completion summaries.

The first increment is a working slice, not the complete MVP.
Identify dependencies between increments.

## Specification Deliverables

Produce:
- Prioritized user stories.
- Entity attributes, types, defaults, mutability, and validation rules.
- Numbered functional requirements linked to use cases.
- Preconditions, processing steps, postconditions, and failure outcomes.
- API request/response examples.
- Given/When/Then acceptance scenarios.
- Measurable success criteria.
- Explicit assumptions and exclusions.

Acceptance scenarios must cover:
- Valid, blank, boundary-length, oversized, and null text.
- Defaults and unsupported enum values.
- Unknown and immutable fields.
- Malformed versus nonexistent identifiers.
- Cross-list task operations.
- Empty and unchanged-value updates.
- Clearing descriptions.
- All status transitions and reopening.
- Atomic cascading deletion.
- Individual and combined filters.
- Pagination boundaries and stable ordering.
- Empty-list, zero, full, and fractional completion.
- Completion independent of filters and pagination.
- Completion changes following task creation, deletion, and status changes.
- Concurrent updates preserving unrelated fields.
- Persistence after restart.

Apply the constitution's architecture, typing, testing, coverage, and
delivery standards without reproducing the entire constitution.

Surface material conflicts with the PDF or constitution.
Do not add features beyond this scope. Create the specification only.