# URL Shortener API

A small HTTP API that turns a long URL into a short code: `POST` a URL (optionally with your
own alias), get a short code back, and a `GET` on that code redirects to the original. Every
link expires 24 hours after it is created, and each one keeps a count of how many times it
has been followed. No accounts, no authentication.

**Not built yet.** This repository currently contains the plan only: the agreed requirements
in [PRD.md](PRD.md), the design in [ARCHITECTURE.md](ARCHITECTURE.md), the build order in
[TASKS.md](TASKS.md), and working notes in [AGENTS.md](AGENTS.md). The commands below are
what will work once the tasks in TASKS.md are done.

## Install

Requires Python 3.11 or newer.

```
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API is then on <http://127.0.0.1:8000>, with interactive docs at `/docs` and a health
check at `/health`. Data is kept in a SQLite file (`./shortener.db` by default) and survives
restarts.

Configuration, all optional, via environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_PATH` | `./shortener.db` | Where the SQLite file lives. |
| `BASE_URL` | `http://127.0.0.1:8000` | Prefix used to build the returned `short_url`. |
| `LINK_TTL_HOURS` | `24` | Link lifetime. |

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/links` | Create a short link from `{"url": "...", "alias": "optional"}`. |
| `GET` | `/{code}` | Redirect (302) to the original URL. |
| `GET` | `/links/{code}` | Read the link's details and usage count. |
| `GET` | `/health` | Liveness check. |

## Test

```
pytest
```

Runs the full suite with no manual setup — each test uses its own temporary database.
