# Receipt KMITL — Development Hand-off

Implementation spec for the changes agreed in the grill session. Read alongside
`CONTEXT.md` (glossary) and `docs/adr/0001..0003`.

**Pre-production module** — not deployed yet ([[kmitl-deployed-in-production]] does
NOT apply here). No migration scripts, no manifest version bump. Model/table
renames are done directly (dev DBs are reinstalled/`-u`, not data-migrated).
Two selection values removed by this hand-off, `kmitl.receipt.state='to_submit'`
and `kmitl.payment.method.payment_type='other'`, are no longer valid and Odoo
will **not** remap existing rows for you (`ir_model._process_ondelete` skips
selections on base fields) — once this module ships to a database with real
data, a migration script must remap both before upgrade.

Work is in three deliverables, implement in this order:

1. **Base `receipt_kmitl`** (items A–E below)
2. **`receipt_kmitl_exception`** (item F) — depends on base
3. **`receipt_kmitl_operating_unit`** + **`receipt_kmitl_operating_unit_access_all`** (item G)

---

## A. Rename `department_id` → `department_analytic_id` (ADR none; pure rename)

Both `kmitl.receipt` and `kmitl.receipt.remittance` (the renamed deposit).

- On `kmitl.receipt.remittance` (which carries no `analytic.mixin`): stays a
  **plain, required, `store=True` Many2one** to `account.analytic.account`,
  `domain=[("root_plan_id.code","=","departments")]`, source of truth for the
  running number and bundling.
- On `kmitl.receipt` the header now inherits `analytic.mixin` (Revision 4) —
  `department_analytic_id` is a `compute="_compute_analytic_id"` /
  `inverse="_inverse_department_analytic"` field, still `store=True,
  required=True, index=True`, but `analytic_distribution` is the source of
  truth it is derived from. See Revision 4 below and item B.
- Update every reference: `_get_receipt_sequence(rec.department_analytic_id, …)`,
  `action_confirm`, deposit/remittance pull + validate, and all views
  (`receipt_kmitl_views.xml` tree/form/search + `group_by`, remittance views).

## B. Receipt line — swap `analytic.distribution.mixin` → `analytic.mixin`

`models/receipt_kmitl_line.py`. ⚠️ Not a one-line swap — see
[[analytic-distribution-mixin-migration-crashes-at-load]]. Do it atomically:

- `_inherit = ["analytic.mixin"]`
- Declare **all 6** dimension fields yourself (the mixin defines none):
  `activity_analytic_id`, `department_analytic_id`, `fund_analytic_id`,
  `source_analytic_id`, `kmitl_project_analytic_id`, `procurement_plan_analytic_id`.
  Each: `compute="_compute_analytic_id"`, `inverse="_inverse_<x>_analytic"`,
  `domain=[("root_plan_id.code","=","<code>")]`, **all `store=False`**
  (including `department_analytic_id` — no search/group_by/report consumes it,
  and `store=True` causes `compute_sudo` inconsistency warnings in the registry
  plus stale values when `analytic_distribution` is cleared).
- `_analytic_keys = { "activities":"activity_analytic_id",
  "departments":"department_analytic_id", "funds":"fund_analytic_id",
  "sources":"source_analytic_id", "kmitl_project":"kmitl_project_analytic_id",
  "procurement_plan":"procurement_plan_analytic_id" }`  (a **dict**, never a method)
- 6 per-field inverses, each `self._update_analytic_distribution("<code>")`.
- Both directions must work: writing `analytic_distribution` (default context/import)
  → fields populate via the inherited `_compute_analytic_id`
  (`@api.depends("analytic_distribution")`); editing a field → JSON via inverse.
- View: `receipt_kmitl_views.xml` already lists 4 of them; add
  `kmitl_project_analytic_id` / `procurement_plan_analytic_id` as `optional="hide"`.
- Reference pattern: `purchase_request_budget/models/purchase_request.py`.

> **This is about the line's own dimension fields, which were never built** —
> `receipt_kmitl_line.py` still inherits plain `analytic.mixin` with no
> per-field declarations (see Deviations). The `store=False` /
> "no search/group_by/report consumes it" reasoning above does **not**
> generalize to `department_analytic_id` on the **header** — that one is
> `store=True` and load-bearing (remittance `child_of` pull, pivot row,
> search field, `group_by` filter — see Revision 4).

## C. Walk-in customer

Resolution helper is the single source of truth: `kmitl.receipt._default_partner_id`
(config param `receipt_kmitl.walkin_partner_id` first, else `ref('partner_walkin')`).

- **Settings menu "ลูกค้า Walk-In"** under Configuration, `groups="…manager"`:
  a `ir.actions.server` (model `res.partner`) whose code resolves the partner via
  `_default_partner_id()`, `raise UserError` if none, else returns an act_window
  dict: `res.partner`, `res_id=<resolved>`, `view_mode='form'`, `target='current'`.
- **Undeletable** — new `models/res_partner.py`, override `unlink()`: if any record
  in `self` equals the `_default_partner_id()` result → `raise UserError`
  (`"ไม่สามารถลบลูกค้า Walk-In ได้ เนื่องจากระบบใบเสร็จใช้งานอยู่"`). This is
  dynamic (B1): follows the config param, falls back to seed on fresh install, and
  releases the seed once the param points elsewhere. **Do not** guard `active`
  (archive is allowed).

## D. `kmitl.cash.deposit` → `kmitl.receipt.remittance` (ADR-0002)

Rename model + file (`models/receipt_remittance.py`, update `__init__`,
`_description`, security xmlids, views file, menu action). Rename `receipt.deposit_id`
→ `receipt.remittance_id` everywhere (model + form/search + pull logic).

**States** `draft → submitted → done` (+ `cancelled`) — rename `posted`→`done`:

- `action_pull_pending_receipts` — filter receipts by **`child_of`** the remittance
  department: `[("department_analytic_id","child_of", rec.department_analytic_id.id),
  ("state","=","confirmed"), ("remittance_id","=",False), …]`.
- `action_submit` (User) — validate each receipt's `department_analytic_id`
  **`child_of`** the remittance department; **stamp `date = fields.Date.context_today`**
  (the submission date); mint number; lock header.
- `action_done` (Treasury Officer) — replaces `action_post`; calls
  `rec.receipt_ids.action_post()` (creates JE per receipt, **not** sudo) and sets
  `done`.
- `action_cancel` — allowed from draft/submitted, **not** `done`; on cancel,
  **release receipts** (`remittance_id = False`).
- **Remove `submitted → draft`.** Reset-to-draft only from `cancelled` (empty).

**Sequence** — new helper, **per-FY only** (drop department):
- code `kmitl.receipt.remittance.<fy_be>`, prefix `RM/<fy_be>/`, `padding=4`,
  where `<fy_be>` is the **4-digit** Buddhist-era fiscal year of `remittance.date`
  (reuse `kmitl.receipt._get_fiscal_year_be`). Result e.g. `RM/2569/0001`.
- Receipts keep the existing per-(dept,FY) `_get_or_create_dept_fy_sequence` (`RC/…`).

**Detach mechanism**:
- Per-row button in the `receipt_ids` tree on the remittance form (works while the
  o2m is readonly). Method clears `receipt.remittance_id`, posts a chatter note on
  **both** remittance and receipt. Visible to `group_user` (covers both dept users
  and treasury officers, since treasury implies user).
- **One-click "แก้ไขใบเสร็จ"** on the receipt form, visible when
  `state == 'confirmed'` and `remittance_id == False`: does cancel→draft in one step
  so the detached receipt can be edited then re-confirmed (number preserved) and
  pulled into a later remittance.

## E. Security model (ADR-0001 + ADR-0003)

Replace the three role groups entirely.

- `security/security.xml`:
  - Tier (same `category_id`, hierarchical): `group_receipt_kmitl_viewer`
    (implies `base.group_user`) → `group_receipt_kmitl_user` (implies viewer) →
    `group_receipt_kmitl_manager` (implies user **and** treasury_officer).
  - `group_receipt_kmitl_treasury_officer` — **independent checkbox** (no tier
    `category_id`, per [[odoo16-independent-permission-checkbox-no-category]]);
    `implied_ids = [user, account.group_account_invoice]`.
  - **Delete** the old dept record rules and the central "see all" rules (ADR-0001;
    row scoping now lives in the OU module).
- `security/ir.model.access.csv` — rewrite:
  - viewer: **read** on `kmitl.receipt`, `kmitl.receipt.line`,
    `kmitl.receipt.remittance`, `kmitl.payment.method`, `account.analytic.account`,
    and **`account.account`** (so `account_id` renders / is selectable — ADR-0003).
  - user: full CRUD on receipt / line / remittance.
  - manager: + CRUD on `kmitl.payment.method`.
  - treasury officer: same doc access as user; `account.move` comes from
    `account.group_account_invoice`.
- `models/res_users.py` — **remove** `kmitl_department_ids`.
- `views/res_users_views.xml` — **remove** the "KMITL Receipt" page.
- Menus (`menus.xml`): root + operational menus → `…viewer`; Configuration →
  `…manager`. Add the Walk-In settings menu (item C).
- Button/field gating:
  - receipt `action_confirm`, remittance `action_submit` / detach / correct → `user`
  - remittance `action_done` → `treasury_officer`
  - receipt form **Accounting page / `move_id`** → `groups="…treasury_officer"`
    (prevents `account.move` access errors for non-treasury users — ADR-0003).
- `res_config_settings_views.xml` block → `groups="…manager"`.

## F. New module `receipt_kmitl_exception`

`depends = ["receipt_kmitl", "base_exception"]`. Pattern:
`purchase-workflow/purchase_request_exception` + `kmitl/kmitl_project` exception.

- `models/receipt_kmitl_exception.py`: `_inherit = ["kmitl.receipt","base.exception"]`;
  `test_all_draft_orders` (`@api.model`), `_reverse_field`, `action_draft` resets
  `exception_ids/main_exception_id/ignore_exception`, `action_confirm` →
  `if self.detect_exceptions() and not self.ignore_exception: return self._popup_exceptions()`
  else `super()`, and `_get_popup_action` returning this module's confirm action.
- `wizard/receipt_kmitl_exception_confirm.py`: `TransientModel`
  `_name="kmitl.receipt.exception.confirm"`, `_inherit=["exception.rule.confirm"]`,
  `related_model_id = M2o("kmitl.receipt")`, `action_confirm` per template.
- `wizard/…_view.xml`: act_window → `base_exception.view_exception_rule_confirm`.
- `data/exception_data.xml`: **1 example rule, `active=False`**, `model="kmitl.receipt"`,
  e.g. non-blocking check `if not self.partner_id: failed = True`.
- Scope: **`kmitl.receipt` only**, gated on `action_confirm` (not remittance).

## G. New modules — Operating Unit

**Base hook prerequisite** (do in base `receipt_kmitl`): refactor `_create_move()`
so per-line vals go through `_prepare_move_line_vals(line)` (and a debit-line
helper), and the header dict goes through `_prepare_move_vals(line_vals)`, giving
the OU module clean override points for both header and line stamping.

**`receipt_kmitl_operating_unit`** — `depends = ["receipt_kmitl","operating_unit",
"account_operating_unit"]`. Pattern: `procurement_plan_operating_unit`.
- Add `operating_unit_id` (default `self.env["res.users"].operating_unit_default_get()`)
  to `kmitl.receipt` **and** `kmitl.receipt.remittance`. **Not** on payment method.
- Override `_prepare_move_line_vals` to stamp `operating_unit_id` onto the JE lines.
- `security/…security.xml`: one **global** `ir.rule` per model:
  `['|',('operating_unit_id','=',False),('operating_unit_id','in',user.operating_unit_ids.ids)]`
  (`perm_read` only, like the template).
- Views: add `operating_unit_id` to both forms.

**`receipt_kmitl_operating_unit_access_all`** — `depends =
["receipt_kmitl_operating_unit"]`. Pattern:
`procurement_plan_operating_unit_access_all`.
- `group_all_ou_receipt_kmitl` (category `operating_unit.module_operating_units`).
- `<function model="ir.rule" name="write">` rewriting both rules' `domain_force` to
  the `(1,'=',1) if user.has_group(...access_all...) else (0,'=',1)` form.

---

## Testing checklist

- [ ] Line: set `analytic_distribution` via default context → all 6 dimension
      fields populate; edit a field → JSON updates; clear distribution → field
      resets (all `store=False`).
- [ ] Receipt confirm mints `RC/<dept>/<fy2>/nnnn`; remittance submit mints
      `RM/<fy4>/nnnn` and stamps today's date; `date` is readonly after submit.
- [ ] Remittance pull/submit gather receipts from a **parent** department's whole
      subtree (`child_of`).
- [ ] Detach one receipt from a submitted remittance → remittance stays submitted,
      receipt returns to the confirmable pool; "แก้ไขใบเสร็จ" reopens it. Detach
      is blocked on `draft` and `done` remittances.
- [ ] Cancel a submitted remittance releases all receipts; `done` cannot be cancelled;
      `submitted` cannot reset to draft.
- [ ] Cancel/Reset to Draft buttons are hidden from Viewer (require `group_user`).
- [ ] Walk-in partner cannot be deleted (config-param target); menu opens it; archive
      still allowed.
- [ ] viewer read-only + sees app; user does everything but `done`; only treasury
      officer sees `done` + Accounting page; manager configures + can `done`.
- [ ] user (no accounting group) can pick `account_id` on a line and never hits an
      `account.move` access error on a posted receipt.
- [ ] Exception: example rule (activated) blocks/warns on `action_confirm`; ignore
      path works; `action_draft` clears it.
- [ ] OU: a user sees only their OU's receipts/remittances; access-all group sees all;
      posted JE lines carry `operating_unit_id`.

## Deviations from this spec

What actually shipped differs from the plan above in a few places:

- **No detach mechanism.** Item D's per-row detach button and `_get_or_create_dept_fy_sequence`-
  style per-row unlink were never built. Removing a receipt from a `submitted`
  remittance is instead done through the standard `many2many`-style widget on
  `receipt_ids` (the × on a row); `kmitl.receipt.write()` resets the receipt's
  state back to `draft` when `remittance_id` is cleared this way. See
  ADR-0002 (revised).
- **Approval stage added.** The workflow gained a `submitted → approved →
  posted` split (not just `submitted → done` from item D), with an
  `approver_id`, a mail activity scheduled on submit, and both `action_approve`
  and `action_reject` (whole-remittance, with a reason, back to `draft`).
  `posted` replaces the planned `done` state name.
- **Group renamed.** `group_receipt_kmitl_treasury_officer` from item E shipped
  as `group_receipt_kmitl_remittance_approver` — same independent-checkbox
  shape, different name (see CONTEXT.md).
- **Dimension implementation differs from item B — superseded by Revision 4.**
  Between Revision 3 and Revision 4 the 6 dimension fields lived as plain
  Many2one fields on the receipt **header**, with `analytic_distribution` a
  hand-built dict assembled from them (`_build_analytic_distribution`). As of
  Revision 4 the header itself inherits `analytic.mixin`:
  `analytic_distribution` is the source of truth, and the 6 fields are
  compute/inverse convenience fields around it (`department_analytic_id` /
  `source_analytic_id` stored, the other 4 not). `receipt_kmitl_line.py`
  still just inherits plain `analytic.mixin` with no per-field declarations
  of its own — the header's JSON is copied onto every line via
  `_sync_analytic_to_lines()`.
- **Receipt numbering is per-FY only.** `RC/<fy4>/nnnn` (e.g. `RC/2569/0001`),
  matching CONTEXT.md — the testing checklist item above that says
  `RC/<dept>/<fy2>/nnnn` is stale.

## Revision 2 — user-feedback grill (state/numbering/payment)

A second grill session on live user feedback removed the receipt's separate
`to_submit` state and reworked payment entry. `action_confirm` in the sections
above never shipped under that name (it shipped as `action_to_submit`/
"Confirm") and is now gone entirely:

- **`to_submit` merged into `draft`.** `kmitl.receipt` mints its
  `RC/<FY>/nnnn` number in `create()`, not on a confirm step; there is no
  `action_to_submit`/"Confirm" button any more. The header stays editable
  through `draft` and only locks once pulled into a remittance and submitted
  (`kmitl.receipt.remittance.action_submit`, unchanged). See ADR-0002's
  "Revision — receipt-side `to_submit` collapsed into `draft`" section.
- **Line validation is a model constraint**, not a submit-time check:
  `kmitl.receipt._check_lines` requires ≥1 line, every line to carry an
  `account_id`, and `amount_total > 0` (a single line's `amount` may be 0).
- **`account_fiscal_year_id` is gone.** `_get_fy_be()` always derives the
  Buddhist-era fiscal year from `date` via `_get_fiscal_year_be`; the
  `account_fiscal_year` module dependency was dropped from the manifest.
- **Payment entry redesigned.** `kmitl.payment.method.payment_type` dropped
  `other` (cash/cheque/transfer only). The receipt header now carries its own
  `payment_type` (selected before `payment_method_id`, which is domain-filtered
  to that type) plus `cheque_number`/`cheque_date`/`transfer_date`, required by
  type via `_check_payment_type_fields` and cleared on type switch via
  `_onchange_payment_type`. See CONTEXT.md's "Payment Type" entry.
- **`description`/`fund_analytic_id`/`source_analytic_id`/`activity_analytic_id`
  required only at the form view**, not on the model — so imports/API writes
  aren't blocked by them.
- **Remittance attachments can be downloaded as one combined PDF.**
  `kmitl.receipt.remittance._build_attachments_pdf()` interleaves a QWeb
  separator page per receipt with its `attachment_ids` (PDFs appended as-is,
  images converted via `odoo.tools.pdf.to_pdf_stream`, other mimetypes skipped
  and noted on the separator page); served by
  `GET /receipt_kmitl/remittance/<id>/attachments` (`controllers/main.py`).
- **Dashboard cards follow the list's active search filter.** 
  `get_receipt_dashboard(self, domain=None)` ANDs the caller's domain into each
  bucket; `receipt_dashboard.js` reads `env.searchModel.domain` and refetches
  on the search model's `update` event — no `search_default_*` added anywhere.

## Revision 3 — post-review fixes

A code review of Revision 2 found five defects, closed before deploy:

- **Payment**: `payment_type` on the receipt header intentionally duplicates
  `payment_method_id.payment_type` (type-first UX, per CONTEXT.md) — the form
  domain alone doesn't stop imports/API writes from pairing them up wrong, so
  `_check_payment_method_matches_type` (`@api.constrains`) closes that gap.
  The printed receipt and the summary report both read the receipt's own
  `payment_type`, never the method's.
- **Attachments PDF**: `_build_attachments_pdf()` renders the separator batch
  once and slices it by index, which only holds if every receipt's separator
  is exactly one page. It now checks the separator's page count against the
  receipt count and falls back to rendering each receipt's separator
  individually (still correctly ordered) when they don't match, plus caps the
  skipped-file list per receipt at 8 names (`MAX_SKIPPED_LISTED`) so long
  lists rarely trigger the fallback in the first place.

**Known follow-ups**:
- `receipt_kmitl_operating_unit`'s test suite is not part of base
  `receipt_kmitl`'s suite and was found broken (calling a removed method)
  only via manual grep, not by running `oca_run_tests` on the base module.
  Grep every add-on's tests whenever the base workflow changes.

## Revision 4 — post-review fixes + header analytic.mixin

A review of `16.0-imp-receipt_kmitl-user-feedback` found two more defects and
decided a third finding didn't need a code fix; the same round also reverted
Revision 3's header-fields deviation back to the item-B design (`analytic.mixin`
on the header, not just the line).

- **Summary Report no longer reads `account.fiscal.year`.** The ACL for that
  model was removed from `ir.model.access.csv` but the JS report still did an
  `orm.searchRead("account.fiscal.year", …)` on `onWillStart` — Viewer/User
  hit an `AccessError` opening the report. The Fiscal Year dropdown is gone;
  the default date range is now computed client-side as the current Thai
  fiscal year (1 Oct – 30 Sep), the same boundary `_get_fiscal_year_be` uses.
  Date From / Date To remain freely editable.
- **`_check_lines` constrains parameter fixed.** `@api.constrains("line_ids",
  "line_ids.amount", "line_ids.account_id")` — Odoo drops dotted params with a
  registry warning, so only `line_ids` actually triggered the constraint, and
  the web client omits `line_ids` from `create()` vals entirely when no line
  was ever touched — a lineless receipt could be saved after minting a
  number. Changed to `@api.constrains("line_ids", "amount_total")`:
  `amount_total` is a stored compute that always gets marked for recompute on
  `create` (and whenever a line's amount changes), so `_validate_fields`
  always re-runs this constraint.
- **`date` stays editable in draft after numbering.** Considered locking it
  once the fiscal-year-derived receipt number is minted (since changing
  `date` across a FY boundary would desync the number from the year it
  implies), but decided against a code change — accepted as a known,
  low-frequency edge case rather than adding another readonly-state rule.
- **Header returns to `analytic.mixin` (supersedes Revision 3's deviation).**
  `kmitl.receipt` now inherits `analytic.mixin` directly, per item B's
  original design. `analytic_distribution` is the source of truth;
  `department_analytic_id` / `source_analytic_id` stay `store=True` (the
  former `required=True` too) because both are load-bearing — remittance
  pull's `child_of` search, the pivot report row, the search-view field and
  `group_by` filter all need a real column. The other 4
  (`fund_analytic_id`, `activity_analytic_id`, `kmitl_project_analytic_id`,
  `procurement_plan_analytic_id`) stay `store=False`. `_compute_analytic_id`
  is overridden reset-first (clears all 6 convenience fields before
  delegating to the mixin) so a stored field doesn't keep a stale value when
  its dimension drops out of the JSON. Each of the 6 convenience fields
  carries its own single-field `@api.onchange` (stacked directly on its
  `_inverse_*` method) mirroring it into `analytic_distribution` immediately
  (the field inverses only fire on `write`), so the `analytic_distribution`
  widget and the pickers agree before the record is even saved. **Must stay
  one onchange per field** — an earlier version used one `@api.onchange`
  covering all 6 fields, looping `_update_analytic_distribution` over every
  code on every edit; each loop iteration reassigns
  `analytic_distribution`, and because the reset-first compute above fires
  on every reassignment, it wiped out the *other* fields' in-memory values
  before the loop ever got to read them. Only the first dimension processed
  (`departments`, first in `ANALYTIC_KEYS`) survived — Fund/Source/Activity
  silently failed to save picker → JSON in the UI. This was caught in
  manual testing, not by the test suite (the tests write field values
  directly, which goes through `write()`/the inverse, not onchange, so they
  never exercised the loop).
  `_sync_analytic_to_lines()` now just copies the header's
  `analytic_distribution` onto every line, and `write()` re-syncs on any of:
  the 6 convenience fields, `analytic_distribution` itself (direct
  write/import/RPC), or `line_ids` (a newly added line otherwise starts with
  no distribution at all) — the old trigger set (only the 6 fields) missed
  both of those cases.
- **`receipt_kmitl_summary_report`'s dimension filter no longer crashes.**
  `get_report_data` built `(field_name, "in", ids)` leaves straight off the 6
  convenience fields; once 4 of them went `store=False` (no `search=`),
  filtering by Fund or Activity raised `ValueError: Invalid field … in leaf`.
  `ReceiptReport` now inherits
  `accounting_kmitl_reports.dimension.filter.mixin` and builds the domain via
  `_kmitl_build_dim_leaves`, which targets `analytic_distribution` directly
  (with `child_of` expansion, and exact-match for the flat `sources` plan) —
  the same helper the Trial Balance / Aged Partner Balance reports use.
- **`receipt_kmitl_exception`'s blocking-exception constraint gained
  `analytic_distribution`** to its trigger field list, so a direct JSON write
  (import/RPC/widget) re-evaluates exception rules, not just writes through
  the 4 convenience fields.

## Revision 5 — post-review fixes

- **Receipt sequences are now `no_gap`.** `_get_receipt_sequence` /
  `_get_sequence` create an `ir.sequence` per fiscal year lazily but never
  set `implementation`, so it defaulted to `standard` — PostgreSQL
  `nextval()`, which does not roll back. Since Revision 4 mints the number
  in `create()` while `_check_lines` only fires later, on flush's
  recompute of `amount_total`, every save a constraint rejects burns a
  `RC/<FY>/nnnn` number — and `retrying()` can replay the same request up
  to 5 times, burning one each time. `no_gap` keeps its counter in the
  `ir_sequence.number_next` column, so it is returned by every rollback
  path, not just the one we happened to think of, and it brings this
  module in line with every other KMITL document sequence, which is
  already `no_gap`. The remittance sequence gets the same flag for
  symmetry (its number mints in `action_submit` after validation, so it
  was only ever at risk from retries). **Not done**: reordering `create()`
  to validate before minting — redundant once the counter is transactional,
  and it would only cover one path anyway. **Trade-off**: `_update_nogap`
  holds `FOR UPDATE NOWAIT` until commit, so concurrent saves within the
  same fiscal year serialize; `LOCK_NOT_AVAILABLE` is in
  `PG_CONCURRENCY_ERRORS_TO_RETRY`, so the framework retries automatically.
  **No self-heal** for sequences already created as `standard`: those rows
  are created from Python, have no xmlid, and survive `-u`/uninstall — on
  an existing database this fix has no effect. This was decided on a
  fresh-install assumption; an existing database needs its
  `kmitl.receipt.%` / `kmitl.receipt.remittance.%` sequences deleted
  manually, or a fresh database.
- **Line-level `analytic_distribution` is read-only in the tree.** This
  column was editable for users in `analytic.group_analytic_accounting`
  in the `editable="bottom"` tree, but `write()` pushes the header's
  distribution onto every line whenever `line_ids` is in vals — so a line
  edit was silently discarded in the same save. Header-is-source-of-truth
  is the design (Revision 4), so the affordance was a bug; the field is
  now `readonly="1"`, which the widget supports natively — no
  `force_save` needed, since the value is pushed server-side anyway.
- **Cheque/transfer dates print in the user's date format.** These used
  `t-esc`, printing raw ISO, unlike `o.date` in the same report. Switched
  to `t-field`, matching `o.date`. `cheque_number` stays `t-esc` — it's a
  `Char`.
- **Orphan attachments-separator report removed.** Splitting out
  `receipt_kmitl_attachment_viewer` left
  `receipt_kmitl/report/receipt_kmitl_attachments_separator.xml` behind;
  it was never in `data`, so it had no `ir.model.data` and nothing
  referenced its xmlid — removed with no impact, along with 9 stale
  entries in `th.po` (3 templates, 2 report actions, the
  `ดูไฟล์แนบทั้งหมด` button that moved to the inherited view, and the
  `… and %s more file(s)` string). All had empty `msgstr`, so no
  translation was lost, and nothing else in the file was touched.
