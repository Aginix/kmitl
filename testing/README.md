# KMITL ERP Load Testing

Locust load test that simulates KMITL staff using the Odoo 16 ERP: logging in,
browsing Discuss/Todo/purchase requests, running the `agx_approval` budget
approval flow, and browsing procurement/budget records.

**Owner**: whoever is running the current load-test round — see git blame on
`locustfile.py` for the last person to tune it.

## What's here

| File | Purpose |
|------|---------|
| `locustfile.py` | The test itself — one `KMITLUser` class with 7 weighted tasks |
| `users.csv` | 1000 real KMITL accounts (`No,Username,Email,Password`) used as login credentials |
| `requirements.txt` | Pinned Python deps (`pip install -r requirements.txt`) |
| `locust.conf` | Default Locust CLI options (host, users, spawn-rate, run-time) — picked up automatically when you run `locust` from this directory |
| `automation_create_employee_on_user_create.xml` | `base.automation` record: auto-creates an `hr.employee` (without `department_id`) whenever a `res.users` is created — see [Auto-create employee automation](#auto-create-employee-automation) |
| `Locust_*_failures.csv` | Failure reports exported from previous runs via the Locust web UI (not required to run the test — safe to delete) |

## Prerequisites

- Python 3.9+
- `pip install -r requirements.txt` (or reuse the checked-in `.venv`)
- Network access to the target Odoo server, and login credentials that actually exist in that server's database (see [Credentials](#credentials))

## Running

`locust.conf` already points at `http://localhost:16069`. For a real target,
override `host` on the command line or via env vars — the script reads these
at import time:

| Env var | Default | Purpose |
|---------|---------|---------|
| `ODOO_URL` | `http://localhost:16069` | Target server (also settable via `--host`) |
| `ODOO_DB` | unset | Database name. Leave unset to auto-detect via `/web/database/list` — only works if the server is filtered down to exactly one database |
| `ODOO_VERIFY_SSL` | `1` | Set to `0` to skip TLS verification (self-signed certs) |

> **Don't hardcode the real target server/db in these files.** Pass them via
> env var or `--host`/`--config-file` at run time instead — that keeps a real
> UAT/production hostname out of the repo. Example: keep a personal,
> gitignored `my.locust.conf` with your actual `host =` line instead of
> editing the committed `locust.conf`.

**Web UI** (interactive, good for a first run):

```bash
locust -f locustfile.py --host=https://<your-odoo-host>
```

Then open `http://localhost:8089` and set **Number of users** and **Ramp up**.

> Number of users caps how many of the 1000 CSV accounts get used
> concurrently — each spawned user claims the next credential round-robin.
> Setting Number of users above 1000 makes multiple simulated users share the
> same real account.

**Headless** (scripted runs, CI):

```bash
locust -f locustfile.py --host=https://<your-odoo-host> \
  --headless -u 50 -r 5 --run-time 5m --csv=results
```

## What the test simulates

Each simulated user logs in once (`on_start`), then repeatedly picks a task
weighted as follows:

| Task | Weight | What it does |
|------|--------|---------------|
| `agx_approval_flow` | 4 | Browse approval requests → **create** one (fixed category/budget/participants/lines, see below) → read it back → `action_to_verify` → `action_reserve_budget` |
| `open_discuss` | 3 | `POST /mail/init_messaging` (what the Discuss app calls on load) |
| `open_todo` | 3 | `search_read` on `mail.activity` filtered to `is_my_todo` |
| `open_purchase_request` | 3 | `search_read` on `purchase.request` |
| `browse_procurement_plan` | 2 | `search_read` on `procurement.plan` |
| `browse_budget_move` | 2 | `search_read` on `budget.move` |
| `browse_budget_commitment` | 2 | `search_read` on `budget.commitment` |

Every user waits a constant 2 seconds between tasks (`wait_time = constant(2)`).

## Configuration you'll need to change per target database

The `agx_approval` create step uses **hardcoded, environment-specific record
IDs** — they only work because they matched real records on the database
they were picked against. Re-point these constants at the top of
`locustfile.py` before running against a different database:

```python
BUDGET_ACCOUNT_ID = 152        # a real, appropriated budget.account
DEPARTMENT_ANALYTIC_ID = 474   # ] all 4 dimensions must match an existing,
ACTIVITY_ANALYTIC_ID = 264     # ] posted budget appropriation — the budget
FUND_ANALYTIC_ID = 249         # ] engine matches all dimensions or none
SOURCE_ANALYTIC_ID = 421       # ]
CATEGORY_ID = 1                # approval.category id (drives required city/period fields)
PARTICIPANT_PARTNER_IDS = [...]  # res.partner ids, valid for CATEGORY_ID's allowed partner types
LINE_PRODUCT_IDS = [...]         # product.product ids, must be in CATEGORY_ID's allowed_product_ids
```

There's no auto-discovery for these anymore (an earlier version mined them
from the database — dropped in favor of explicit, known-good values, since
mining silently skipped request creation whenever it came up empty).

## Known gotchas

- **Every simulated user hits the same budget account + dimensions.** Under
  enough concurrency, PostgreSQL will throw `serialization failed` /
  `could not serialize access due to concurrent update` on
  `action_reserve_budget` — that's Postgres's concurrency control rejecting a
  conflicting concurrent write, not a script bug. It's expected, and is
  itself a useful signal about how the budget engine handles contention on a
  single line. If you want to test a more realistic spread instead of a
  worst-case pile-up, add more `(account, 4 dims)` combinations and pick one
  per request instead of a single fixed tuple.
- **"Session Expired" right after login** usually means infrastructure, not
  this script — check that all app workers/replicas share the same session
  storage (filesystem or otherwise) and that their clocks are in sync (NTP
  drift can make a session look prematurely expired to a GC running on a
  different node). Also check whether **Number of users > 1000** — that
  makes multiple simulated users share one real account, which can trigger
  session invalidation if the server enforces single-session-per-user.
- **`owner_id` required field errors on `[Approval] Create request`** mean
  the logged-in account has no linked `hr.employee` — see the automation
  below.

## Auto-create employee automation

`automation_create_employee_on_user_create.xml` defines a `base.automation`
(Settings → Technical → Automation Rules) that fires on `res.users` creation
and creates a matching `hr.employee` — needed because `approval.request`
requires `owner_id`, which defaults from `env.user.employee_id`.

`department_id` is deliberately left commented out in the code — fill it in
before use:

```python
# "department_id": ...,  # TODO: set the target department here
```

To load it, either paste the `code` field into a new Automation Rule via the
UI (fastest, no install needed), or drop the file into a module's `data/` and
add it to `__manifest__.py` before upgrading that module.

## Credentials

`users.csv` contains **real KMITL login passwords**. Treat it like any other
credential file — don't commit it to a shared/public repo, and rotate the
accounts if it's ever exposed. It is currently untracked; keep it that way
(add `users.csv` to `.gitignore` if this directory gets committed).
