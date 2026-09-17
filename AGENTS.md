# Agent guide

## What this repository is

A URL shortener HTTP API. **[PRD.md](PRD.md) is the agreed goal — read it before you change
anything, build toward it, and never edit it.** The design is
[ARCHITECTURE.md](ARCHITECTURE.md); the ordered work is [TASKS.md](TASKS.md). If a task and
the PRD disagree, the PRD wins: raise it rather than quietly changing scope.

## Stack

Python 3.11+, FastAPI + Pydantic v2, uvicorn, SQLite through the stdlib `sqlite3` module
(no ORM), pytest with FastAPI's `TestClient`. Do not add a dependency unless a task names
it; each one in ARCHITECTURE.md's Stack table has a requirement behind it.

## Layout

```
app/
  main.py      FastAPI app and the four routes
  schemas.py   Pydantic request/response models (input validation lives here)
  codes.py     short-code generation, reserved words
  store.py     all SQL; the only module that talks to sqlite3
  db.py        connection per request, schema bootstrap
  clock.py     now() as an injectable dependency
  config.py    settings from the environment
  schema.sql   the links table
tests/         pytest suite, one module per journey
```

## Conventions

- All SQL stays in `app/store.py`, with parameterised queries only — never f-string a value
  into a statement. Routes must not see `sqlite3` exceptions; `store` raises domain errors.
- Get the current time from the `clock.now()` dependency, never `datetime.now()` inline —
  the expiry tests depend on that seam being the only one.
- Status codes: 201 create, 302 redirect, 404 unknown code, 409 alias taken, 410 expired,
  422 malformed input. Keep them exactly as written; tests assert on them.
- Times are UTC, stored as ISO-8601 strings.
- Type-annotate function signatures. Keep modules small; a new module needs a reason.
- Routes are thin: validate, call `store`, map the result to a response.

## Install

```
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Settings come from the environment: `DATABASE_PATH` (default `./shortener.db`), `BASE_URL`
(default `http://127.0.0.1:8000`), `LINK_TTL_HOURS` (default 24 — fixed by the PRD, an env
var only so tests can shorten it). Interactive docs at `/docs`, health at `/health`.

## Test

```
pytest
```

The suite must run with no manual setup: each test builds its app against a temp SQLite file
and overrides the clock dependency for anything time-dependent. Never `sleep` to test expiry.
Every task in TASKS.md lands with its tests in the same change.
