# Task: Rename Router Layer

**Date:** 2026-07-06  
**State:** Draft  
**Priority:** Medium  
**Type:** Refactoring / Naming Consistency

---

## 0. TDD Contract
- [ ] This is a documentation/naming task - no code tests required
- [ ] All file renames verified to not break imports
- [ ] All documentation updated consistently

---

## 1. Context & Scope

### Rationale

The term **"Router"** is misleading for this layer. In traditional software architecture, "router" implies a central processing component that performs transformations, business logic, or coordination between systems. However, in Apelios:

- The layer is **stateless** - it holds no position data, performs no calculations
- The layer is a **pure passthrough** - it does not transform or process data
- The layer is a **router** - it maps input topics to output topics based on configuration
- The "smart" processing (math, state integration) happens in the **Fixture Layer**

Using "Router" creates cognitive dissonance and makes the architecture harder to understand. The name should reflect its actual function: **routing messages between Input and Fixture layers**.

### Current Architecture Flow
```
Input Layer (publishes {value, type, timestamp})
    → Router (stateless passthrough + topic routing)
    → Fixture Layer (state engine + math)
    → Output Layer (protocol translation)
```

### Name Options

| Option | Pros | Cons | Vote |
|--------|------|------|------|
| **router** | Simple, accurate, industry-standard term | May be confused with network routing | ⭐⭐⭐⭐ |
| **mapper** | Describes the mapping function clearly | Slightly generic | ⭐⭐⭐ |
| **topic_router** | Very explicit about function | Long, but clear | ⭐⭐⭐⭐ |
| **message_router** | Explicit about message handling | Longer | ⭐⭐⭐ |
| **broker_router** | Emphasizes NATS/broker context | Redundant (broker is separate) | ⭐⭐ |
| **dispatcher** | Implies routing/distribution | Can imply logic/processing | ⭐⭐ |
| **forwarder** | Emphasizes passthrough nature | Less common term | ⭐⭐ |
| **switchboard** | Metaphor for routing connections | Less technical | ⭐ |

**Recommendation:** **router** - Simple, accurate, and aligns with the layer's single responsibility.

---

## 2. Strict Constraints

- Maintain backward compatibility where possible (update imports, not break external APIs)
- All files in a directory must use consistent naming
- Documentation must be updated atomically
- Do not change functionality, only naming

---

## 3. Decision: Selected Name

**New Name: router**

This is the most accurate and concise term that describes the layer's function as a stateless topic-based message router.

---

## 4. Implementation Steps

### Phase 1: Directory Renames

| # | Task | Old Path | New Path | Action |
|---|------|----------|----------|--------|
| 4.1.1 | Rename source directory | `src/apelios/router/` | `src/apelios/router/` | `mv src/apelios/router/ src/apelios/router/` |
| 4.1.2 | Rename test directory | `tests/router/` | `tests/router/` | `mv tests/router/ tests/router/` |

### Phase 2: File Renames (Source)

| # | Task | Old Path | New Path | Action |
|---|------|----------|----------|--------|
| 4.2.1 | Rename runtime manager | `src/apelios/router/router_runtime_manager.py` | `src/apelios/router/router_runtime_manager.py` | Rename file |
| 4.2.2 | Rename core module | `src/apelios/router/router_core.py` | `src/apelios/router/router_core.py` | Rename file |
| 4.2.3 | Rename input subscriber | `src/apelios/router/router_input_subscriber.py` | `src/apelios/router/router_input_subscriber.py` | Rename file |
| 4.2.4 | Rename output publisher | `src/apelios/router/router_output_publisher.py` | `src/apelios/router/router_output_publisher.py` | Rename file |
| 4.2.5 | Update `__init__.py` | `src/apelios/router/__init__.py` | `src/apelios/router/__init__.py` | Update imports |

### Phase 3: File Renames (Tests)

| # | Task | Old Path | New Path | Action |
|---|------|----------|----------|--------|
| 4.3.1 | Rename test file | `tests/router/test_router_core.py` | `tests/router/test_router_core.py` | Rename file |
| 4.3.2 | Rename test file | `tests/router/test_router_runtime_manager.py` | `tests/router/test_router_runtime_manager.py` | Rename file |
| 4.3.3 | Rename test file | `tests/router/test_router_input_subscriber.py` | `tests/router/test_router_input_subscriber.py` | Rename file |
| 4.3.4 | Rename test file | `tests/router/test_router_output_publisher.py` | `tests/router/test_router_output_publisher.py` | Rename file |
| 4.3.5 | Rename test file | `tests/router/test_integration_router.py` | `tests/router/test_integration_router.py` | Rename file |

### Phase 4: Update Imports in Source Files

| # | Task | File | Old Import | New Import | Action |
|---|------|------|------------|------------|--------|
| 4.4.1 | Update orchestrator | `src/apelios/orchestrator.py` or similar | `fromapelios.router...` | `fromapelios.router...` | Search and replace |
| 4.4.2 | Update fixture input subscriber | `src/apelios/fixture/fixture_input_subscriber.py` | Any router references | Use router references | Search and replace |
| 4.4.3 | Update any cross-layer imports | All `src/apelios/*/`.py | `router` references | `router` references | Global search |

### Phase 5: Update Configuration References

| # | Task | File | Old | New | Action |
|---|------|------|-----|-----|--------|
| 4.5.1 | Routing config | `src/apelios/router/router_core.py` | `mapping/` directory references | `routing/` directory references | Already done in Phase 6 |
| 4.5.2 | Runtime manager config | `src/apelios/router/router_runtime_manager.py` | `_MAPPING_DIR` | `_ROUTING_DIR` | Already done in Phase 4 |

### Phase 6: Update Documentation

| # | Task | File | Old | New | Action |
|---|------|------|-----|-----|--------|
| 4.6.1 | Architecture doc | `docs/architecture/architecture.md` | "Router" section | "Router" section | Rename section D |
| 4.6.2 | Update references | `docs/architecture/architecture.md` | All "Router" mentions | "Router" where appropriate | Careful review |
| 4.6.3 | Update diagrams | `docs/diagrams/system-architecture.drawio` | "Router" labels | "Router" labels | Manual edit |
| 4.6.4 | Update diagrams | `docs/diagrams/router-architecture.drawio` | Rename file | `docs/diagrams/router-architecture.drawio` | Rename file |
| 4.6.5 | Update C4 diagrams | `docs/c4/*.drawio` | "Router" references | "Router" references | Manual edit |

### Phase 7: Update Task Documentation

| # | Task | File | Old | New | Action |
|---|------|------|-----|-----|--------|
| 4.7.1 | Phase 2 tasks | `docs/tasks/002-refactor-phase2-router.md` | Rename file | `docs/tasks/002-refactor-phase2-router.md` | Rename file |
| 4.7.2 | Phase 7 tasks | `docs/tasks/007-refactor-phase7-source-field-in-input-layer.md` | "router" references | "router" references | Update content |
| 4.7.3 | Update README | `docs/tasks/README.md` | router links | router links | Update links |

### Phase 8: Update ADR References

| # | Task | File | Old | New | Action |
|---|------|------|-----|-----|--------|
| 4.8.1 | ADR references | `docs/adr/*.md` | "Router" layer mentions | "Router" layer mentions | Search and replace |

### Phase 9: Update Other Documentation

| # | Task | File | Old | New | Action |
|---|------|------|-----|-----|--------|
| 4.9.1 | README.md | `README.md` | router references | router references | Search and replace |
| 4.9.2 | Any other docs | `docs/*.md` | router references | router references | Search and replace |

---

## 5. Detailed Change List

### Files to Rename (Directory Structure)
```
src/apelios/router/
├── __init__.py
├── router_core.py → router_core.py
├── router_input_subscriber.py → router_input_subscriber.py
├── router_output_publisher.py → router_output_publisher.py
└── router_runtime_manager.py → router_runtime_manager.py

tests/router/
├── test_router_core.py → test_router_core.py
├── test_router_runtime_manager.py → test_router_runtime_manager.py
├── test_router_input_subscriber.py → test_router_input_subscriber.py
├── test_router_output_publisher.py → test_router_output_publisher.py
└── test_integration_router.py → test_integration_router.py
```

### Files to Update (Content Changes)
- All files that import from `apelios.router.*` → change to `apelios.router.*`
- All documentation mentioning "Router Layer" → change to "Router Layer"
- All configuration references to `router` → change to `router` where appropriate

### Files to Update (Documentation)
- `docs/architecture/architecture.md` - Section D and all references
- `docs/diagrams/system-architecture.drawio` - Labels
- `docs/diagrams/router-architecture.drawio` - Rename to router-architecture.drawio
- `docs/c4/*.drawio` - All C4 context diagrams
- `docs/tasks/002-refactor-phase2-router.md` - Rename to 002-refactor-phase2-router.md
- `docs/tasks/007-refactor-phase7-source-field-in-input-layer.md` - Content updates
- `docs/tasks/README.md` - Link updates
- `docs/adr/*.md` - Layer name references
- Any other markdown files in docs/

---

## 6. Verification Checklist

- [ ] All source files compile/run without errors
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] All imports resolve correctly
- [ ] No references to old `router` module paths remain
- [ ] All documentation consistently uses "Router" instead of "Router" for the layer
- [ ] Diagram files are renamed and updated
- [ ] Git history is clean (one commit per logical change or one big rename commit)

---

## 7. Execution Strategy

### Recommended Order
1. **First:** Rename directories (src and tests)
2. **Second:** Rename files within directories
3. **Third:** Update imports in source code (use search/replace)
4. **Fourth:** Update imports in test code
5. **Fifth:** Update documentation
6. **Last:** Update diagrams and ADRs

### Search/Replace Patterns

**For Python imports:**
```bash
# From source root
find src -name "*.py" -exec sed -i 's/from apelios\.router/from apelios.router/g' {} \;
find src -name "*.py" -exec sed -i 's/apelios\.router/apelios.router/g' {} \;
```

**For tests:**
```bash
find tests -name "*.py" -exec sed -i 's/from apelios\.router/from apelios.router/g' {} \;
find tests -name "*.py" -exec sed -i 's/apelios\.router/apelios.router/g' {} \;
```

**For documentation:**
```bash
find docs -name "*.md" -exec sed -i 's/Router Layer/Router Layer/g' {} \;
find docs -name "*.md" -exec sed -i 's/router/router/g' {} \;  # Review carefully!
```

> **⚠️ WARNING:** The sed commands above are aggressive. Review changes carefully and consider doing them incrementally with manual verification. Some words like "router" may appear in contexts that shouldn't be changed (e.g., describing traditional router patterns).

---

## 8. Rollback Plan

If issues arise:
1. `git checkout .` to revert all changes
2. The rename can be split into smaller commits for easier rollback
3. Keep old directory temporarily and use symlinks during transition if needed

---

## 9. Name Change Documentation

After completing the rename, add a note to the architecture documentation:

**In `docs/architecture/architecture.md`:**
- Update Section 3 (Architectural Principles) to reflect the new terminology
- Update Section 6.D (formerly Router) to be "Router (formerly Router)"
- Add a footnote explaining the rename

**In `docs/architecture/architecture-changes.md`:**
- Add a new section documenting the name change as a completed migration

---

## Notes

### Why Not Other Names?

- **mapper**: Good, but slightly less common in event-driven architectures
- **topic_router**: Very accurate but verbose
- **dispatcher**: Implies active logic, which we don't have
- **forwarder**: Doesn't capture the routing/table-lookup aspect
- **switchboard**: Metaphorical but not technical enough

### Historical Context

The name "Router" was inherited from early ADR decisions (see `docs/adr/002-architecture.md`). At that time, the layer may have been envisioned to perform more active processing. However, the architecture evolved to a purer model where:
- Input Layer: Normalization + Type Tagging
- **Router Layer: Stateless Topic Mapping**
- Fixture Layer: State + Math

This rename aligns the naming with the actual implementation.

---

**Document Version:** 1.0  
**Author:** Mistral Vibe (for motzel)  
**Created:** 2026-07-06  
**Status:** Ready for Review
