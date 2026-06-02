# Procurement Plan

Annual procurement planning (แผนจัดซื้อจัดจ้าง) for KMITL. A plan is born from an approved budget appropriation, reserves its full amount against the budget pipeline at that moment, and is realised through exactly one purchase request and a series of installment disbursements.

## Language

**Procurement Plan (แผนจัดซื้อจัดจ้าง)**:
A single planned procurement, created when a `budget.appropriation` line is posted. Owns one `budget.commitment` (its reservation) and at most one *active* purchase request. Carries the financial dimensions via `analytic_distribution`.
_Avoid_: purchase plan, procurement request

**Installment (งวดงาน, `procurement.plan.payment`)**:
A planned disbursement tranche of a plan. Actual budget consumption happens งวด-by-งวด through disbursement requests; the installment rows are the *plan*, not the ledger.
_Avoid_: payment, period

**Reserve (จองงบ)**:
The plan's full-amount earmark, created the moment its source appropriation is posted — i.e. when the plan reaches state `new`. The single act of จองงบ; nothing downstream reserves again. See [budget » Reserve](../budget/CONTEXT.md).
_Avoid_: allocate

**Ready (the ETA gate)**:
The operational checkpoint — all five ETA fields + procurement method filled — that **unlocks creating the plan's purchase request**. It does not touch budget (the reserve already happened at `new`).
_Avoid_: confirmed, approved

**Reserve Budget (the PR `action_reserve_budget` button)**:
A misnomer for plan-driven PRs: it does **not** จองงบ. The reservation already exists on the plan; a plan-driven PR only *links* it. Reserving (จองงบ) is exclusively the appropriation→`new` event.
_Avoid_: using "reserve budget" to mean จองงบ for plan-driven PRs
