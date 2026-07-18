# Post-Sarabun state split for พ.1: `in_egp` / `in_approval` and auto PA creation

Sarabun completing on a พ.1 (`purchase.request`) used to land the record in a single generic
`approved` state, forcing the user to manually branch — either click through the e-GP dance
(`action_egp_in_progress` → `action_egp_create_purchase_order`) or manually press "Create PA"
(`button_create_approval`) to spawn a `purchase.request.approval`. A PO created downstream
never advanced the PR beyond `in_progress`, so the terminal `done` state was effectively unreachable.

**Decision.** Split the post-approve state into two new semantic states — `in_egp` (e-GP branch,
waiting for the e-GP project number) and `in_approval` (non-e-GP branch, พจ.1 being drafted/approved)
— and reuse the OCA base `in_progress` for the "PO not yet cut" phase. The Sarabun completion
callback dispatches into a new hook `_transition_after_sarabun_approve()` chained by `super()`
across `purchase_request_egp` (owns `in_egp`) and `purchase_request_approval` (owns `in_approval`);
`purchase_request_kmitl` owns the base fallback and the new terminal state `cancelled`. On the
non-e-GP branch the dispatcher **auto-creates the PA** — the manual "Create PA" button is deleted.
`approval_make_purchase_order` (non-e-GP) and the OCA
`purchase.request.line.make.purchase.order.make_purchase_order()` (e-GP) each cascade PR → `done`
after the PO is actually created. PA approved cascades PR `in_approval` → `in_progress`. PA
cancelled (Sarabun reject or manager cancel) cascades PR → `cancelled`, which cancels the budget
commitment via a new `button_cancel` override in `purchase_request_budget`. The PA state machine
is also reduced from 5 states to 4 (merge `validate` into `to_approve`, rename `rejected` →
`cancelled`) to align with the drawio v2 model.

State labels for the new selections (`in_egp`, `in_approval`, `cancelled`) are declared in
English at the model layer; Thai user-facing strings live in each module's `i18n/th.po` so
translations can be revised without editing the code.

## Considered options

- **Add a sub-status field alongside a single `approved` state** — rejected. Dashboards, reports,
  and state-based ACL still see one state; the six existing computed-visibility booleans
  (`hide_create_po_button`, `need_make_purchase_order`, `show_egp_create_purchase_order_button`, …)
  would still branch on `state + sub_status` instead of `state` alone, doubling the guard surface.
- **Rename `approved`/`in_progress` in place** — rejected. Both values are referenced by
  OCA-adjacent modules (`purchase_request_verify_state`, base OCA computes) and by dashboards; a
  rename would ripple through every grep hit and every SELECT written by downstream reports.
  `selection_add` for the new values + a data migration is far cheaper.
- **Introduce a new `in_purchase` state (initial ADR-0005 draft)** — rejected in round-3.
  Reusing the OCA base `in_progress` state carries the same semantics, is already translated
  (`อยู่ระหว่างจัดซื้อจัดจ้าง` in the base `th.po`), and does not require a `selection_add` or a
  wizard `_VALID_PR_STATES` extension.
- **Cascade PA rejected → PR `rejected` (initial ADR-0005 draft)** — rejected in round-3.
  Reusing `rejected` was cheap but semantically off — `rejected` in drawio v2 is reserved for
  "Sarabun rejected the พ.1 directly". A dedicated `cancelled` state gives us a clean split.

## Consequences

- **Legacy `approved` / `in_progress` remain in the Selection.** No new transition writes
  `approved` (the fallback in `_transition_after_sarabun_approve`'s base is a safety net for
  installs without `_egp` / `_approval`, which we do not ship). The post-migration script at
  `purchase_request_kmitl/migrations/16.0.0.1.0/post-migration.py` moves existing rows:
  `approved+is_egp` → `in_egp`; `approved+non-egp+has PA` → `in_approval`; any stray
  `in_purchase` from intermediate builds → `in_progress`; PA `validate` → `to_approve`;
  PA `rejected` → `cancelled`.
- **Case 3 (approved + non-egp + no PA) is left in `approved`** and the row IDs are logged as a
  warning. Auto-creating a `purchase.request.approval` in SQL migration bypasses sequences, mail
  activities, and Sarabun template setup; ops manually advances these residual records or a
  one-time cleanup script (ORM-based) handles them post-deploy.
- **Grep audit required.** Every existing `state in ("approved", "in_progress")` check across the
  purchase_request family was reviewed; the model layer is patched to also accept the new states
  where relevant. Downstream reports/dashboards that filter on state must be independently
  audited — the migration cannot know which of them expected the old broad state and which
  expected the new narrower phase.
- **PA cascade goes to `cancelled`**, with commitment-cancel wired via `purchase_request_budget.button_cancel`.
- **PA state machine is 4-state.** `button_validate` is removed; `button_rejected` is renamed
  to `button_cancel`. Any RPC/tests calling `button_validate` will break — the demo hook was
  updated accordingly.
- **UI**: A "Cancel" button is added on PR in the header, visible only while `state in (draft, to_verify)`
  per the drawio's "user cancel window is pre-Sarabun only" rule.
- Reinforces [ADR-0003](0003-sarabun-sole-approval-driver.md) (Sarabun is the sole approval
  driver) and [ADR-0004](0004-pa-owns-copied-data.md) (PA carries its own copied data): the auto
  PA creation still snapshots via `_prepare_approval_vals`, so PA divergence is preserved.
