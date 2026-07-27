# ADR 011: Process Lifecycle Management

**Date:** 2026-07-27  
**Status:** Accepted  
**Supercedes:** None  

---

## Context

Apelios spawns child processes (notably the NATS server) that must be properly managed throughout their lifecycle. A previous implementation attempted to solve process management issues at startup by forcefully killing ALL `nats-server` processes on the system using `pgrep -f nats-server`. This violated the **Ownership Boundary** principle — Apelios should only manage resources it created.

The root cause was not the startup logic, but rather **missing cleanup guarantees** when Apelios exits abnormally (Ctrl+C, crash, `kill`, etc.).

## Decision

**Apelios will manage its child processes with a defense-in-depth approach:**

1. **OS-Level Guarantee (Linux):** Use `PR_SET_PDEATHSIG` to instruct the kernel to automatically send SIGTERM to child processes when the parent dies
2. **Application-Level Guarantees:** Register cleanup handlers via `atexit` for normal exit and signal handlers for SIGINT/SIGTERM
3. **Fail-Fast at Startup:** If a port is already in use, fail with a clear, actionable error message instead of forcefully clearing the way

### Implementation Details

```python
# In __init__: Register cleanup handlers
def __init__(self, config: NatsConfig | None = None):
    # ... existing setup ...
    
    # Register cleanup handlers
    atexit.register(self._cleanup_on_exit)
    signal.signal(signal.SIGINT, self._handle_exit_signal)
    signal.signal(signal.SIGTERM, self._handle_exit_signal)

# In start_server: Setup OS-level cleanup (Linux)
async def start_server(self) -> None:
    # Check port FIRST
    if self._is_port_in_use(self.port):
        raise RuntimeError(
            f"Port {self.port} is already in use. "
            f"Check with: lsof -i :{self.port} or ss -tlnp | grep {self.port}"
        )
    
    # Setup auto-cleanup on Linux
    self._setup_auto_cleanup()
    
    # Create process
    self.process = subprocess.Popen(
        ["nats-server", "-p", str(self.port)],
        stdout=self.log_file,
        stderr=self.log_file,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

# OS-level cleanup setup
def _setup_auto_cleanup(self) -> None:
    """Setup OS-level auto-cleanup of child process on parent death (Linux)."""
    try:
        libc = ctypes.CDLL("libc.so.6")
        PR_SET_PDEATHSIG = 1
        SIGTERM = 15
        libc.prctl(PR_SET_PDEATHSIG, SIGTERM, 0, 0, 0)
    except Exception:
        pass  # Not on Linux, rely on atexit + signal handlers

# Signal handler
def _handle_exit_signal(self, signum, frame) -> None:
    """Handle SIGINT/SIGTERM by triggering cleanup and exiting."""
    self._cleanup_on_exit()
    raise SystemExit(1)

# Centralized cleanup
def _cleanup_on_exit(self) -> None:
    """Clean up NATS server process and log file on exit."""
    if self.process and self.process.poll() is None:
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        except ProcessLookupError:
            pass
    
    if self.log_file:
        try:
            self.log_file.close()
        except Exception:
            pass
        self.log_file = None
    
    self.process = None
```

---

## Consequences

### Positive

- **Ownership Boundary Maintained:** Apelios only manages its own child processes, never touches other users' processes
- **Guaranteed Cleanup on Linux:** `PR_SET_PDEATHSIG` ensures child dies even on `kill -9` or segfault
- **Cross-Platform Fallback:** atexit + signal handlers work on all platforms
- **Clear Error Messages:** Users get actionable information when ports are in use
- **No Silent Failures:** All exceptions in cleanup are logged, not swallowed

### Negative

- **Linux-Specific Feature:** `PR_SET_PDEATHSIG` only works on Linux; other platforms rely on application-level handlers
- **Slight Complexity Increase:** More code to manage process lifecycle, but this is necessary for production robustness

---

## Alternatives Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Kill all at startup** | Simple, "clears the way" | Violates ownership, kills other users' processes | ❌ Rejected |
| **Manual cleanup only** | Simple | Fails on crash, Ctrl+C, kill | ❌ Insufficient |
| **Process groups** | Works on Unix | Complex, still needs signal handling | ❌ PR_SET_PDEATHSIG is simpler |
| **PR_SET_PDEATHSIG + atexit + signals** | Most robust, OS-enforced | Linux-specific component | ✅ **Accepted** |

---

## Lessons Learned

This ADR highlights a critical difference between **AI-generated solutions** and **human architectural reasoning**:

1. **AI solved the symptom:** "Port is in use" → kill all processes to clear it
2. **Human identified the root cause:** Process not cleaned up on abnormal exit
3. **Proper solution:** Ensure cleanup on ALL exit paths

**Architectural Principles Reinforced:**
- **Ownership Boundary:** Only manage resources you created
- **Defensive Programming:** Handle normal exit, signals, AND crashes
- **Fail-Fast with Context:** Clear errors are better than silent fixes
- **Use OS Mechanisms:** Kernel-enforced guarantees are more reliable than user-space code

---

## Related Documents

- [Task 025: Fix NATS Runtime Manager](../tasks/025-fix-nats-kill-all-processes.md)
- [Architecture: Core Architectural Rules](../architecture/architecture.md#core-architectural-rules-never-violate)
- [NFR: Reliability & Fault Tolerance](../architecture/non-functional-requirements-list.md#reliability--fault-tolerance)
