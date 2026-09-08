# Not used by the running app

Everything under this folder is dead code that was never wired into
the app that actually runs (`backend/main.py`, a FastAPI app started
by `main.py` / `app.py` / `run_platform.py` at the project root, all
of which import `backend.main:app`). Nothing here is imported by
anything else in the project. Kept in case it has design/reference
value, but it should NOT be confused with the live backend.

## node_backend/

A parallel, unfinished Node.js/Express + PostgreSQL API (controllers,
routes, JWT auth, a `schema.sql`) that lived inside `backend/`
alongside the real Python backend, with its own `package.json` and a
`.env` full of Postgres/JWT config that no Python file reads. If you
run `npm install && npm start` in here you'll get a second, unrelated
server -- it doesn't share data or routes with the FastAPI app, and
the frontend (`templates/`, `static/script.js`) only ever talks to the
FastAPI app on port 8000.

## root_src_duplicate/

An older, stale copy of `matching_engine.py` (plus its `__init__.py`)
that used to live at the project root as `src/`. `backend/main.py`
imports `from src...`, and Python resolves that to `backend/src/`
(inserted into `sys.path` ahead of the project root), so this copy was
never actually executed -- but it's an easy trap to edit the wrong
file. It has real behavioral differences from the live version in
`backend/src/matching_engine.py` (no vegan check, no soft pickup-radius
allowance, strict food-type matching instead of the flexible fallback
matching) so don't merge it back in without reconciling those.
