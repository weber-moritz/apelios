---
date: 2026-07-27
state: Done
---

# Task 025: Fix NATS Runtime Manager - Remove Global Process Killing

> **Document Purpose:** Replace the dangerous `_kill_stale_nats_servers()` that kills ALL nats-server processes with a safe, scoped approach
> **Problem:** Current implementation kills every `nats-server` process on the system, not just ones owned by Apelios
> **Priority:** HIGH - This is a critical architectural violation (scope of control)
> **Status:** Implementation Complete
> **Files Modified:** `src/apelios/broker/nats_runtime_manager.py`, `tests/broker/test_nats_runtime_manager.py`

---

## 0. TDD Contract
- [ ] Tests written for new behavior before implementation
- [ ] All tests pass after implementation
- [ ] No regression in existing functionality

---

## 1. Context & Scope

### Problem Origin
When starting Apelios, if a NATS server process was already running (e.g., from a previous Ctrl+C termination), the application would fail. An AI-generated solution added `_kill_stale_nats_servers()` which **kills ALL `nats-server` processes on the system** — not just Apelios-owned ones.

This violates the **Principle of Least Surprise** and **Ownership Boundary**: Apelios should only manage resources it created.

### Files in Scope
- `src/apelios/broker/nats_runtime_manager.py`

### DO NOT TOUCH
- Other broker implementations (memory)
- Client code using the runtime manager
- NATS server configuration structure

---

## 2. Strict Constraints

- **MUST NOT** kill processes outside Apelios' ownership scope
- **MUST** ensure NATS server dies when Apelios stops (any exit: normal, Ctrl+C, crash, `kill`)
- **MUST** provide clear error message when port is already in use
- **MUST** maintain existing API (`start_server()`, `stop_server()`, `is_running()`)
- **MUST** use only standard library (no new dependencies)
- **SHOULD** leverage OS-level process management where possible

---

## 3. Problem Statement

### Current Issues
1. **Overreach:** `_kill_stale_nats_servers()` kills ALL `nats-server` processes on the system using `pgrep -f nats-server`
2. **No Ownership Check:** Does not verify if the process belongs to Apelios before killing
3. **Silent Failures:** Swallows all exceptions (PermissionError, ProcessLookupError) silently
4. **Wrong Approach:** Solves startup problem by forcefully clearing the way, rather than fixing the root cause (stale process from previous run)

### Root Cause
The **real problem** is that NATS server processes are not being properly cleaned up when Apelios exits abnormally (Ctrl+C, crash, `kill -9`). The current code tries to fix this at startup by killing everything, rather than fixing cleanup at exit.

---

## 4. Solution Architecture

### Core Principle
**Apelios should only manage its own child processes.**

### Approach: Two-Part Fix

#### Part A: Remove Dangerous Startup Killing (Immediate Fix)
Remove `_kill_stale_nats_servers()` entirely. If port is in use at startup, **fail with clear error** and let user manually resolve it.

#### Part B: Guarantee Cleanup on ANY Exit (Robust Fix)
Ensure NATS server process dies when Apelios stops, regardless of how it stops:
- Normal exit
- Ctrl+C (SIGINT)
- `kill` (SIGTERM)  
- Crash/unhandled exception

### OS-Level Process Management (Recommended)

On **Unix-like systems** (Linux, macOS), we can use `prctl` to automatically kill the child when parent dies:

```python
# In start_server(), when creating the process:
import ctypes
import os

# Only available on Linux
try:
    libc = ctypes.CDLL("libc.so.6")
    PR_SET_PDEATHSIG = 1
    SIGTERM = 15
    libc.prctl(PR_SET_PDEATHSIG, SIGTERM, 0, 0, 0)
except:
    pass  # Not on Linux, fall back to manual cleanup

self.process = subprocess.Popen(
    ["nats-server", "-p", str(self.port)],
    stdout=self.log_file,
    stderr=self.log_file,
    stdin=subprocess.DEVNULL,
    start_new_session=True,
    preexec_fn=lambda: os.setsid(),  # Already done by start_new_session
)
```

**What this does:** When the parent (Apelios) dies for ANY reason, the kernel automatically sends SIGTERM to the child (NATS server). This solves the zombie process problem at the OS level.

### Fallback for Non-Unix Systems
For Windows or systems without `prctl`, use **atexit registration**:

```python
import atexit

# In __init__:
atexit.register(self._cleanup_on_exit)

def _cleanup_on_exit(self) -> None:
    """Called by Python interpreter on normal exit."""
    if self.process and self.process.poll() is None:
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
```

### Signal Handler for Ctrl+C
```python
import signal

# In __init__:
signal.signal(signal.SIGINT, self._handle_signal)
signal.signal(signal.SIGTERM, self._handle_signal)

def _handle_signal(self, signum, frame) -> None:
    """Handle SIGINT/SIGTERM by stopping NATS server."""
    if self.process:
        self.process.terminate()
    # Re-raise to allow normal Python signal handling
    raise SystemExit(1)
```

---

## 5. Implementation Steps

### Phase 1: Remove Dangerous Code (Critical)
- [ ] Delete `_kill_stale_nats_servers()` method entirely
- [ ] Remove call to `_kill_stale_nats_servers()` from `start_server()`
- [ ] Update port conflict check to happen BEFORE any process creation

### Phase 2: Enhance Process Creation (Recommended)
- [ ] Add `prctl` call on Linux to auto-kill child on parent death
- [ ] Keep `start_new_session=True` (already present)
- [ ] Keep `stdin=subprocess.DEVNULL` (already present)

### Phase 3: Add Exit Guards (Robustness)
- [ ] Register `atexit` handler for normal exit
- [ ] Register signal handlers for SIGINT/SIGTERM
- [ ] Add try/finally in `start_server()` to ensure cleanup on health check failure

### Phase 4: Improve Error Messages
- [ ] Make port-in-use error message actionable: include command to check/free port

---

## 6. Code Changes

### Removal (Critical)
```python
# DELETE THIS METHOD COMPLETELY:
def _kill_stale_nats_servers(self) -> None:
    """Kill any existing nats-server processes that might be using our port."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "nats-server"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            for pid_str in result.stdout.strip().split('\n'):
                try:
                    pid = int(pid_str.strip())
                    os.kill(pid, signal.SIGTERM)
                except (ValueError, ProcessLookupError, PermissionError):
                    pass
    except Exception:
        pass
```

### Modified `start_server()` (Safer)
```python
async def start_server(self) -> None:
    if self.process is not None:
        raise RuntimeError("NATS server already running")

    # Check port FIRST - fail fast with clear message
    if self._is_port_in_use(self.port):
        raise RuntimeError(
            f"Port {self.port} is already in use. "
            f"Another process may be using it. "
            f"Check with: lsof -i :{self.port} or ss -tlnp | grep {self.port}"
        )

    log_path = self.log_dir / "nats-server.log"
    self.log_file = open(log_path, "a", buffering=1)

    # Setup auto-cleanup on parent death (Linux)
    self._setup_auto_cleanup()

    self.process = subprocess.Popen(
        ["nats-server", "-p", str(self.port)],
        stdout=self.log_file,
        stderr=self.log_file,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Register cleanup handlers
    atexit.register(self._cleanup_on_exit)

    try:
        await self.health_check(timeout=5)
    except Exception:
        await self.stop_server()
        raise
```

### New Helper Methods
```python
def _setup_auto_cleanup(self) -> None:
    """Setup OS-level auto-cleanup of child process on parent death."""
    try:
        # Linux: automatically kill child when parent dies
        libc = ctypes.CDLL("libc.so.6")
        PR_SET_PDEATHSIG = 1
        SIGTERM = 15
        libc.prctl(PR_SET_PDEATHSIG, SIGTERM, 0, 0, 0)
    except Exception:
        pass  # Not on Linux, rely on other cleanup methods

def _cleanup_on_exit(self) -> None:
    """Called on normal Python exit."""
    if self.process and self.process.poll() is None:
        try:
            self.process.terminate()
            self.process.wait(timeout=2)
        except Exception:
            try:
                self.process.kill()
                self.process.wait(timeout=1)
            except Exception:
                pass
    if self.log_file:
        try:
            self.log_file.close()
        except Exception:
            pass
```

---

## 7. Acceptance Criteria

### Functional
- [ ] NATS server starts when port is free
- [ ] NATS server **fails to start** with clear error when port is in use
- [ ] NATS server **dies automatically** when Apelios exits normally
- [ ] NATS server **dies automatically** when Apelios receives SIGINT (Ctrl+C)
- [ ] NATS server **dies automatically** when Apelios receives SIGTERM (`kill`)
- [ ] NATS server **dies automatically** when Apelios crashes (unhandled exception)
- [ ] No `pgrep` / `pkill` commands are used anywhere in the codebase

### Safety
- [ ] Apelios never kills processes it didn't create
- [ ] Running `pgrep -f nats-server` does NOT return Apelios' PID
- [ ] Another user's NATS server on a different port is NOT affected by Apelios

### Code Quality
- [ ] No silent exception swallowing
- [ ] Clear, actionable error messages
- [ ] All existing tests continue to pass

---

## 8. Testing Strategy

### Manual Tests
1. Start Apelios → NATS server starts
2. Stop Apelios with Ctrl+C → NATS server stops
3. Start Apelios again → NATS server starts (no stale process)
4. Start external NATS server on same port → Apelios fails to start with clear error
5. Start Apelios, then start external NATS on same port → External NATS fails (port in use), Apelios continues

### Automated Tests
```python
# In tests/broker/test_nats_runtime_manager.py

async def test_start_server_fails_on_port_conflict():
    """Verify port conflict is detected and fails cleanly."""
    # Start a NATS server on the target port
    conflicting_process = subprocess.Popen(
        ["nats-server", "-p", str(TEST_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    try:
        manager = NatsRuntimeManager(config=NatsConfig(port=TEST_PORT))
        with pytest.raises(RuntimeError, match="already in use"):
            await manager.start_server()
    finally:
        conflicting_process.terminate()
        conflicting_process.wait()

async def test_no_global_process_killing():
    """Verify Apelios never kills external NATS servers."""
    # Start external NATS on a different port
    external_process = subprocess.Popen(
        ["nats-server", "-p", str(TEST_PORT + 1)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    try:
        manager = NatsRuntimeManager(config=NatsConfig(port=TEST_PORT))
        await manager.start_server()
        await manager.stop_server()
        # External process should still be running
        assert external_process.poll() is None
    finally:
        external_process.terminate()
        external_process.wait()
```

---

## 9. Technical Discussion

### Why `PR_SET_PDEATHSIG` is the Right Solution

On Linux, `PR_SET_PDEATHSIG` is the most elegant solution because:
- **Kernel-enforced**: The child process dies immediately when parent dies, even on `kill -9`
- **No cleanup code needed**: Works for crashes, kills, any unexpected termination
- **No race conditions**: The kernel handles it, not user-space code
- **Used by production systems**: Docker, Kubernetes, and other container systems use this pattern

### Why This Matters for Your Thesis

This is a **textbook example of AI critique in software architecture**:

1. **The AI's solution** solved the immediate symptom (port conflict) but violated architectural principles (ownership boundary, least surprise)
2. **The human's insight** identified the root cause (stale process from improper cleanup) and reframed the problem correctly
3. **The proper solution** addresses the root cause (ensure cleanup on ALL exit paths) rather than brute-forcing the symptom

**Key architectural lessons:**
- Always manage only resources you own
- Fix problems at the root cause, not the symptom
- Use OS-level mechanisms when available (they're battle-tested)
- Defensive programming: handle normal exit, signals, AND crashes

---

## 10. Related Work

- Task 013: Previous NATS subprocess fixes (port checking, session detachment)
- Architecture Principle: Ownership Boundary (documented in architecture.md)
- Unix process management: `prctl`, process groups, sessions

---

## 11. References

- [prctl(2) - Linux manual page](https://man7.org/linux/man-pages/man2/prctl.2.html)
- [PR_SET_PDEATHSIG explanation](https://stackoverflow.com/questions/21474079/how-to-terminate-child-process-when-parent-exits-in-c)
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)
- [atexit module documentation](https://docs.python.org/3/library/atexit.html)
