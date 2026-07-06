# Task Template

**Core Principle: Test-Driven Development (TDD) is mandatory for all tasks.**
Tests are the specification. Write tests first. AI agents must strictly follow the Red-Green-Refactor cycle. Human review must verify test correctness before implementation proceeds.

Tasks describe a feature implementation or change in detail. They are meant to be written mostly manually. The implementation can be done manually or by an Agent.

---

## Template

```markdown
---
date: YYYY-MM-DD
state: Draft # [Draft | In Progress | Done]
---

# Task XXX: [Short, Actionable Title]

## 0. TDD Contract
- [ ] Tests written and committed before implementation begins
- [ ] All new tests fail initially (Red phase)
- [ ] Test files: [specify test file paths]

## 1. Context & Scope
- **Objective:** [Single sentence describing the goal]
- **Files in Scope:** [List files that will be modified]
- **Test Files:** [List test files to be created/modified]
- **DO NOT TOUCH:** [Files/areas that must remain unchanged]

## 2. Strict Constraints
- [List any non-negotiable technical constraints]
- [e.g., no dynamic memory, no new dependencies, specific patterns to follow]

## 3. Test Specification
- [ ] `test_[functionality]`: [brief description of what it tests]
- [ ] `test_[edge_case]`: [brief description]

## 4. Implementation Steps
- [ ] Step 1: [Specific action]
- [ ] Step 2: [Specific action]

## 5. Acceptance Criteria
- **Build:** [build command] succeeds with no new warnings
- **Test:** [test command] passes all tests
- **Behavior:** [specific observable behavior]
- **Regression:** All existing tests continue to pass
```

---

## AI Workflow Notes

1. **Always start with Section 3 (Test Specification)** — this is your first action
2. **Verify tests fail** before implementing (Red phase)
3. **Implement minimally** to pass tests (Green phase)
4. **Refactor** with test safety net
5. **Never implement** without a corresponding failing test
6. **If you cannot write a test** for a requirement, escalate for clarification — the requirement is not well-defined

---

## Existing Phases

This directory contains the following phase documentation from the TDD migration:

- [001-refactor-phase1-input-layer.md](001-refactor-phase1-input-layer.md) - Input Layer migration tasks
- [002-refactor-phase2-router.md](002-refactor-phase2-router.md) - Router stateless transformation tasks
- [003-refactor-phase3-fixture-layer.md](003-refactor-phase3-fixture-layer.md) - Fixture Layer type migration tasks
- [004-refactor-phase4-config-cleanup.md](004-refactor-phase4-config-cleanup.md) - Configuration cleanup tasks
- [005-refactor-phase5-integration.md](005-refactor-phase5-integration.md) - Integration testing tasks
- [006-refactor-phase6-many-to-one-input-summation.md](006-refactor-phase6-many-to-one-input-summation.md) - Many-to-one input handling tasks
- [007-refactor-phase7-source-field-in-input-layer.md](007-refactor-phase7-source-field-in-input-layer.md) - Source field migration tasks
- [008-refactor-phase8-final-validation.md](008-refactor-phase8-final-validation.md) - Final validation and acceptance criteria
- [009-refactor-phase9-improvement-analysis.md](009-refactor-phase9-improvement-analysis.md) - Improvement analysis, agent execution guide, statistics, and reference documents
- [010-rename-router-layer.md](010-rename-router-layer.md) - Rename Router to Router layer for naming accuracy