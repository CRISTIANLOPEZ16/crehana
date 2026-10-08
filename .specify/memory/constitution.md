<!--
Sync Impact Report
Version: 3.0.0 -> 4.0.0 (MAJOR)
Rationale: user removed the mandatory file-length cap in favor of cohesive responsibilities.
Modified principle: III. Object-Oriented Design replaces line-count enforcement with review
  of responsibility boundaries, comprehension, testability, and independent change.
Added sections: none. Removed sections: none.
Removed artifact: tests/unit/test_python_file_lengths.py.
Updated: constitution/plan/spec/tasks templates, AGENTS.md, README.md, DECISION_LOG.md,
  feature plan/spec/tasks and requirements checklist.
Reviewed unchanged: docs/constitution_promp.md, checklist template, quickstart and research.
No constitution hooks or command templates apply. Follow-up TODOs: none.
-->
# Crehana Backend Challenge Constitution

## Core Principles

### I. Technology and Dependency Management

- The project MUST use Python 3.11, FastAPI, Pydantic, and PostgreSQL.
- Dependencies, virtual environments, and project commands MUST be managed through uv.
- `pyproject.toml` MUST define dependencies and tool configuration where supported.
- `uv.lock` MUST be committed. Local verification and Docker MUST use frozen dependency
  installation.
- Docker and Docker Compose MUST provide reproducible execution.

### II. Architecture

- The application MUST be a single deployable monolith organized into Domain,
  Application/UseCases, and Infrastructure layers.
- Dependencies MUST point inward. Domain code MUST remain independent of FastAPI, HTTP,
  ORM implementations, and database libraries.
- Business operations MUST be expressed through explicit application use cases.
- Use cases MUST access persistence through small interfaces defined at the application
  boundary and supplied through dependency injection.
- Infrastructure MUST implement persistence interfaces and handle HTTP routing,
  framework integration, and dependency wiring.
- Abstractions and dependencies MUST address demonstrated needs. Speculative extensibility
  and generic repository frameworks are excluded.

### III. Object-Oriented Design

- Domain entities, application use cases, and infrastructure adapters MUST use
  object-oriented Python.
- Classes MUST represent clear domain concepts or cohesive responsibilities.
- Business behavior MUST reside in responsible domain objects or application use cases,
  rather than HTTP handlers.
- Composition MUST be preferred over inheritance. Inheritance and base classes MUST have
  a concrete behavioral purpose.
- Standalone utilities MUST NOT be wrapped in classes without a meaningful responsibility.
- Modules and classes MUST have clear, cohesive responsibilities. Related production
  behavior and test scenarios MUST stay together. Split at responsibility boundaries
  when a module contains independent responsibilities or becomes difficult to understand,
  test, or change. File length is a review signal, not a mandatory threshold. Code MUST
  NOT be fragmented solely to reduce line count.

### IV. Strict Typing and Descriptive Naming

- Function and method parameters, return values, class attributes, and local variables
  MUST have explicit type annotations wherever Python 3.11 supports them, except `self`
  and `cls`.
- Collection types MUST specify element types. Optional values MUST be explicit.
- Types MUST describe actual values and contracts. `Any`, untyped generic containers,
  and type-check suppressions require a documented justification.
- mypy MUST run in strict mode and pass during local verification.
- Variables, methods, functions, modules, and classes MUST have descriptive names that
  communicate their domain meaning or responsibility.
- Use `snake_case` for variables, functions, and methods; `PascalCase` for classes;
  and `UPPER_SNAKE_CASE` for constants.
- Prefer names such as `task_title: str`, `completion_percentage: float`, and
  `CreateTaskUseCase`. Avoid arbitrary names, unexplained abbreviations, and vague
  names such as `var_1` or `Manager`.

### V. Correctness, Validation, and Error Handling

- External inputs and API responses MUST have explicit Pydantic schemas.
- Domain and application code MUST enforce business invariants independently of HTTP
  validation.
- PostgreSQL constraints MUST protect persisted relationships and integrity.
- Operations requiring multiple related writes MUST be atomic.
- Expected business failures MUST use explicit custom exceptions mapped consistently
  to appropriate HTTP responses.
- Unexpected errors MUST NOT expose stack traces, credentials, or sensitive implementation
  details to clients.
- Secrets MUST remain outside source control, container images, and logs.

### VI. Testing

- pytest MUST provide unit, integration, and end-to-end testing.
- Unit tests MUST verify domain behavior and application use cases.
- Integration tests MUST verify persistence against PostgreSQL.
- End-to-end tests MUST exercise critical workflows through a running API backed by
  PostgreSQL.
- Tests MUST cover successful behavior, invalid inputs, missing resources, and relevant
  boundary and failure cases.
- Tests MUST be deterministic, independently runnable, and isolated from development
  and production data.
- The suite MUST enforce at least 75% statement coverage across all application source,
  including modules not imported during tests.
- Coverage exclusions MUST NOT conceal untested business logic. Meaningful behavioral
  assertions are required; coverage alone does not establish correctness.
- Tests MUST accompany every behavior change. Strict test-first sequencing is optional.
- `pytest.ini` MUST contain the pytest configuration.

### VII. Code Quality and Delivery Gates

- Flake8 MUST enforce linting, Black MUST enforce formatting, and mypy MUST enforce
  strict typing.
- The project MUST include `.flake8` and project-level Black and mypy configuration.
- Before delivery, local verification MUST pass Flake8, Black in check mode, strict mypy,
  unit, integration, and end-to-end tests, the application coverage threshold, and the
  Docker image build.
- Application containers MUST run as a non-root user.
- Runtime configuration MUST be supplied through environment variables.
- Containerized database storage MUST persist across application restarts.
- `README.md` MUST document reproducible setup, configuration, execution, and verification
  commands.
- `DECISION_LOG.md` MUST record consequential architectural decisions, tradeoffs, and
  known limitations.

## Delivery Constraints

- Core scope: CRUD for task lists and their tasks, task status changes, task filtering by
  status or priority, and a completion-percentage field.
- JWT authentication, task assignment, and simulated invitation emails are optional and
  MUST NOT delay required functionality or quality gates. Invitations MUST remain simulated.
- `README.md` MUST explain the project, local setup, configuration, Docker startup, database
  initialization, test/quality commands, and known limitations. `DECISION_LOG.md` MUST record
  consequential choices, rejected alternatives, assumptions, and deferred work.
- Cloud deployment, GraphQL, and a frontend are outside the initial scope. No throughput or
  latency target may be claimed without a corresponding requirement and measurement.

## Development Workflow and Quality Gates

1. Specify observable behavior from `docs/prueba.pdf`, separating required behavior,
   optional bonuses, and assumptions. Define validation limits, missing resources,
   task/list membership, deletion behavior, statuses, priorities, filter combinations,
   and completion semantics, including empty lists and filter effects on the denominator.
2. For each specification or plan, the agent CLI MUST use the `grilling` skill ("grill me")
   for a structured review of design decisions and tradeoffs with the user. Record decisions,
   alternatives, rationale, and unresolved questions in the artifact; carry consequential
   architectural decisions into `DECISION_LOG.md`.
3. Check constitution compliance before planning research and after design. Surface
   conflicts explicitly and resolve them before claiming compliance.
4. Build and smoke-test a minimal containerized FastAPI application with a health endpoint
   first. Use a `.dockerignore` to exclude secrets and irrelevant build context.
5. Implement complete use cases through HTTP, application/domain, and persistence, with
   tests accompanying each behavior change. Optional authentication MUST NOT block core CRUD;
   if implemented, authorization MUST protect resource access as well as endpoint entry.
6. Run all Principle VII gates and the documented Compose startup/health check before
   delivery. Verify persistence across an application restart. Report failed or unavailable
   checks accurately.
7. Perform a final constitution review and verify README commands and the decision log
   against delivered behavior. Evaluate bonuses only after core acceptance scenarios and
   quality gates pass.

## Governance

- Specifications, plans, tasks, implementations, and reviews MUST comply with this
  constitution. `docs/prueba.pdf` remains the challenge requirements source; explicit
  user changes take precedence and MUST be reflected in affected artifacts.
- Constitution compliance MUST be checked during planning and final review. Conflicts
  MUST be surfaced explicitly rather than silently weakening a requirement. Recording
  a conflict or tradeoff does not waive a requirement; an incompatible change requires
  an explicit amendment.
- Amendments MUST include a rationale, a semantic version update, and synchronization
  of affected templates and project artifacts, including the Sync Impact Report.
- Use MAJOR versions for incompatible principle changes, MINOR versions for new or
  materially expanded standards, and PATCH versions for clarifications.
- Preserve the original ratification date and update the amendment date when changed.
- Every rule MUST remain concise, actionable, and verifiable.

**Version**: 4.0.0 | **Ratified**: 2026-10-07 | **Last Amended**: 2026-10-07
