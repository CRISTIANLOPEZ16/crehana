---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Unit, PostgreSQL persistence integration, and running-API/PostgreSQL end-to-end tests are REQUIRED by the constitution, overriding generic optional-test guidance. Enforce >=75% statement coverage across all application source, including unimported modules. Group related test scenarios by behavior; split at responsibility boundaries, not to meet a line count. Tests accompany every behavior change; test-first sequencing is optional.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Monolith**: `src/domain/`, `src/application/`, `src/infrastructure/`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Adapt package paths to plan.md while preserving the layer boundaries.

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit-tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal runnable FastAPI application and Docker setup first, with a health endpoint and container smoke check. Then add only the structure needed by the first use case.

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Python 3.11 with uv and FastAPI/Pydantic/PostgreSQL dependencies in pyproject.toml; generate and commit uv.lock
- [ ] T003 [P] Configure .flake8, Black and strict mypy in pyproject.toml, and pytest.ini with all-source coverage enforcement

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Set up PostgreSQL schema, integrity constraints, and migrations
- [ ] T005 [P] Configure persistent database storage and local Docker Compose startup
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007 Define required application persistence interfaces and wire infrastructure adapters through dependency injection
- [ ] T008 Configure custom business exception HTTP mappings and logs that exclude secrets
- [ ] T009 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (REQUIRED)

> **NOTE: Tests must verify acceptance scenarios and ship with the use case. Test-first sequencing is optional.**

- [ ] T010 [P] [US1] Unit tests for domain behavior and application use cases in tests/unit/test_[name].py
- [ ] T011 [P] [US1] PostgreSQL persistence integration tests in tests/integration/test_[name].py
- [ ] T012 [P] [US1] Critical workflow tests through a running API backed by PostgreSQL in tests/e2e/test_[name].py

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create [Entity1] domain class in src/domain/[entity1].py
- [ ] T014 [P] [US1] Create [Entity2] domain class in src/domain/[entity2].py
- [ ] T015 [US1] Implement [UseCase] class with injected persistence interfaces in src/application/[use_case].py (depends on T013, T014)
- [ ] T016 [US1] Implement persistence adapter classes and Pydantic HTTP schemas/routes in src/infrastructure/[file].py
- [ ] T017 [US1] Add validation and error handling
- [ ] T018 [US1] Add logging for user story 1 operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (REQUIRED)

- [ ] T019 [P] [US2] Unit tests for domain behavior and application use cases in tests/unit/test_[name].py
- [ ] T020 [P] [US2] PostgreSQL persistence integration tests in tests/integration/test_[name].py
- [ ] T021 [P] [US2] Critical workflow tests through a running API backed by PostgreSQL in tests/e2e/test_[name].py

### Implementation for User Story 2

- [ ] T022 [P] [US2] Create [Entity] domain class in src/domain/[entity].py
- [ ] T023 [US2] Implement [UseCase] class with injected persistence interfaces in src/application/[use_case].py
- [ ] T024 [US2] Implement persistence adapter classes and Pydantic HTTP schemas/routes in src/infrastructure/[file].py
- [ ] T025 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (REQUIRED)

- [ ] T026 [P] [US3] Unit tests for domain behavior and application use cases in tests/unit/test_[name].py
- [ ] T027 [P] [US3] PostgreSQL persistence integration tests in tests/integration/test_[name].py
- [ ] T028 [P] [US3] Critical workflow tests through a running API backed by PostgreSQL in tests/e2e/test_[name].py

### Implementation for User Story 3

- [ ] T029 [P] [US3] Create [Entity] domain class in src/domain/[entity].py
- [ ] T030 [US3] Implement [UseCase] class with injected persistence interfaces in src/application/[use_case].py
- [ ] T031 [US3] Implement persistence adapter classes and Pydantic HTTP schemas/routes in src/infrastructure/[file].py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX Verify all test levels cover success, invalid inputs, missing resources, boundaries, and failures with deterministic isolated test data
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation
- [ ] TXXX Verify pytest.ini, .flake8, Black/strict mypy configuration, explicit annotations and descriptive names, and >=75% all-source coverage enforcement
- [ ] TXXX Verify local quality gates using uv with frozen installation: unit/integration/end-to-end tests, coverage, Flake8, Black --check, strict mypy, and Docker build
- [ ] TXXX Verify Docker frozen uv installation, non-root application user, environment configuration, Compose startup/health, and persistent PostgreSQL storage across application restart
- [ ] TXXX Complete README.md and DECISION_LOG.md with uv setup/verification commands, configuration, execution, decisions, tradeoffs, and limitations
- [ ] TXXX Perform final constitution review; report evidence and resolve conflicts before claiming completion
- [ ] TXXX Review production and test modules for cohesive responsibilities; keep related behavior together and split only where comprehension, testing, or independent change benefits

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests MUST cover behavior and pass before the story is marked complete
- Domain classes and application persistence interfaces before use cases
- Use cases before infrastructure adapters and endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (required):
Task: "Unit tests for domain behavior and use cases in tests/unit/test_[name].py"
Task: "PostgreSQL persistence tests in tests/integration/test_[name].py"
Task: "Running-API/PostgreSQL workflow tests in tests/e2e/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] domain class in src/domain/[entity1].py"
Task: "Create [Entity2] domain class in src/domain/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests detect incorrect behavior and pass for the delivered implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
