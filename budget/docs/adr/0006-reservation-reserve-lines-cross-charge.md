# Reservation is a ledger of reserve lines; header budget account is a mirror

A budget reservation (`budget.commitment`) holds its budget codes as `budget.commitment.line` reserve lines (budget account + amount each) — **the lines are the source of truth**. The header `account_id` is kept for the common single-code case but becomes a **computed/stored mirror**: the line's account when there is exactly one reserve line, blank / labelled "ถัวจ่าย" when there are several. The five fixed analytic dimensions live on the header — one combination for the whole reservation (per ADR 0005, the same combination applies to every line).

Most reservations use a **single** budget code. Multiple codes — **ถัวจ่าย / cross-charge**, pooling several pools in one reservation — are the minority and are gated by a new `budget.account.cross_chargeable` flag: a reservation may hold more than one reserve line **only when every line's account is `cross_chargeable = true`**. The flag alone governs; there is no same-category constraint.

**The picker widget is reusable across every form that reserves budget** (PR / PO / DR / procurement plan / approval, …), not just `budget.commitment`. It is host-agnostic: a host adopts `budget.commitment.mixin` and drops the widget on the mixin's existing `_commitment_id_field` (a M2O to `budget.commitment`). The widget edits that commitment's reserve `line_ids` + header dimensions directly — **a draft `budget.commitment` is the staging area**. This works because a *draft* commitment does **not** lock budget (used counts only active `reserved`/`partial`/`done`), so staging in draft never affects anyone else's availability; `action_reserve` flips it active at the host's lifecycle trigger. Commitment creation stays centralised in the mixin (`_get_or_create_draft_commitment`), created **lazily** when the first reserve line is entered (the host must be saved first — standard Odoo for related records). Abandoned drafts are cleaned by `ondelete=cascade` on the host link; a leftover draft is harmless.

## Considered options

- **Header `account_id` writable + lines (dual-mode)** — rejected: two sources of truth, write ambiguity.
- **Cross-charge gated by root category code (`53000` / ค่าใช้สอย)** — rejected: hard-codes today's data. A flag is generic and needs no code change when the policy widens.
- **Cross-charge requiring the same root category *in addition* to the flag** — rejected: redundant. To confine pooling to one category, flag only that category's codes (option A in grilling).
- **Staging reserve-line input in a JSON field on the mixin** — rejected: prefer reusing the `budget.commitment(.line)` models (their fields, validation, audit, and the existing `read_group` paths) over parsing a JSON blob. A draft commitment is the staging instead.

## Consequences

- Availability is checked **per reserve line** — each line is its own (account × dimension) combination, evaluated at its control node (ADR 0005).
- The reservation picker widget writes reserve lines; its editable amount column is enabled on budgetable rows, and more than one row may carry an amount only when all those accounts are `cross_chargeable`.
- `cross_chargeable` is a new boolean on `budget.account` (default `false`); the current ค่าใช้สอย/`53000` set is simply the data that will be flagged, not a code-level rule.
- All five analytic dimensions must be chosen to a **specific value** (parent or leaf — the control-node logic of ADR 0005 handles coverage) before any amount can be entered; the picker has **no "all"/rollup mode** — a reserve line always records a concrete combination.
- Availability is checked **per line**; if **any** line exceeds its available, the whole reservation is **blocked (atomic)**, governed by the existing `budget.allow_negative` switch (default = block). The widget surfaces per-row sufficiency (available vs entered amount).
