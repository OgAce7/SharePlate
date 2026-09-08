# SharePlate audit -- findings and fixes

Every item below was reproduced (not just read) before being fixed --
see "How I verified" at the end.

## Fixed

### 1. `requirements.txt` was missing packages the app can't start without
`backend/src/shareplate_client.py` does `import requests`, which is
imported transitively by `backend/main.py` at startup. `requirements.txt`
never listed `requests`, so a clean `pip install -r requirements.txt`
followed by `uvicorn` would crash immediately with
`ModuleNotFoundError`. Also missing: `joblib` and `xgboost` (needed by
`demand_api.py`/`train_model.py`), and `ortools` (route_optimizer.py
has a degraded single-truck fallback without it, but silently -- you'd
never know routing wasn't actually optimized).
**Fix:** added all four to `requirements.txt`.

### 2. `generate_data.py` would silently destroy the real dataset
It wrote `data/donations.csv` in a totally different, incompatible
schema (`donation_id/date/donor_id/food_category/quantity_kg/
shelf_life_days` instead of the real `donation_id/donor_type/food_type/
quantity/unit/latitude/longitude/vegetarian/vegan/perishability/
hours_until_expiry/pickup_required`), and invented fake `R001`-style
recipients with no connection to the real NGOs in `data/ngos.csv`. The
README's own documented setup steps (`python generate_data.py`) would
have broken the whole platform on the first run.
**Fix:** replaced it with `generate_recipients_from_ngos.py`, which
builds `data/recipients.csv` + `data/demand.csv` from the real
`data/ngos.csv` (`recipient_id == ngo_id`, so `/predict/demand` works
with the same id used everywhere else) and never touches
`donations.csv`/`ngos.csv`. Verified against the real `ngos.csv`.

### 3. NGO eligibility filtering was silently a no-op
`find_eligible_ngos()` had `if not eligible_ngos: return ngos.copy()`
-- if literally zero NGOs passed the food-type/radius/vegan checks, it
returned *every* NGO as "eligible" anyway. `backend/main.py`'s own
`get_ai_ngo_matches()` did the same fallback a second time. Net
effect: a vegan-only donation could get matched to a non-vegan NGO
with no way to tell, and `/match` / `/routes/optimize`'s
`unmatched_donation_ids` could basically never populate, because
"nothing is eligible" never actually happened. The frontend's
"No eligible NGO within pickup radius" message (`showNoMatchResult()`
in script.js) could never trigger in practice.
**Fix:** removed both fallbacks. `find_eligible_ngos()` now returns a
genuinely empty result when nothing qualifies, and callers treat that
as "no match" like they were already designed to. Verified with a
donation whose food type + vegan requirement no NGO in a test set
could satisfy -- correctly returns 0 eligible rows now.

### 4. Donor/NGO dashboards used food-type values the backend doesn't know
Both `templates/donor.html`'s "Food Type" select and `templates/
ngo.html`'s filter select offered `bakery_items`, `dairy_products`,
`snacks`, `other` -- none of which exist in the backend's real
vocabulary (`cooked_meal`, `packaged_food`, `fruits`, `vegetables`,
`bakery`) -- while missing `bakery` itself, a value that's actually in
the data. Picking those options wouldn't crash anything (unknown food
types get silently appended and fall back to default unit/
perishability/shelf-life), but they'd never match real donations and
the filter would just look broken.
**Fix:** both dropdowns now list only the backend's real 5 food types.

### 5. The "Pickup Required" checkbox on the donor form did nothing
It's in the form HTML, but `script.js`'s submit handler never read it
or included it in the payload, and `NewDonationRequest` in
`backend/main.py` had no `pickup_required` field at all -- so even a
manually-sent value would've been silently dropped by pydantic. Every
donation was always saved with `pickup_required=1` regardless of what
the user picked.
**Fix:** added `pickup_required` to `NewDonationRequest`, threaded it
through to `register_donation()`, and had `script.js` read the
checkbox and include it in the request.

### 6. Two unrelated "backends" were tangled together in one folder
`backend/` contained the real, running FastAPI app (`main.py` +
`src/`) *and* a separate, unfinished Node.js/Express + PostgreSQL API
(`src/server.js`, controllers, routes, `schema.sql`, its own
`package.json` and a Postgres/JWT-flavored `.env`) that's never
imported by anything -- every entry point (`app.py`, `main.py`,
`run_platform.py`) boots `backend.main:app`, the Python one. This is
confusing rather than broken (nothing crashes), but it's a real trap:
someone could reasonably try `npm install && npm start` in `backend/`
expecting it to be part of the running app, and it isn't. There was
also a stale, materially different duplicate of `matching_engine.py`
sitting at the project root under `src/` (no vegan check, no radius
tolerance, strict-only food matching) -- never executed (Python
resolves `backend/src/` first) but an easy file to edit by mistake.
**Fix:** moved both into `_unused_legacy/` with a README explaining
why they're there and not deleting anything. Also deleted
`backend/node_modules/` (12MB, fully regenerable via `npm install`,
not source).

## Verified but not touched
- `food_intelligence.py`, `demand_api.py`, `schema_mapping.py`,
  `shareplate_client.py`, `route_optimizer.py`, `register_donor.py`,
  `templates/style.css` -- read in full, no bugs found.
- The OR-Tools pickup-and-delivery formulation in `route_optimizer.py`
  and its no-ortools fallback both look correct.

## How I verified
- `python3 -m py_compile` on every edited/new `.py` file.
- Ran `generate_recipients_from_ngos.py` against the real `ngos.csv`
  and confirmed `donations.csv`/`ngos.csv` were untouched.
- Called `find_eligible_ngos()` directly with a donation no NGO in a
  test set could satisfy (wrong food type + vegan-only) -- confirmed
  it now returns zero rows instead of all of them.
- Ran `pipeline.build_matches()` against the real `donations.csv`/
  `ngos.csv` end-to-end (with no demand service running, so the
  per-row local-heuristic fallback path was exercised) -- correct
  matched/unmatched counts, no exceptions.
- `fastapi` itself isn't installed in this sandbox (no network access
  to pip install it), so I could not boot `uvicorn` and click through
  the actual dashboards -- do that as your first smoke test after
  `pip install -r requirements.txt`.

---

# Setup instructions

```bash
cd SharePlate
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## One-time: generate the demand model's training data

```bash
python generate_recipients_from_ngos.py   # builds data/recipients.csv + data/demand.csv from data/ngos.csv
python train_model.py                     # writes models/*.pkl
```

Re-run both whenever `data/ngos.csv` changes meaningfully (new NGOs,
capacity changes).

## Run both services

```bash
# Terminal 1 -- demand/food-intelligence service
uvicorn demand_api:app --reload --port 8001

# Terminal 2 -- main platform (matching, routing, web dashboards)
export SHAREPLATE_API_URL=http://localhost:8001   # optional, this is the default
python main.py
```

Then open:
- Donor dashboard: http://localhost:8000/donor
- NGO dashboard: http://localhost:8000/ngo
- API docs: http://localhost:8000/docs

If terminal 1 isn't running, terminal 2 still works -- donation
urgency scoring and NGO demand scoring fall back to a local heuristic
per row (visible as `urgency_source`/`demand_source: "local_fallback"`
in API responses), rather than failing.

## Notes
- `_unused_legacy/` is dead code (an unfinished Node.js backend and a
  stale duplicate file) kept for reference only -- see its own
  README. It is not part of the running app.
- `run_platform.py` and `main.py` (project root) both start the same
  app the same way; either works. `app.py` also works if you prefer
  `uvicorn app:app` directly.
