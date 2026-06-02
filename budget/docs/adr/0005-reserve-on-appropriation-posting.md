# Reserve fires when the budget appropriation is posted, not when the plan is made ready

A `procurement.plan` reserves its full `total_price` against a `budget.commitment` the moment its source `budget.appropriation` is **posted** (`action_post`) — not when the plan is later moved to `ready`. The reservation is created in the appropriation's `action_post` override **after** `super()` has posted the appropriation move, so the pool is appropriated (and therefore available) before it is locked. `_reserve_plan_commitment` stays idempotent, so the (now operational-only) `ready` step never double-reserves.

The plan's `ready` step — gated on the five ETA fields + procurement method — no longer *creates* the reservation. It keeps an idempotent `_reserve_plan_commitment()` call only as a backward-compatible safety net (a no-op once the plan already holds a commitment, covering plans whose appropriation was posted before this change). Its real job is now to be the **operational gate that unlocks creating the plan's purchase request**.

Supersedes the *"Reserve timing: on `ready`"* consequence of [ADR-0004](./0004-procurement-plan-shared-commitment.md). The shared-commitment, per-DR draw-down, release and cancellation decisions in ADR-0004 still stand.

## Why

- Thai practice: once budget is appropriated/approved the money is earmarked **immediately**; a plan must never sit appropriated-but-unreserved.
- Decouples money (reserved at allocation) from operations (ETA readiness), so the ETA gate can govern PR creation without doing double duty as the reservation trigger.

## Consequences

- Reserve still blocks on insufficient budget unless `budget.allow_negative` is set.
- Reservation must run *after* the appropriation move is posted; reserving inside `budget_move_line_vals` (before the move posts) would fail the availability check because the pool is not yet appropriated.
