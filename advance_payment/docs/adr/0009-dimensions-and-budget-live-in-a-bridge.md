# Financial dimensions and budget live in `advance_payment_budget`, not in the core module

Status: accepted (2026-07; UAT-only) — amends ADR-0008

## Context & Decision

ADR-0008 put `budget_commitment_id` straight onto `advance.payment` and added `budget` to `advance_payment`'s `depends`. That made the core module carry the whole KMITL budget stack for one field, on top of the four analytic dimension pickers it already carried.

Both concerns move out into a new bridge, **`advance_payment_budget`** (`advance_payment` + `budget` + `account_analytic_kmitl`):

- `analytic.mixin` (hence `analytic_distribution`), the `_analytic_keys` registry, the four `*_analytic_id` pickers with their compute and inverses
- `budget_commitment_id`
- the blocking exception rule `excep_missing_analytic`, whose `py_code` reads those pickers
- the form's **มิติทางบัญชี** group and the ใบจองงบประมาณ field

Core keeps only the loan lifecycle and drops `account_analytic_kmitl` and `budget` from `depends`. The two places where core used to hand a distribution downstream — `advance.payment._prepare_account_payment_vals` and `advance.payment.return.line._prepare_return_payment_vals` — no longer mention it; the bridge overrides both and adds `analytic_distribution` back.

`auto_install: True`, so any database that has `advance_payment` and `budget` keeps today's behaviour with no action.

## Why

- **The loan lifecycle does not need งบประมาณ to be correct.** Submit, verify, approve, transfer, report, return, close and every guard around them are about who owes what; none reads a dimension or a commitment. A module that can be installed and tested without the budget chart is a smaller thing to reason about.
- **The dimensions were never core's to own.** They are the repo-wide `analytic_distribution` idiom from `account_analytic_kmitl`, and the loan is one more consumer of it. Keeping the idiom next to the budget field it feeds is the arrangement every other budget-backed document already uses (`purchase_request_budget` does exactly this to `purchase.request`).
- **The readonly-when-reference-locked behaviour comes home.** Those four `attrs` lived in `advance_payment_disbursement` — a module about ใบเบิก that had no business owning dimension attrs, and which only had a view file for that reason. The rule is now inline on the fields in the module that declares them, and that view file is deleted.
- `auto_install` rather than a manual install keeps the split invisible to UAT: the alternative is a database where a loan silently has no dimensions and the blocking rule that would have caught it is absent too.

## Consequences

- **The two source bridges now depend on `advance_payment_budget`.** `purchase_request_advance_payment` and `agx_approval_advance_payment` both prefill `analytic_distribution` and `budget_commitment_id` from their source document, so the fields must exist. In practice this means the bridge is present wherever loans have a source document — which is every KMITL install. The separation buys testability and a coherent dependency graph, not the ability to run KMITL without it.
- **`excep_missing_analytic` changes owner**, `advance_payment.excep_missing_analytic` → `advance_payment_budget.excep_missing_analytic`. Nothing in production depends on the old id; `advance_payment`'s own test suite now looks it up with `raise_if_not_found=False` so it neither requires the bridge nor breaks when `post_install` has it.
- A loan created with only core installed has no dimensions and no commitment, and `excep_missing_analytic` is not there to stop it — correct, since with no budget stack there is nothing to charge.
- The outbound and return `account.payment` still carry the loan's distribution; that now happens in the bridge's `_prepare_*_vals` overrides, so anything else that wants to extend those vals must be careful to `super()` in the right order.
- Consumption (ตัดงบ) is still parked exactly as ADR-0008 describes. This split changes where the carrier lives, not whether anything consumes.
