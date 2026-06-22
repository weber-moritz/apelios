# ADR 006: Input Adapters

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

Input adapters provide a stateless interface between the operating system and the Apelios system. Each adapter is Linux-first but can be expanded to run on other operating systems as well.

## Decision

The adapter uses a base `BaseInputAdapter` class that implements common functionality to avoid code repetition.

The input runtime manager calls each adapter's tick function on every 60Hz tick. The runtime manager's tick is called by the main orchestrator.