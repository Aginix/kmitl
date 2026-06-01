# Procurement plan owns a shared commitment drawn down by downstream documents

When a `procurement.plan` is made **ready** it reserves ONE `budget.commitment` for its full `total_price`, linked via `procurement_plan_id`. Downstream plan-driven PR → PO → DR **draw this single commitment down** (obligate + consume) rather than each reserving its own — which is what prevents double-reservation (a plan reserving *and* its PR reserving would lock the same money twice).

Discriminator: a PR with `use_procurement_plan` links `plan.budget_commitment_ids` instead of calling `_create_budget_commitment`; a PR/approval **without** a plan keeps its own per-document commitment (unchanged).

## Consequences

- **Reserve timing:** on `ready`; blocks on insufficient budget unless `budget.allow_negative` is set.
- **Release:** on `on_hold` / `reset_to_draft` the plan cancels its commitment **only while untouched**; if any obligate/consume draw exists, the commitment is kept and a note is posted (never strand in-flight spend).
- **Cancellation:** cancelling one downstream DR reverses **only its own** obligate/consume lines — attributed via `res_model`/`res_id` stamped on the lines (`disbursement.request`) — leaving the shared reservation open for sibling DRs. Full-commitment cancel is kept only for sole-owner, non-plan commitments (D4). This relies on the Phase 1 fix that keeps reversals postable after a commitment auto-reaches `done`.

## Deferred (not in this phase)

- Consolidating the dormant `budget.mixin` into `budget.commitment.mixin`.
- POs created directly (without a PR) drawing the plan commitment.
- `approval.request` sharing a plan commitment (it has no `procurement_plan_id`).
