# Atlas

Atlas is a local-first Personal Treasury / Financial Decision Engine.

## Product goal

Reduce the number of manual financial decisions and improve the quality of the decisions that remain.

## Current release

`v0.4` — Local Web + SQLite MVP.

### User Story

As a user, I want to enter new income, generate an allocation proposal, edit it, post it, and see updated balances and ledger history.

## Windows usage

Current development version requires Python.

```powershell
cd atlas
scripts\start_windows.cmd
```

Future target:

```text
Atlas.exe
```

## Data

SQLite database:

```text
app\data\atlas.db
```

Back up this file.

## Modules

- Treasury: cash allocation, vaults, ledger
- Investments: planned
- Business Capital: planned
- AI Career Resilience: planned
