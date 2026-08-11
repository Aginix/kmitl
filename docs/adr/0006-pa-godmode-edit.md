# พจ.1 (PA) God-Mode edit — narrow field unlock in `to_approve` / `approved`, silent writes, PDF auto-regen, capped by budget commitment

พจ.1 currently locks every field the moment the record leaves `draft`
([ADR-0005]). Real-world corrections (typo, wrong vendor, off-by-one qty,
market price ≠ requested price) then require cancel-and-reissue — which
cascades to Sarabun, PO, DR. That cost is disproportionate whenever the
correction still fits inside the budget already reserved for the parent
พ.1.

**Decision.** Introduce a security group `group_pa_godmode` in a new addon
`purchase_request_approval_godmode`. Members may edit a narrow set of PA
fields while the record is in `to_approve` **or** `approved`, without
transitioning it out of that state.

Scope of the unlock:

- **Header (6):** `partner_id`, `procurement_type_id`, `procurement_method_id`,
  `payment_type`, `vat_included`, `tax_id`.
- **Line (3):** `product_qty`, `price_unit`, `name` on
  `purchase.request.approval.line`. Add/remove lines is disallowed;
  `product_id` and `product_uom_id` stay locked.
- **Not in scope:** `title`, `description` — treated as PR-sourced metadata
  that should stay in step with the parent purchase.request.

An `@api.constrains('amount_total', 'line_ids', ...)` guards the edit: the
sum of `amount_total` across all PAs on the same
`request_id.budget_commitment_id` in state `to_approve` / `approved` must
not exceed the commitment cap (`commitment.amount`). The check runs only
when `state ∈ (to_approve, approved)` **and** the writer holds the
god-mode group.

God-Mode writes are **silent**: `write()` on both `purchase.request.approval`
and `purchase.request.approval.line` injects
`tracking_disable=True, mail_notrack=True, mail_create_nolog=True` into the
context when the writer holds the group. No chatter entry, no field-diff
tracking, no follower notification is emitted — for either the direct edit
or any workflow button (Reset, Approve, Cancel) the god-mode user presses.

When a god-mode edit touches a field visible in the พจ.1 PDF (any of the
six header fields or `line_ids`), the same `write()` calls
`_regenerate_report_pdf()`: unlinks the stored `ir.attachment` named
`<pa.name>.pdf` on this PA and re-invokes the base `report_generate()` to
render a fresh one. This fixes the observed defect where the Sarabun
preview showed the corrected data (live QWeb re-render) but the Sarabun
export/print flow served the stale attachment snapshotted at
`button_to_approve()` time.

Downstream artefacts (PO already created, DR already raised, bill already
posted) are not re-derived — God-Mode is a surgical PA correction, not a
re-issue.

**Bug fix (bundled).** `purchase.request.approval` declared `title` and
`description` twice in the base module — once as own `fields.Char/Text`,
then again as `fields.Char(related="request_id.title")`. Python's second
declaration wins, so those fields silently delegated to the PR,
contradicting [ADR-0004](0004-pa-owns-copied-data.md). The god-mode PR
removes the `related=` re-declaration, restoring ADR-0004 intent —
`title`/`description` become true PA-own columns again. The
`_prepare_approval_vals` snapshot at PA creation already carries the
values from the PR, and no data migration is needed (feature is
pre-production).

## Considered options

- **Boolean toggle on `res.users` instead of a security group** — rejected.
  Groups are the OCA-native permission surface, are visible in the standard
  Access-Rights tab, participate in `groups="…"` in views and in `ir.rule`,
  and are auditable without a dedicated report. A per-user boolean gives
  the same effect but hides the fact that it is a permission.

- **Full cancel-and-reissue (spawn a new PA revision on correction)** —
  rejected. Cascades to Sarabun (a new หนังสือ must be routed), breaks the
  1 พ.1 ↔ 1 พจ.1 policy from [ADR-0002](0002-pa-separate-model.md), and is
  heavy for what is often a ≤10% price correction.

- **Include `title` / `description` in the god-mode scope by shadowing them
  in the addon** — rejected. Odoo's `_inherit` field-merge does not let a
  downstream addon override a base-module `related=` re-declaration cleanly;
  the base bug had to be fixed at the source (bundled here). Even after the
  base fix, we deliberately keep `title` / `description` out of the god-mode
  unlock scope — they are metadata sourced from the parent PR and any
  correction should originate there.

- **Include add / remove lines in the scope** — rejected. Empirically ≥95%
  of post-approval corrections are `product_qty` / `price_unit` / `name`
  edits; adding lines implies renumbering, re-triggering
  `_prepare_approval_vals` snapshotting, and a Sarabun diff surface too
  large for v1.

- **Model-level `write()` guard blocking non-god-mode writers on locked
  states** — rejected. OCA convention is that state-based edit locks live in
  views (`attrs="{'readonly': [('state', '!=', 'draft')]}"`), not in the
  model. A model guard would need explicit exceptions for every workflow
  that writes to non-draft PAs (`_on_sarabun_completed`, tier-validation
  actions, etc.) and for RPC integrations. We accept the trade-off that a
  non-god-mode user hitting `write()` directly via RPC is not blocked; the
  form is the enforcement surface.

- **Emit `tracking=True` on unlocked fields as the sarabun-branch signal**
  (the initial v1 design) — rejected in v2. The user requires god-mode
  edits to be silent (no chatter, no notification). `tracking=True` would
  fire chatter entries on every field diff. Instead, silent writes suppress
  everything and the sarabun-sync branch detects changes by diffing the
  `vals` dict inside its own `write()` override.

- **Compare against `commitment.available_to_obligate` (ledger headroom)
  instead of `commitment.amount` (cap)** — rejected. A god-mode edit
  mutates the PA's own future footprint on the commitment, not its current
  consumption. Comparing `sum(open PAs.amount_total) ≤ commitment.amount`
  handles single-PA and shared-commitment cases in one formula and is
  decoupled from the ledger's in-flight state.

- **Manual "Regenerate PDF" button instead of auto-regen** — rejected.
  Users would have to remember to press it after every edit; the reason
  they need god-mode is to iterate quickly. Auto-regen fits the workflow.

## Consequences

- **PDF export now reflects god-mode edits.** `_regenerate_report_pdf`
  unlinks the stored `<pa.name>.pdf` and re-renders via base
  `report_generate()` on every god-mode write that touches a PDF-visible
  field. The Sarabun preview flow was already live-rendering the QWeb
  template, so preview and export now agree.

- **Silent write is total, not partial.** A god-mode user's workflow-button
  actions (`button_draft`, `button_approved`, `button_cancel`) are also
  suppressed because the same `write()` runs underneath. This is deliberate
  — a partial audit trail would be more misleading than none. If future
  auditing needs a "god-mode edit occurred" event, add it outside the
  chatter (dedicated log table).

- **Sarabun-sync contract shifts from "listen to `tracking`" to "diff the
  `vals` dict"** — because no tracking events are emitted. The
  sarabun-sync branch overrides
  `purchase.request.approval.write()` (and the line's `write()`), detects
  god-mode edits by `state ∈ (to_approve, approved)` **and**
  `env.user.has_group('purchase_request_approval_godmode.group_pa_godmode')`,
  reads the freshly-regenerated PA `ir.attachment`, and updates the
  Sarabun-side `signed_pdf`.

- **`create="0" delete="0"` on the inner line tree** blocks add/remove
  even in draft. That capability existed in the base view but has no
  documented flow — all draft PA lines come from `_prepare_approval_vals`
  snapshotting the PR. We accept this narrowing.

- **Base-module bug fix landed here.** The `title` / `description`
  `related=` re-declaration is removed from
  `purchase_request_approval/models/purchase_request_approval.py`,
  restoring [ADR-0004](0004-pa-owns-copied-data.md). No data migration is
  needed because the feature is pre-production; new PAs populate
  `title` / `description` via the existing `_prepare_approval_vals`
  snapshot.

- **Cap is the commitment header amount, not the ledger headroom.** If ops
  need more room than the current cap allows, they must first raise the
  cap (`budget.commitment._update_commitment_amount`); god-mode is not a
  back door to cap growth.

- **KMITL Project shared-commitment scenario ([ADR-0007])** is covered by
  the aggregate rule: PA-A and PA-B under one project share
  `budget_commitment_id`, and the constraint sums both.

- **`rejected` and `cancelled` PAs stay fully locked** even for god-mode
  holders — the two terminal-negative states are out of scope; editing
  them would confuse audit and downstream reconciliation.

- **Reinforces [ADR-0004](0004-pa-owns-copied-data.md)** (PA carries its
  own copied divergeable data) and does not conflict with
  [ADR-0003](0003-sarabun-sole-approval-driver.md) — god-mode is a data
  correction, not a re-approval; state stays put and the Sarabun approval
  chain is not re-run.
