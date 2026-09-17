# Architecture: URL Shortener API

The goal is defined in [PRD.md](PRD.md); this document says how the first version is built.

One FastAPI application with one SQLite file behind it. It exposes four routes: create a
link, redirect a code, read a code's stats, and a health check. There is no UI, no
authentication, no background worker: expiry is an `expires_at` column checked on read, not
a scheduled job. Everything the PRD asks for fits in a single deployable process, so that is
what this design is.

## Stack

| Technology | Reason |
| --- | --- |
| Python 3.11+ | FastAPI's ecosystem; `datetime.UTC` and modern typing available without back-ports. |
| FastAPI | Required by PRD Constraints. Also gives request validation and `RedirectResponse` for the 302 in requirement 2. |
| Pydantic v2 (ships with FastAPI) | Requirement 4 (reject invalid input): `HttpUrl` validates absolute URLs, and a constrained string validates aliases, without hand-written parsing. |
| Uvicorn | The standard ASGI server for FastAPI; needed to run the app for verification. |
| SQLite via stdlib `sqlite3` | Storage required by PRD Constraints; a file gives requirement 8 (persistence across restarts). Stdlib driver, not SQLAlchemy — one table, a handful of statements, and the developer asked for the simplest option. Rejected: SQLAlchemy + Alembic (migration machinery no requirement asks for). |
| pytest + `httpx`/`TestClient` | Requirement 9 (automated suite, no manual setup). Each test gets its own temp DB file, so the suite is self-contained. |
| `secrets` (stdlib) | Auto-generated codes (requirement 1); unguessable codes cost nothing over `random` and avoid a sequential-ID enumeration of everyone's links. |

No queue, cache, second service or second datastore: no requirement needs one. Single
instance, single file, as recorded in the PRD defaults.

## Parts

All application code lives in one importable package, `app/`.

- **`app/main.py`** — creates the FastAPI app and holds the four routes. Translates domain
  outcomes into HTTP: 201 created, 302 redirect, 404 unknown, 409 alias taken, 410 expired.
- **`app/schemas.py`** — Pydantic request/response models. `CreateLinkRequest` carries
  `url: HttpUrl` and optional `alias: str` constrained to `^[A-Za-z0-9_-]{3,30}$`; this is
  where requirement 4 is enforced.
- **`app/codes.py`** — generates auto codes (7 characters from `[a-z0-9]`, `secrets.choice`)
  and holds the reserved-word list (`links`, `health`, `docs`, `redoc`, `openapi.json`) so an
  alias can never shadow a real route.
- **`app/store.py`** — every SQL statement in the project: `insert_link`, `get_link`,
  `increment_hits`. Raises `AliasTaken` on the unique-constraint violation so the route layer
  never sees `sqlite3` exceptions.
- **`app/db.py`** — opens a connection per request (`sqlite3.connect(path)`,
  `row_factory=sqlite3.Row`, foreign keys and WAL on), and applies `schema.sql` at startup if
  the table is absent. Per-request connections keep SQLite off the shared-thread problem
  without a pool.
- **`app/config.py`** — `Settings` read from the environment: `DATABASE_PATH`
  (default `./shortener.db`), `BASE_URL` (default `http://127.0.0.1:8000`, used to build the
  `short_url` in responses), `LINK_TTL_HOURS` (default 24; fixed per PRD, an env var only so
  tests can shorten it).
- **`app/clock.py`** — a `now()` function exposed as a FastAPI dependency. Requirement 5
  (24-hour expiry) must be testable without waiting a day or sleeping; tests override this
  dependency to move time forward. Rejected: `freezegun` (extra dependency for one seam).
- **`tests/`** — pytest suite, one module per journey.

## Data

One table, `links`:

| Column | Type | Notes |
| --- | --- | --- |
| `code` | TEXT PRIMARY KEY | The short code, auto-generated or the custom alias. Uniqueness here is what produces the 409 in requirement 3. |
| `target_url` | TEXT NOT NULL | The exact original URL, stored as submitted so the redirect matches it exactly. |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC. |
| `expires_at` | TEXT NOT NULL | `created_at + LINK_TTL_HOURS`, written at creation. Comparing it to `now()` on read implements requirement 5 with no scheduler. |
| `hits` | INTEGER NOT NULL DEFAULT 0 | Requirement 7. Incremented with `UPDATE ... SET hits = hits + 1`, which is atomic in SQLite. |

Rows are never deleted, so an expired code stays retired and is never re-issued (PRD default).
No second table: usage tracking is a count, not an event log, per "Not in the first version".

## Journeys

**Create a link** — `POST /links` with `{"url": "...", "alias": "..."?}`. Pydantic validates
the URL and alias shape (invalid → 422, a 400-level error per requirement 4). If an alias is
given it is checked against the reserved words, then inserted; a primary-key collision
returns 409 and nothing is written. With no alias, `app/codes.py` generates a code and
`store.insert_link` retries on collision (up to 5 attempts). Response 201:
`{code, short_url, target_url, created_at, expires_at, hits}`.

**Follow a link** — `GET /{code}`. Unknown code → 404. Found but `expires_at <= now()` → 410
with a "link expired" message. Otherwise `hits` is incremented and a 302 to `target_url` is
returned. 302, not 301, so browsers do not cache a link that dies within a day.

**Check usage** — `GET /links/{code}` returns the same JSON body as creation, including the
current `hits`, without incrementing it. Expired → 410, unknown → 404.

**Restart** — the SQLite file is the only state; on start `app/db.py` applies the schema if
needed and existing rows keep working until their `expires_at` (requirement 8).

## Sign-in

None. The PRD states no authentication in v1, so every endpoint is open and no user or
ownership data is stored.

## Decisions

- **Expiry checked on read, not swept by a job.** Rejected: a background task or cron
  deleting expired rows — it adds a moving part and the PRD wants expired codes retired
  permanently anyway, so the rows should stay.
- **410 for expired, 404 for unknown.** The PRD leaves this to the builder; distinct codes
  cost nothing and make the test for requirement 5 unambiguous. Rejected: 404 for both.
- **Time injected via a FastAPI dependency.** Rejected: a library that patches the clock
  globally, and `time.sleep` in tests (would make the suite take 24 hours).
- **Connection per request instead of a module-level connection.** Rejected: one shared
  connection with `check_same_thread=False` — it works only while the app is single-threaded
  by accident.
- **Codes are 7 random lowercase-alphanumeric characters.** Rejected: base62 of a sequential
  ID (lets anyone walk the whole link table).
- **`short_url` built from a `BASE_URL` setting.** Rejected: deriving it from the inbound
  `Host` header, which breaks the moment there is a proxy.
- **422 for malformed input rather than 400.** FastAPI's default for a validation failure; it
  is a 400-level error as requirement 4 asks. Alias conflicts stay a deliberate 409.

## Verification

Install and run the suite:

```
pip install -e ".[dev]"
pytest
```

The suite is the primary evidence: it covers create, redirect to the exact original URL,
hit count 0 → 3, expiry (clock override), invalid URL, alias conflict, unknown code, and
persistence across a re-opened database file — i.e. every numbered requirement in the PRD.

Manual check of the live app:

```
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

then `POST /links` with `{"url": "https://example.com/some/long/path?query=1"}`, follow the
returned `short_url` in a browser (lands on example.com), and `GET /links/<code>` to see
`hits` at 1. Interactive docs at `/docs`.

The automated gate below is GET-only, so it checks that the app starts, serves, and returns
the right errors for codes that do not exist; the create-and-redirect journey is covered by
pytest.

```verify
start: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
ready: http://127.0.0.1:8000/health
check: GET http://127.0.0.1:8000/health 200
check: GET http://127.0.0.1:8000/docs 200
check: GET http://127.0.0.1:8000/openapi.json 200
check: GET http://127.0.0.1:8000/zzzzzzz 404
check: GET http://127.0.0.1:8000/links/zzzzzzz 404
```

## Open questions

- **Where this runs and behind what hostname.** No deployment target was given. Default
  applied: it runs as a single uvicorn process with a local SQLite file, and `BASE_URL` is an
  environment variable so the deployed hostname needs no code change. No Dockerfile or deploy
  config is part of v1; say the word and it becomes one task.
- **Traffic and latency targets.** None given (PRD open question). Default applied: none
  assumed, single instance. If more than one instance is ever needed, the SQLite file is the
  thing that must change, not the API.
- **Alias case sensitivity.** Not stated. Default applied: codes are case-sensitive, matched
  exactly as stored; `My-Link` and `my-link` are different links.
