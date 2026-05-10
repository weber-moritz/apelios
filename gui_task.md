# 🤖 Apelios GUI: Autonomous Iteration Guideline

## ⚠️ CRITICAL AGENT PROTOCOLS

1. **TOOL SYNTAX:** Always use `filepath` as the parameter name. **Never** use `file_path`.
2. **NO BASH:** Use only the provided file tools and the **SecureDevTools** MCP tools.
3. **EXECUTION:**
* To test: Use `run_tests(args="tests/gui/...")`
* To verify logic: Use `run_script(script_name="...")`


4. **TDD LOOP:** You must follow this sequence for every sub-task:
* `Create/Edit Test File` -> `run_tests` (Observe Failure) -> `Implement Code` -> `run_tests` (Observe Pass).



---

## 📋 Project Context: Apelios

* **Purpose:** Camera follow spot system for moving head DMX fixtures.
* **Hardware:** Steam Deck (Controller) + NATS Broker + DMX Middleware.
* **GUI Stack:** Python, PySide6/PyQt (Qt), Asyncio, NATS.

---

## 📊 Phase 1: Foundation 🟡 (Active)

* [x] Create iteration guideline.
* [x] Read existing codebase structure.
* [ ] **Next Task:** Create directory structure: `src/apelios/gui/{views,controllers,models,components}`.
* [ ] Create `__init__.py` files for all new packages.
* [ ] Write `tests/gui/conftest.py` with global mocks (NATS, VideoStream).
* [ ] Write tests for `SettingsModel`.
* [ ] Implement `SettingsModel` (Persistence & Signals).
* [ ] Write integration tests for `MainOrchestrator`.

## 📋 Phase 2: Core Components ⚪

* [ ] **MenuBar Component:** Tab switching logic and signals.
* [ ] **Overlay System:** Implementation of Circle, Crosshair, and Dot renderers.
* [ ] **Exclusion Logic:** Ensure only one overlay is active at a time.
* [ ] **VideoController:** Lifecycle management (Start/Stop/Heartbeat).

---

## 🔧 MCP Tool Reference

| Tool                      | Usage                                                        |
| ------------------------- | ------------------------------------------------------------ |
| `run_tests`               | Runs `./.venv/bin/pytest`. Pass file paths in `args`.        |
| `run_script`              | Runs `./.venv/bin/python`. Use for quick logic verification. |
| `read_file`               | Read code. Use this before editing.                          |
| `edit_existing_file`      | Use for large rewrites.                                      |
| `single_find_and_replace` | Use for targeted fixes (Use `filepath`!).                    |

---

## 🧪 Testing Patterns (Strict)

```python
# conftest.py pattern
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_nats():
    """Mock NATS client for GUI testing."""
    client = MagicMock()
    client.publish = MagicMock()
    return client

# Signal Testing Pattern
def test_slider_emits_signal(qtbot):
    widget = CustomSlider()
    with qtbot.waitSignal(widget.valueChanged, timeout=1000) as blocker:
        widget.setValue(50)
    assert blocker.args[0] == 50

```

---

## 🔧 Code Conventions

* **Imports:** Use absolute imports (`from apelios.gui.models import ...`).
* **Type Hints:** Mandatory for all function signatures.
* **Async:** Use `asyncio` for NATS interactions; use `qasync` or similar for Qt/Async integration if required.
* **Logging:** Use `logging.getLogger("apelios.gui")`. No `print()`.

---

## 🚀 Overnight Autonomy Instructions

1. **Work through Phase 1 checkboxes.** Do not skip to Phase 2 until Phase 1 is 100% green.
2. **Stuck Pattern:** If a test fails 3 times and you cannot find the fix:
* Leave a `FIXME` comment in the code detailing what you tried.
* Update the "Blockers" section in this file.
* Move to the next independent task (e.g., if `SettingsModel` is stuck, try `MenuBar` UI layout).


3. **Context Refresh:** Every 5 turns, output a `### 🧠 Current State Summary` to maintain your attention on the goal.

---

## 📊 Progress Tracking

* **Last updated:** 2026-05-10
* **Current phase:** Phase 1 - Foundation
* **Active Task:** Creating module structure.
* **Blockers:** None.

---

*End of Guideline - Read this at the start of every message.*