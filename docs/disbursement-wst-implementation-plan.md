# Disbursement work stations — implementation plan

> **Transient.** This file tracks one branch's remaining work. Delete it when the last
> task lands; the decisions it refers to live in `docs/adr/` and the `CONTEXT.md` files,
> which are permanent.

Branch: `16.0-add-disbursement_wst`

## Where things stand

The disbursement request used to advance through a `state` selection that core and two
bridge modules each extended (`selection_add`), across four parallel status fields and
about thirty-nine values. It now walks a **route** of **work stations**: core keeps a
closed six-value `state` (`draft → submitted → signed → in_progress → done / cancel`),
and the station a request currently sits at is `station_code`.

Already on the branch:

- `disbursement_wst` — the engine: `disbursement.station`, `disbursement.route(.line)`,
  `disbursement.step`, and the extension of `disbursement.request` that walks them.
- Four stations: `disbursement_wst_verify`, `_approve_finance`, `_approve_rector`, `_bill`.
- Core collapsed: `pipeline_status`, `display_status`, `approval_state`, the approver
  stamps and the `disbursement.request.signature` model are gone; the signature snapshot
  moved onto `disbursement.step`.
- The three legacy return paths (return-for-correction, return-to-verification,
  return-to-source) are gone, with the `disbursement.return.source.mixin` and the
  `returned` state each of the four source bridges added to its own model.

### ⚠ The payment phase is currently dead

`disbursement_finance_kmitl` still gates on state values that no longer exist. It
installs (the breakage is all at runtime) but nothing past the billing station works.
Fixing this is **Task 3**.

| File | Line | Problem |
|---|---|---|
| `models/disbursement_request.py` | 348, 374, 443, 522, 546, 686 | `state != "bills_posted"` / `"payment_audited"` / `"payment_authorized"` / `"paid"` — values removed from the selection, so these guards are always true |
| `models/disbursement_request.py` | 354, 380 | writes `"state": "payment_audited"` / `"payment_authorized"` — not in the selection, `ValueError` |
| `models/disbursement_request.py` | 359, 385 | calls `_stamp_signature()`, deleted with the signature model |
| `models/account_move.py` | 72, 95 | reads/writes `"paid"` / `"cleared"` |
| `views/disbursement_queue_views.xml` | — | 5 references to dead values (silently-false `attrs`, so buttons and queues never appear) |
| `views/disbursement_request_views.xml` | — | 19 references, same |

## The rules this work follows

Read these before touching anything; they are short.

| Rule | Where |
|---|---|
| Stations replace the shared state vocabulary | `disbursement_wst/docs/adr/0001` |
| Stations never depend on each other — ordering is declared by **code string**, not xmlid | `disbursement_wst/docs/adr/0002` |
| The head-of-unit signature is not a station | `disbursement_wst/docs/adr/0003` |
| **Data lives in the bridge, verbs live in the station** | `disbursement_wst/docs/adr/0004` |
| **A station is removable, but not while it holds work** | `disbursement_wst/docs/adr/0005` |
| **Core declares the facts downstream asks about** | `disbursement/docs/adr/0003` |

Vocabulary: `disbursement_wst/CONTEXT.md` and `disbursement/CONTEXT.md`. Use those words
in code and commit messages — *station*, *route*, *step*, *forward*, *divert*, *detour*,
*bridge*, *settled*.

**No migrations.** The deployment is UAT-only and prod will be a fresh install, so
moving fields, models and groups between modules and renaming them is free. Do not write
`migrations/`, do not write backfill SQL. Test on a fresh database.

## A station module, for reference

`disbursement_wst_approve_rector` is the template. Thirteen files, thirty-eight lines of
Python:

```
__manifest__.py                  depends: ["disbursement_wst", <bridge if any>]
data/disbursement_station.xml    one disbursement.station record
data/disbursement_route_line.xml one line appended to disbursement_wst.route_default
data/mail_activity_type.xml      the Todo pushed to the station's group
models/disbursement_request.py   _station_check / _station_enter / _station_complete
security/security.xml            the station's own group
views/disbursement_request_views.xml   its button, its work queue
i18n/th.po · CONTEXT.md
```

---

# Task 1 — Make stations removable

**Why first:** it changes `disbursement.step`'s schema, which every station added later
depends on. Doing it after Task 3 means revisiting four new modules.

Branch: `16.0-imp-disbursement_wst-removable-stations`

### What to change

**`disbursement_wst/models/disbursement_step.py`**

- `:25` `station_id` → `ondelete="set null"` (today `"restrict"`, which is what makes a
  station permanently un-uninstallable once one request has passed it).
- `:28` `station_code` → plain `fields.Char(index=True)` written in `create`, **not**
  `related="station_id.code"`. A stored related field is still cleared when its source
  goes null, which would blank the history.
- Add `station_name = fields.Char()` and `is_signature = fields.Boolean()`, both written
  at create from the station.
- `:138` `_stamp` currently reads `self.station_id.is_signature`; read the step's own
  copy instead.

**`disbursement_wst/models/disbursement_request.py`**

- `:67-73` `_compute_signature_step_ids` filters on `s.station_id.is_signature`; filter
  on the step's own `is_signature`. Without this, reprinting an old ใบขอเบิก after an
  uninstall silently drops a signature cell.

**`disbursement_wst/models/disbursement_route.py`**

- `:78` route line `station_id` → `ondelete="cascade"`. A route line naming a station
  that no longer exists is meaningless, and `restrict` here would block the uninstall
  for a configuration row.

**`disbursement_wst/models/disbursement_request.py`** — add the guard helper:

```python
def _wst_station_in_use(self, code):
    """Requests parked at ``code`` right now. Empty means the station can go."""
    return self.search([("station_code", "=", code)])
```

**Each of the four station modules** — add `hooks.py` and wire `uninstall_hook` in the
manifest:

```python
def uninstall_hook(env):
    parked = env["disbursement.request"]._wst_station_in_use("approve_rector")
    if parked:
        raise UserError(_(
            "Cannot remove this work station: %s request(s) are waiting at it: %s. "
            "Send them on first.",
            len(parked), ", ".join(parked.mapped("name")),
        ))
```

**Data files** — `data/disbursement_station.xml` in each station module: `noupdate="1"`
→ `noupdate="0"`. A station is code, nobody may edit it, so there is no user edit to
protect, and renaming one has to actually reach an installed database. Leave
`data/disbursement_route_line.xml` and `disbursement_wst/data/disbursement_route.xml` at
`noupdate="1"` — those are an admin's configuration.

### Done when

- Install everything, walk a request to `done`, print the PDF, then uninstall
  `disbursement_wst_approve_finance`: the old steps still show their station name, and
  the PDF prints the same number of signature cells.
- With a request parked at a station, uninstalling it raises and names the request.

---

# Task 2 — Stations are code, routes are configuration

Branch: `16.0-imp-disbursement_wst-stations-are-code`

- `disbursement_wst/security/ir.model.access.csv:3` — the manager row for
  `disbursement.station` is `1,1,1,1`; make it `1,0,0,0`. Nobody creates a station
  through the UI: a station with no module behind it has no handler, so it would be a
  step that does nothing.
- Delete `disbursement_wst/views/disbursement_station_views.xml` (tree, form, action, and
  the `Work Stations` menu at `:49`) and its manifest entry.
- `disbursement_wst/views/disbursement_route_views.xml` — the route line's `station_id`
  gets `options="{'no_create': True}"`.

Routes stay admin-editable, including `condition_domain` and the ordering constraint
(`_check_station_order`).

### Done when

A manager has no Work Stations menu, and `env["disbursement.station"].create({...})` as
a manager raises `AccessError`. Routes are still editable.

---

# Task 3 — The payment phase (un-breaks the branch)

Branch: `16.0-add-disbursement_wst-payment-stations`

Four new station modules, each `depends: ["disbursement_wst", "disbursement_finance_kmitl"]`.
There is deliberately **no shared base module**: the data they share lives in the bridge
(ADR-0004), so there is nothing left for a base to hold.

| Module | code | seq | requires_codes | group (move from the bridge) | Todo |
|---|---|---|---|---|---|
| `disbursement_wst_payment_audit` | `payment_audit` | 50 | `bill` | `group_disbursement_payment_auditor` | `mail_activity_dr_to_audit` |
| `disbursement_wst_payment_authorize` | `payment_authorize` | 60 | `payment_audit` | `group_disbursement_payment_authorizer` | `mail_activity_dr_to_authorize` |
| `disbursement_wst_pay` | `pay` | 70 | `payment_authorize` | `group_disbursement_payment_finance` | `mail_activity_dr_to_pay` |
| `disbursement_wst_clear` | `clear` | 80 | `pay` | `accounting_kmitl.group_accounting_kmitl_user` | `mail_activity_dr_to_book` |

Groups are at `disbursement_finance_kmitl/security/security.xml:15,23,31`; activity types
at `disbursement_finance_kmitl/data/mail_activity_type.xml:7,16,25,38`. Moving them
across modules is free (no migrations).

### Move out of `disbursement_finance_kmitl/models/disbursement_request.py`

| → | Methods |
|---|---|
| `_payment_audit` | `_ensure_payment_lines` · `_prepare_payment_line_vals` · `_apply_subject_defaults` · `_payable_payment_lines` · `_check_payment_classification` · `action_audit` (becomes `_station_check` + `_station_complete`) |
| `_payment_authorize` | `_try_create_payments` · `_create_payments` · `action_authorize` · `action_create_payment` |
| `_pay` | `_hand_over` · `_try_hand_over_when_all_paid` · `action_confirm_paid` · `action_submit_payments`; and `account_payment.py:45,54,66,78,85` `_try_hand_over_requests` |
| `_clear` | `account_move.py:95`, the `_post` override that marks the request cleared |

### Delete outright — do not move

- `payment_auditor_id` · `payment_audit_date` · `payment_authorizer_id` ·
  `payment_authorize_date`. These are `disbursement.step.acted_by_id` / `acted_date`,
  filtered by `station_code`. Ten view references have to be repointed at `step_ids`,
  including the two "work I audited" domains in `views/disbursement_request_views.xml`.
- `_payment_batch` and `action_audit_batch` / `action_authorize_batch` /
  `action_submit_payments_batch` — the engine's `action_act_batch()` replaces all three.
- The `write()` interception that reacts to `state == "bills_posted"` — `_station_enter`
  is the hook for that now.
- The two `_stamp_signature()` calls (`:359`, `:385`) — the step stamps itself.

### Keep in the bridge

`disbursement.payment.line` (the whole model) · `payment_subject_id` ·
`account.payment.disbursement_request_id` · `account.move.payment_disbursement_request_id`
· the bank-export link · the voucher report. `disbursement_cash_movement_kmitl` extends
`disbursement.payment.line`, which is the plainest proof it is data and not a verb.

### Also

`disbursement_cash_movement_kmitl/views/` xpaths into
`disbursement_finance_kmitl.view_disbursement_request_form_inherit_finance`; that view is
being rewritten here, so its anchors need checking.

### Done when

`disbursement_finance_kmitl/tests/test_payment_workflow.py` (620+ lines, covers
audit → authorize → pay → clear) passes against the four stations. It is the safety net
for this task — repair it, do not replace it.

---

# Task 4 — Forward and divert

Branch: `16.0-imp-disbursement_wst-forward-and-divert`

Today a station has one press. It gets two: **Forward** (ส่งต่อ) hands the request to the
next station on its route; **Divert** (ส่งไปยังสถานี) says something is wrong and names
the station that must look at it. They are recorded differently on purpose — counting
diverts is how you find out which station keeps sending work back.

### `disbursement.step`

- `disposition` → `forward` / `divert` (today: `complete`).
- `origin` → `route` (seeded from the route line) / `insert` (diverted here) / `resume`
  (the diverting station, re-queued behind the detour).
- `inserted_by_step_id` — self many2one, which step caused this one.

### Insertion

Modelled on `agx_sarabun`'s `_do_direct` (`agx_sarabun/models/sarabun_routing_step.py`),
which inserts a step after the acting one and shifts the rest of the chain down. Station
X at sequence *n* diverts to Y:

1. stamp `s_x` done with `disposition = "divert"` and the reason
2. `_shift_steps_from(n + 1, by=2 if come_back else 1)`
3. create Y at *n+1*, `origin="insert"`, `inserted_by_step_id = s_x`
4. if `come_back`: create X again at *n+2*, `origin="resume"`
5. `_advance()`

So `come_back` gives `X → Y → X → (route continues)` and without it `X → Y → (route
continues)`. No resume pointer, no extra state — two creates and a renumber.

Check the target's `requires_codes` against the request's own completed steps before
inserting: diverting into `bill` before the budget is committed must be refused.

### UI

Two header buttons gated on `can_act`; a wizard for divert with `station_id` (required,
excluding the current station), `come_back` (boolean, default True) and `note`
(required). Batch in the list view stays forward-only — a divert target is a per-request
judgement.

### Watch out

`come_back` means a station can appear twice among the completed steps. The signature
block must print the **latest done step per station**, not every one, or a request that
detoured gets two signature cells for the same officer.

---

# Task 5 — The billing station owns its verbs

Branch: `16.0-imp-disbursement_wst_bill-own-the-verbs`

Move from `disbursement_accounting_kmitl/models/disbursement_request.py` into
`disbursement_wst_bill`: `_create_bill` (`:95`), `_create_bills` (`:114`),
`_prepare_bill_vals` (`:141`), `_prepare_bill_line_vals` (`:156`), `action_create_bill`
(`:177`).

Keep in the bridge: `bill_ids`, `account.move.disbursement_request_id` and its snapshot
fields, `_related_move_domain`, `action_view_move_lines`, `action_view_related_moves`,
the `action_cancel` guard, and the `_post` override that raises `_on_bills_posted`.

`disbursement_cash_revenue_handover` overrides `_create_bill()`
(`models/disbursement_request.py:22`) and currently depends on
`disbursement_accounting_kmitl`; it moves to depending on `disbursement_wst_bill`. That
is the honest shape — there is no handover to draw if there is no billing station — and
Odoo will uninstall it along with the station rather than leaving a `super()` call with
nothing under it.

### Optional, while in here

`_prepare_bill_vals(self, partner, partner_bank, invoice_lines)` is parameterised by
*today's* grouping. If bills ever need splitting by anything other than partner, the
signature changes and every override breaks at once. Passing the `lines` recordset and
letting the method derive partner and bank is strictly more information and a signature
that survives a new grouping dimension.

### Done when

`disbursement_cash_revenue_handover/tests/` passes — it calls `action_create_bill()` at
fifteen points and is the regression net for this task.

---

# Task 6 — The settled fact

Branch: `16.0-imp-disbursement-settled-fact`

Four modules outside the disbursement family still list disbursement state values,
including values owned by bridges they do not depend on:

| File | Line |
|---|---|
| `kmitl_project_disbursement/models/kmitl_project.py` | 7, 12 — used in **search domains** at 60, 103, 127 |
| `procurement_plan_disbursement/models/procurement_plan.py` | 4, 6 — used in Python `filtered` at 54, 55, 69, 82 |
| `purchase_request_approval_disbursement/models/purchase_request_approval.py` | 140-144 — dead keys in `_DR_STATE_TO_BILLING_STATUS` |

Per `disbursement/docs/adr/0003`:

- Add `is_settled` to core `disbursement.request` — `fields.Boolean(default=False,
  store=True)`. It must be a **stored field, not a helper method**: `kmitl_project`
  uses it inside `search()`, where a method cannot go.
- `disbursement_finance_kmitl` computes it true once the money has left.
- "Has it committed budget" needs nothing new — `budget_consumed_amount > 0` is already
  core's and already stored. Both downstream `DONE_STATES` tuples mean exactly that.

`advance_payment_disbursement/models/advance_payment_usage_line.py:25` is a `related` to
`state`, not a hardcoded tuple. It still works; relabel it if you like.

---

# Testing

There is no CI on this repository (`tests` and `pre-commit` workflows are disabled on
purpose) and no module ships a `.pot`, so i18n is edited by hand and nothing enforces
the checks. Run them locally.

### A fresh install against your worktree

The doodba checkout lives at `~/workspace/kmitl-odoo` and bind-mounts
`odoo/custom/src/kmitl`. To test a worktree instead, mount it over that path:

```bash
docker inspect kmitl-odoo-odoo-1 --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -v '^$' | grep -vE '^(PGDATABASE|PATH)=' > /tmp/wst_env.txt
echo "PGDATABASE=wst_check" >> /tmp/wst_env.txt
docker exec kmitl-odoo-db-1 psql -U odoo -d postgres -c "CREATE DATABASE wst_check OWNER odoo;"

docker run -d --name wst_install --network kmitl-odoo_default --env-file /tmp/wst_env.txt \
  -v ~/workspace/kmitl-odoo/odoo/custom:/opt/odoo/custom \
  -v ~/workspace/kmitl-odoo/odoo/auto:/opt/odoo/auto \
  -v <YOUR-WORKTREE>:/opt/odoo/custom/src/kmitl:ro \
  kmitl-odoo-odoo \
  odoo -d wst_check -i disbursement_wst_verify,disbursement_wst_approve_finance,\
disbursement_wst_approve_rector,disbursement_wst_bill,disbursement_sarabun,\
disbursement_assignment_kmitl,disbursement_finance_kmitl \
  --stop-after-init --without-demo=all --log-level=warn
```

Swap `-i` for `-u ... --test-enable --test-tags '/module,...'` to run the suites. Do not
use `--rm`: the container is where the log is.

### Known noise in that environment

Ten tests in `disbursement_assignment_kmitl` fail there with *"Unable to send message,
please configure the sender's email address"*. That is the throwaway database, not the
code — `oca_init_test_database` seeds what a bare `CREATE DATABASE` does not. Confirm by
running the same suite against a database built from the commit before yours.

### Checks nothing else runs

- `pre-commit run --all-files` — with `SKIP=oca-gen-addon-readme`, which otherwise drops
  a 25 MB pandoc package in the repository root.
- Every hand-edited `.po` entry needs its **whole** comment block, `#. module: <addon>`
  included. Odoo's `PoFileReader` matches `module: ` against the extracted comment with
  no guard, so one entry missing that line raises `AttributeError` for the entire file —
  during `lang_install`, which takes the registry down with *"Failed to initialize
  database"* and a traceback pointing at `translate.py` rather than at your module.
  `msgfmt -c` does not catch it. Sweep with Odoo's own reader:

  ```python
  from odoo.tools.translate import PoFileReader
  for f in pathlib.Path(root).rglob("i18n*/*.po"):
      with open(f, "rb") as fh:
          for _ in PoFileReader(fh):
              pass
  ```

### Repair tests, do not add files

The house rule is to fix existing suites rather than write new ones. The nets that matter
here: `disbursement_wst/tests/` (engine and signature block),
`disbursement_finance_kmitl/tests/test_payment_workflow.py` (Task 3),
`disbursement_cash_revenue_handover/tests/` (Task 5),
`disbursement_assignment_kmitl/tests/`.

Note that `disbursement_wst/tests/test_two_approver.py` trims the standard route to its
three stations in `setUpClass`. It walks them end to end, so any station module installed
alongside would otherwise append a line to the same route and leave the request short of
`done`. Keep that in mind when adding stations.

## Loose ends, not design work

- `disbursement/tests/` holds only an empty `__init__.py`; core has no tests at all since
  its suites moved to `disbursement_wst`.
- `purchase_order_disbursement/models/purchase_order.py:3` imports `UserError` and
  `ValidationError` without using them. Pre-existing, not from this work.
