# Reservation field widget writes in-memory; picker gains a return-selection mode

The `budget_reservation` field widget (anchored on a host's budget-account field —
`budget_account_id` by default) opens the existing reservation picker in a new
`return_selection` mode: instead of calling the host's `apply_reservation_selection`
server-side and reloading the form, the picker returns the chosen
`{account_id, distribution, fiscal_year_id}` via the action `onClose`, and the widget
applies them with an in-memory `record.update` that the host's normal **Save** persists.
This matches the core `analytic_distribution` widget (no forced reload, respects
dirty/discard) and lets the host show the picked code's **Available (งบที่จองได้)**
inline via `budget.controller.get_reservation_status`. The button hosts
(`purchase.request`, `disbursement.request`, `budget.commitment`) keep the original
server-write path unchanged.

**Trade-off:** the widget path bypasses `apply_reservation_selection`'s server-side
domain re-check and host side-effects (e.g. purchase-request product sync). This is
acceptable because the picker still filters *selectable* codes by the host's
`account_domain` (so an out-of-domain code cannot be picked through the UI), the
budget-account field domain guards the client, and the real over-reservation guard
runs at reserve time — `budget.controller.check_budget_availability` when the project
is confirmed (`draft→new`). A host needing server-side side-effects on selection should
keep the button path or move those effects to `write`/`onchange`.

**Save-on-open:** opening reuses the host's `action_open_reservation_picker` (an
instance method that reads `self` to build the account domain + dimension/fiscal-year
defaults), so the widget saves the record on open — the same precondition the legacy
`type="object"` picker button already imposed.

The status figures (`get_reservation_status`) are computed against the **four real
accounting dimensions only**; the ownership tags (`kmitl_project` /
`procurement_plan`) ride on a reservation but never on the floating appropriation pool,
so they are stripped before control-node resolution — mirroring the reserve-time check.
