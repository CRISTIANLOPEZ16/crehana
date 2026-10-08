# Data Model: Secure Task Collaboration

**Source**: [approved specification](spec.md) and [planning research](research.md).
**Status**: Planning design, 2026-10-08; no database changes performed.

The existing task/list UUIDs, text, status, priority and timestamps survive upgrade. All
identities are UUID; all persisted times are `timestamp with time zone` in UTC and serialize
as RFC 3339. Existing creation/update timestamp behavior, trimmed Unicode text rules,
list-to-task cascade, ordering and completion calculations remain.

## Relationships

```text
User 1 ─owns─ * TaskList 1 ─contains─ * Task
  │                     │                    │
  └─joins through─ ListMembership            └─optional assignee─ User
                        │
TaskList 1 ─contains─ * Invitation ─invited by─ User
```

A list's owner is the sole `owner_id`, never a membership row. Owner/member eligibility is
calculated from `task_lists.owner_id` or a row in `list_memberships`, not a stored role.

## User (`users`)

| Column | Storage / constraint | Behavior |
| --- | --- | --- |
| id | UUID primary key, nonnull | Server UUID, immutable |
| display_name | text nonnull, char_length1–100, trimmed | Unicode code points after trim; no account update endpoint |
| email | text nonnull, unique, canonical ASCII, <=254 chars | Trim before validation, IDNA domain, whole lowercase; ASCII local part <=64, domain <=253; dots/plus preserved |
| password_hash | text nonnull/nonblank | Argon2id encoded hash only, never response/log/JWT |
| created_at, updated_at | timestamptz nonnull; updated_at>=created_at | Equal at registration; account updates excluded |

Use a unique database constraint on canonical email for concurrent registration. Application
normalization implements the exact email policy; a database check can assert stored lowercase,
ASCII and length but cannot replace the validator. No `email_normalized` duplicate column.
Foreign keys from owner, membership, assignee and invitation provenance prevent deleting a
referenced account; account deletion is outside this feature.

## TaskList (`task_lists`)

Keep id, name, nullable description, created_at, updated_at and their current constraints.
Add `owner_id` UUID: nullable only in transitional revision 0004; required and foreign-keyed
to `users.id` in final revision 0005. New list creation sets owner_id to authenticated
creator. PATCH/create schemas forbid client owner_id. No `created_by_id`, role or ownership
transfer. List deletion cascades tasks, memberships and invitations in one transaction.
Task/invitation/member activity does not change list updated_at. Add an owner/created_at/ID
index only if needed for caller-visible ordering; inspect query plan during implementation.

## ListMembership (`list_memberships`)

| Column | Storage / constraint | Behavior |
| --- | --- | --- |
| list_id | UUID FK to task_lists.id ON DELETE CASCADE | Parent scope |
| user_id | UUID FK to users.id, delete restricted | Joined account |
| created_at | timestamptz nonnull | Set on committed invitation acceptance |

Composite primary/unique `(list_id,user_id)` prevents duplicate membership. Index
`(user_id,list_id)` supports visible-list lookup. Use-case admission checks prevent adding
the owner as a member. Owner-only removal deletes the membership and clears assignments in
that list atomically. Removing an absent member gives404; trying to remove owner gives409.

## Task (`tasks`)

Keep existing id, immutable list_id, title, nullable description, status, priority,
created_at and updated_at. Add `assignee_id` nullable UUID FK to users.id, defaultnull.
Creation and PATCH may assign the owner or a member; null clears, omission preserves,
identical assignment is a no-op. Assignment changes task updated_at once, never status,
priority, parent updated_at or completion. `ON DELETE CASCADE` from parent list remains;
no task move. Existing `(list_id,created_at,id)` ordering index remains.

The FK prevents a nonexistent account reference. The cross-table owner/member eligibility
rule is enforced by locked use cases, the user-approved Q2 design, rather than a duplicate
trigger. Every assignment and member removal rechecks after acquiring the list row lock;
removal clears affected tasks before commit. Direct privileged SQL bypass of application
use cases is outside this enforcement boundary and must not be described as protected.

## Invitation (`invitations`)

| Column | Storage / constraint | Behavior |
| --- | --- | --- |
| id | UUID primary key | Server-generated immutable identity |
| list_id | UUID FK task_lists.id ON DELETE CASCADE | Invitation's one list |
| invited_by_id | UUID FK users.id, delete restricted | Original owner/creator, immutable |
| recipient_email | canonical text nonnull | Same validator/comparison as User.email, immutable |
| token_hash | fixed 32-byte verifier, unique | SHA-256 of >=256-bit random token; raw token never stored |
| status | text check pending/accepted/revoked/expired | Persisted lifecycle; effective expiry is computed on read |
| created_at, expires_at | timestamptz nonnull | First issue time immutable; expires_at changes on resend |
| accepted_at, revoked_at | nullable timestamptz | One terminal timestamp set once; both cannot be populated |
| simulation_subject | text nonnull | Latest invitation subject/context, including send-time list name |
| simulation_status | text check simulated | No real delivery state claimed |
| simulated_at | timestamptz nonnull | Latest simulated issue/resend timestamp |

Keep recipient, list ID, invitation ID and inviter identity on the invitation; no separate
notification table. An owner receives raw acceptance token once in create/resend response;
inspection returns only stored metadata. Include checks for timestamp order and lifecycle
timestamp consistency. A unique partial index on `(list_id,recipient_email)` for rows with
persisted status='pending' prevents concurrent active duplicates. On create/resend, under
the list lock, materialize expired pending rows first; expiry is still reflected on reads
without background writes. A unique token_hash index protects verifier uniqueness.

State changes:

| State | Accept | Revoke | Resend | Effective expiry |
| --- | --- | --- | --- | --- |
| Pending, before deadline | Accepted + accepted_at + membership | Revoked + revoked_at | Pending; rotate verifier, expiry and simulation | Pending |
| Pending, at/after deadline | 409 | 409 | Pending; rotate verifier, expiry and simulation | Expired |
| Accepted | 200 retry only while membership exists, otherwise409 | 409 | 409 | Remains accepted |
| Revoked | 409 | 200 idempotent, timestamp unchanged | 409 | Remains revoked |
| Expired | 409 | 409 | Pending; rotate verifier, expiry and simulation | Expired until resend |

Invalid token/wrong recipient/deleted list returns404. An already-existing membership may be
reused during first valid acceptance; no second row is inserted. Removing a member never
lets an accepted token recreate membership. New invitation after removal is required.
Resend invalidates previous token immediately after commit; historical invitation ID and
created_at remain, latest simulation changes. An expired old invitation may coexist with a
new pending one. Lock list before invitation/member rows for every lifecycle mutation.

## Migration stages and recovery

- 0004 additive revision: create new tables/indexes/checks and nullable owner/assignee
  columns. Existing rows stay intact and historical tasks have null assignee. Existing
  revisions 0001–0003 remain unchanged.
- Offline owner setup command: operator enters account email/display name and password on a
  TTY if creating a new account, or selects an existing canonical account. The command uses
  the same validation/hashing rules, never resets an existing password, and sets owner_id
  only for null historical rows in one transaction. Repeating it with a conflicting owner
  must stop rather than reassign prior rows. No password in argv, environment or logs.
- 0005 final revision: verify zero null owner_id and valid referenced accounts; enforce
  owner NOT NULL and foreign key. It creates no implicit user and does not reassign data.
  Fresh databases, having no historical lists, upgrade head without owner setup.
- Compose API remains stopped until head succeeds. On a populated migration failure,
  0004 stays committed; run the explicit owner setup command and retry `upgrade head`.
  A failure in the offline transaction or 0005 leaves existing resources intact; do not
  reset volumes or replay 0001–0003. Tests cover both fresh and populated paths in
  isolated schemas, including retry and timestamp preservation.
