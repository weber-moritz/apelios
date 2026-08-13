---
date: 2026-08-13
state: Done
priority: High
---

# Task 031: Clean NATS Startup and Shutdown

## Context

Apelios starts and runs successfully, but a normal terminal session currently
produces alarming NATS errors:

- During startup, the first readiness probe may run before the newly spawned
  NATS server accepts connections. `nats-py` logs a `ConnectionRefusedError`
  before a later retry succeeds.
- On `Ctrl+C`, `NatsRuntimeManager` handles `SIGINT` directly and terminates the
  server before the orchestrator has disconnected its clients. The clients then
  report `UnexpectedEOF`, `BrokenPipeError`, connection resets, and failed
  reconnect attempts.

The direct signal handling was added because earlier versions could leave the
NATS child process running after Apelios was stopped. That cleanup guarantee
must not be lost.

## Goal

Make normal startup and terminal shutdown clean and deterministic while
ensuring that Apelios never leaves behind a NATS process it created.

Expected normal lifecycle:

```text
start NATS -> wait until ready -> connect layers -> run
stop input -> stop router -> stop fixture -> stop output -> stop NATS -> exit
```

No NATS traceback should be printed during an expected readiness retry or a
normal `Ctrl+C` shutdown.

## Scope

Likely files:

- `src/apelios/main_orchestrator.py`
- `src/apelios/broker/nats_runtime_manager.py`
- focused broker and orchestrator tests

Do not refactor the broker abstraction, processing layers, dependency setup, or
60 Hz loop as part of this task.

## Requirements

### 1. One owner for application signals

- The application entry point/orchestrator must coordinate graceful shutdown.
- `NatsRuntimeManager` must not independently kill NATS before broker clients
  have disconnected.
- Handle at least `SIGINT` and `SIGTERM`; assess `SIGHUP` for terminal closure
  on Linux.
- Repeated stop requests must remain safe and idempotent.

### 2. Preserve child-process cleanup

- Normal exit and `Ctrl+C` must stop the exact NATS process started by Apelios.
- `SIGTERM` and applicable terminal-close behavior must not leave that process
  running.
- Startup failure after spawning NATS must clean up the child and close its log
  file.
- Apelios must never find or kill unrelated `nats-server` processes.
- Port conflicts must continue to fail with a clear error rather than killing
  the process using the port.
- Retain `atexit` only as a fallback, not as the primary ordered shutdown path.

The existing Linux parent-death mechanism must be validated. The current
`prctl(PR_SET_PDEATHSIG, ...)` call appears to execute in the Apelios parent
before `Popen`; parent-death configuration must apply to the NATS child to
protect against abrupt parent death. Any correction must be narrowly scoped and
tested. `SIGKILL` cannot be handled by Python code, so this OS-level fallback is
the relevant protection for that case.

### 3. Quiet, bounded readiness checking

- Wait for the spawned server to accept connections before starting layers.
- Expected connection refusals during this bounded wait must not be logged as
  application errors.
- A genuine timeout or an early NATS process exit must fail startup with a clear
  exception and useful diagnostics.
- Do not hide unexpected errors globally or disable normal NATS client error
  reporting during operation.

### 4. Graceful client shutdown

- Disconnect all layer clients before terminating NATS.
- Continue cleanup if one layer fails to stop, while preserving/reporting the
  original failure appropriately.
- Do not allow NATS clients to begin reconnecting solely because the application
  stopped its server too early.

## Tests

Add focused regression coverage for:

- readiness retries followed by successful startup;
- readiness timeout and cleanup;
- early NATS process exit during startup;
- shutdown order: all layer stops complete before `stop_server()`;
- `Ctrl+C`/cancellation reaches the orchestrator's graceful cleanup path;
- repeated `stop()` calls are safe;
- only the owned child process is terminated;
- the parent-death fallback is configured for the child on supported Linux
  systems, or is otherwise verified with a small subprocess integration test;
- a real NATS integration start/stop produces no expected-error tracebacks and
  leaves port 4222 free afterward.

Use a non-default free port in automated integration tests where practical to
avoid collisions with a developer's local NATS instance.

## Manual Verification

1. Confirm that port 4222 is initially free.
2. Start Apelios with the documented command.
3. Confirm all runtimes start without a connection-refused traceback.
4. Press `Ctrl+C` once.
5. Confirm the layers stop before the broker and the command exits promptly.
6. Confirm no EOF, broken-pipe, reconnect, or connection-refused traceback is
   printed during shutdown.
7. Confirm no owned NATS process remains and port 4222 is free.
8. Repeat startup and shutdown once to prove that no stale process prevents the
   next run.

## Acceptance Criteria

- [x] Startup reaches a healthy state without expected-error tracebacks.
- [x] A single `Ctrl+C` performs an orderly shutdown and exits promptly.
- [x] Layer broker clients disconnect before the owned NATS process terminates.
- [x] No Apelios-owned NATS process remains after normal exit, `SIGINT`, or
      `SIGTERM`.
- [x] Abrupt parent-death behavior is explicitly tested on Linux or its remaining
      limitation is documented accurately.
- [x] Unrelated NATS processes are never terminated.
- [x] Startup failures clean up all acquired resources.
- [x] Focused unit and integration tests pass.
- [x] Full test suite passes, apart from explicitly documented environment-only
      skips.
- [x] Manual start, `Ctrl+C`, and immediate restart complete cleanly.

## Verification Results

- Focused lifecycle unit tests: 53 passed.
- Real NATS integration tests: 7 passed.
- Complete application test suite: 251 passed.
- Complete repository test collection: 293 passed with three pre-existing
  collection warnings.
- Manual CLI startup and `Ctrl+C` shutdown: clean exit with status 0 and no NATS
  error traceback.
- Post-shutdown check: no `nats-server` process and no listener on port 4222.

## Release Decision

This is a narrow pre-snapshot correctness fix. Avoid unrelated cleanup. After
the acceptance criteria pass, commit and push the fix, then create a new neutral
snapshot tag at that verified commit. If an unpublished snapshot tag already
exists, it may be deleted and replaced with the new dated snapshot.
