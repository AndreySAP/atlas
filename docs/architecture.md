# Architecture

## Decision

Atlas is local-first and web-first.

## Current architecture

```text
Browser
  ↓
FastAPI local server
  ↓
SQLite atlas.db
```

## Principles

1. Data belongs to the user.
2. Balances are calculated from ledger entries.
3. Allocation is proposal-first, post-second.
4. User may edit before posting.
5. Atlas warns about policy deviations but does not block the user.
6. No bank import in MVP.
7. No cloud dependency in MVP.
