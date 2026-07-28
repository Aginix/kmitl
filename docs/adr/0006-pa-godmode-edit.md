# พจ.1 (PA) God-Mode post-approval edit — narrow header + line qty/price unlock, capped by budget commitment

ADR-0005 makes PA `approved` a terminal state: the only way to correct a mistake
(typo in title, wrong vendor, off-by-one qty, real market price ≠ requested
price) is to cancel and re-issue the whole พจ.1, which cascades to Sarabun and
downstream PO/DR. That cost is disproportionate when the correction fits inside
the budget already reserved for the parent พ.1 (e.g. requested ไก่ 120฿ × 3 =
360฿, actually 130฿ × 3 = 390฿).

**Decision.** Introduce a dedicated security group `group_pa_godmode` in a new
addon `purchase_request_approval_godmode`. Members may edit a **narrow** set of
PA fields even while `state == 'approved'`, without transitioning the record
out of `approved`. The set is:

- **Header (8):** `title`, `description`, `partner_id`, `procurement_type_id`,
  `procurement_method_id`, `payment_type`, `vat_included`, `tax_id`.
- **Line (2):** `product_qty`, `price_unit` on each existing
  `purchase.request.approval.line` — no add/remove; `product_id`, `name`,
  `product_uom_id` stay locked.

A `@api.constrains('amount_total', 'line_ids', 'line_ids.product_qty',
'line_ids.price_unit')` on `purchase.request.approval` guards the edit: the
sum of `amount_total` across all `approved` PAs sharing the same
`request_id.budget_commitment_id` must not exceed the commitment's cap
(`commitment.amount`, "วงเงินอนุมัติ"). The check runs **only when**
`state == 'approved'` **and** the writing user holds `group_pa_godmode`; other
state/actor combinations are governed by existing rails (PR reserve at
`action_reserve_budget`, DR obligate at disbursement creation).

The god-mode edit is a **PA-only surgical write**: downstream PO/DR/bill
artefacts are not re-derived. Sarabun sync of god-mode edits is out of scope
here — that concern belongs to a separate branch which will override PA
`write()` to detect the edit context (`state == 'approved'` +
`env.user.has_group('purchase_request_approval_godmode.group_pa_godmode')`)
and update the linked หนังสือ. To make that detection cheap, this addon adds
`tracking=True` to every newly-unlockable field.

## Considered options

- **Boolean toggle on `res.users` instead of a security group** — rejected.
  Groups are the OCA-native permission surface, are visible in the standard
  Access-Rights tab, participate in `groups="…"` in views/menus and in
  `ir.rule`, and are auditable without a dedicated report. A per-user boolean
  gives the same effect but hides the fact that it is a permission.

- **Full re-issue (cancel PA + create a new PA revision)** — rejected. Cascades
  to Sarabun (a new หนังสือ must be routed), breaks the 1 พ.1 ↔ 1 พจ.1 policy
  from [ADR-0002](0002-pa-separate-model.md), and is heavy for what is often a
  ≤10% price correction.

- **Model-level `write()` guard blocking non-god-mode writers on approved PAs**
  — rejected. OCA convention is that state-based edit locks live in views
  (`attrs="{'readonly': [('state', '!=', 'draft')]}"`), not in the model.
  A model guard would need explicit exceptions for every workflow that writes
  to `approved` PAs (`_on_sarabun_completed`, tier-validation review actions,
  etc.) and for RPC-driven system integrations. We accept the trade-off that
  a non-god-mode user hitting `write()` directly via RPC is not blocked; the
  form is the enforcement surface.

- **Include add/remove lines in the god-mode scope** — rejected. Empirically
  ≥95% of post-approval corrections are `product_qty` / `price_unit` edits;
  adding lines implies renumbering, re-triggering `_prepare_approval_vals`
  snapshotting, and a Sarabun diff surface too large for v1.

- **Compare against `commitment.available_to_obligate` (headroom)** —
  rejected. The commitment's `available_to_*` fields track the reserve →
  obligate → consume ledger. A god-mode edit mutates the PA's **own future
  footprint** on the commitment, not its current consumption. Comparing
  `sum(approved PAs.amount_total) ≤ commitment.amount` handles both single
  and shared-commitment cases in one formula and is decoupled from the
  ledger's in-flight state.

## Consequences

- **`create="0" delete="0"` on the inner line tree** blocks add/remove even
  in draft state. That capability existed in the base view but has no
  documented flow — all draft PA lines come from `_prepare_approval_vals`
  snapshotting the PR. We accept this narrowing.

- **Incidental ADR-0004 bug fix.** The base `purchase.request.approval` model
  declares `title` and `description` twice — first as own `fields.Char/Text`
  and later as `fields.Char(related="request_id.title")`. Python's second
  declaration wins, so those fields have been effectively delegated to the
  PR — contradicting [ADR-0004](0004-pa-owns-copied-data.md). The god-mode
  addon re-declares them as own tracked columns, restoring ADR-0004 intent.

- **Line-level `tracking=True` requires the sarabun-sync branch's `write()`
  override on the line model.** Odoo does not automatically post child field
  changes to the parent chatter via `_message_track`; that branch must
  implement the sync at the appropriate layer.

- **Cap is the commitment header amount, not the ledger headroom.** If ops
  need more room than the current cap allows, they must first raise the cap
  (see `_update_commitment_amount` on `budget.commitment`); god-mode is not
  a back door to cap growth.

- **KMITL Project shared-commitment scenario ([ADR-0007]) is covered** by
  the aggregate rule: PA-A and PA-B under one project share
  `budget_commitment_id`, and the constraint sums both.

- **Reinforces [ADR-0004](0004-pa-owns-copied-data.md)** (PA carries its own
  copied divergeable data — god-mode is the mechanism by which the amount /
  vendor / VAT that ADR-0004 anticipates diverging actually does diverge
  post-approval).

- **Does not conflict with [ADR-0003](0003-sarabun-sole-approval-driver.md)**
  — god-mode is a data correction, not a re-approval; state stays `approved`
  and the Sarabun approval chain is not re-run.
