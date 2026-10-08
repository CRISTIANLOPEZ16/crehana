# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, Pydantic; [persistence library with rationale]

**Dependency Management**: uv; pyproject.toml; committed uv.lock; frozen local/Docker installs

**Storage**: PostgreSQL

**Testing**: pytest unit/integration/end-to-end; pytest.ini; >=75% all-source statement coverage

**Quality Tools**: Flake8 (.flake8), Black and strict mypy (pyproject.toml)

**Target Platform**: Docker and Docker Compose; non-root application; persistent database

**Project Type**: Single deployable monolith; Domain/Application/Infrastructure

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Check every rule in `.specify/memory/constitution.md`; record PASS/FAIL and evidence for:

- Required stack, uv commands, committed lockfile, frozen local/Docker installation.
- Inward dependencies, OO entities/use cases/adapters, narrow injected persistence interfaces.
- Production modules and tests have cohesive responsibilities; related behavior stays together, and splits follow responsibility boundaries rather than line counts.
- Explicit annotations including locals, descriptive names, justified typing exceptions.
- Pydantic boundaries, independent business invariants, PostgreSQL constraints, atomic writes,
  custom exception mappings, and secret protection.
- Unit, PostgreSQL integration, and running-API/PostgreSQL end-to-end tests; isolated data;
  >=75% statement coverage including unimported application modules.
- Local verification: Flake8, Black --check, strict mypy, all test levels/coverage, Docker build.
- Non-root containers, environment configuration, persistent Compose storage, smoke check.
- Core scope, README commands, DECISION_LOG.md, and final compliance review.
- Completed structured "grill me" review for this plan.

Record conflicts in Complexity Tracking. Justification alone does not waive a rule.

## Structured Design Review *(mandatory)*

Use the `grilling` skill ("grill me") with the user before finalizing this plan.
Record decisions, alternatives, tradeoffs, rationale, and unresolved questions here.
Carry consequential architectural decisions into DECISION_LOG.md.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
Adapt these paths to the application package while preserving inward dependencies.

```text
src/
├── domain/
├── application/
└── infrastructure/

tests/
├── unit/
├── integration/
└── e2e/
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Record conflicts and their resolution; an unresolved conflict remains FAIL.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [Affected rule and resolution/amendment] | [Concrete need] | [Alternative and tradeoff] |
