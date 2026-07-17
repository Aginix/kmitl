# Post-Sarabun state split for พ.1: `in_egp` / `in_approval` / `in_purchase` and auto PA creation

Sarabun completing on a พ.1 (`purchase.request`) used to land the record in a single generic
`approved` state, forcing the user to manually branch — either click through the e-GP dance
(`action_egp_in_progress` → `action_egp_create_purchase_order`) or manually press "Create PA"
(`button_create_approval`) to spawn a `purchase.request.approval`. A PO created downstream
never advanced the PR beyond `in_progress`, so the terminal `done` state was effectively unreachable.

**Decision.** Split the post-approve state into three semantic states — `in_egp` (e-GP branch,
waiting for the e-GP project number), `in_approval` (non-e-GP branch, พจ.1 being drafted/approved),
and `in_purchase` (either branch, PA approved or e-GP running, PO not yet cut). The Sarabun
completion callback dispatches into a new hook `_transition_after_sarabun_approve()` chained by
`super()` across `purchase_request_egp` (owns `in_egp`) and `purchase_request_approval` (owns
`in_approval`); `purchase_request_kmitl` owns `in_purchase` and the base fallback. On the
non-e-GP branch the dispatcher **auto-creates the PA** — the manual "Create PA" button is deleted.
`approval_make_purchase_order` (non-e-GP) and the OCA
`purchase.request.line.make.purchase.order.make_purchase_order()` (e-GP) each cascade PR → `done`
after the PO is actually created. PA approved cascades PR `in_approval` → `in_purchase`.

## Considered options

- **Add a sub-status field alongside a single `approved` state** — rejected. Dashboards, reports,
  and state-based ACL still see one state; the six existing computed-visibility booleans
  (`hide_create_po_button`, `need_make_purchase_order`, `show_egp_create_purchase_order_button`, …)
  would still branch on `state + sub_status` instead of `state` alone, doubling the guard surface.
- **Rename `approved`/`in_progress` in place** — rejected. Both values are referenced by
  OCA-adjacent modules (`purchase_request_verify_state`, base OCA computes) and by dashboards; a
  rename would ripple through every grep hit and every SELECT written by downstream reports.
  `selection_add` for the new values + a data migration is far cheaper.
- **Cascade PA rejected/cancelled → PR `cancelled` (per drawio v2)** — rejected for now.
  `purchase_request_budget.button_rejected` (L284-297) already cancels the budget commitment when
  a PR transitions to `rejected`; reusing it saves adding a new `cancelled` state, new
  commitment-cancel wiring, and a new set of view attributes. Semantic drift acknowledged —
  drawio v2 distinguishes "Sarabun rejected the พ.1 directly" (`rejected`) from
  "cascaded from PA / manager cancel" (`cancelled`) and we lose that. A future ADR can introduce
  `cancelled` when the full drawio cancel graph is implemented.

## Consequences

- **Legacy `approved` / `in_progress` remain in the Selection.** No new transition writes them.
  The post-migration script at `purchase_request_kmitl/migrations/16.0.0.1.0/post-migration.py`
  moves existing rows: `approved+is_egp` → `in_egp`; `approved+non-egp+has PA` → `in_approval`;
  `in_progress+PA approved` → `in_purchase`; `in_progress+egp_status='in_progress'` → `in_purchase`.
- **Case 3 (approved + non-egp + no PA) is left in `approved`** and the row IDs are logged as a
  warning. Auto-creating a `purchase.request.approval` in SQL migration bypasses sequences, mail
  activities, and Sarabun template setup; ops manually advances these residual records or a
  one-time cleanup script (ORM-based) handles them post-deploy.
- **Grep audit required.** Every existing `state in ("approved", "in_progress")` check across the
  purchase_request family was reviewed; the model layer is patched to also accept the new states
  where relevant. Downstream reports/dashboards that filter on state must be independently
  audited — the migration cannot know which of them expected the old broad state and which
  expected the new narrower phase.
- **PA cascade goes to `rejected`, not `cancelled`.** See rejected option above.
- Reinforces [ADR-0003](0003-sarabun-sole-approval-driver.md) (Sarabun is the sole approval
  driver) and [ADR-0004](0004-pa-owns-copied-data.md) (PA carries its own copied data): the auto
  PA creation still snapshots via `_prepare_approval_vals`, so PA divergence is preserved.
