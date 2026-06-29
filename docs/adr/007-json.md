# ADR 007: JSON Configuration

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

Throughout Apelios, JSON is used to configure the software. It is used primarily where users need to change settings, routings, and similar configurations.

## Considerations

YAML was considered as an alternative since it is also a well-known configuration format. However, YAML requires strict indentation formatting (similar to Python) and is more error-prone for users. JSON can be parsed more reliably and is better suited for programmatic generation and validation.

## Decision

JSON was chosen because it is a well-known format that is widely supported and easy to understand and parse.