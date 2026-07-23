# Actual (ผล) is read from `budget.move.line` consume, not `budget.commitment.line`

The Actual column reads เบิกจ่ายจริง from the budget **ledger** `budget.move.line` where `move_type='consume'` (posted, net of refunds), resolved by each Budget Line's `expr` over `code` and scoped by month + dimensions — **not** from `budget.commitment.line`, even though the [Budget](../../../budget/CONTEXT.md) glossary frames *Consume (เบิกจ่าย)* as a `budget.commitment` concept and the commitment ledger is the pipeline's canonical consume record. This is a deliberate, finance-directed choice.

## Rationale

`budget.move.line` is the budget **ledger of record** — the pool-reduction ledger that every other budget report (the monitoring dashboard's appropriation side, `budget_revenue_comparison`, `budget_report`) reconciles against, and it records pool consumption whether or not it flowed through a `budget.commitment`. Tying ผล to the ledger keeps the plan's Actual consistent with those reports and complete. For commitment-driven expenses the two ledgers are 1:1 anyway — each posted consume `budget.commitment.line` auto-creates a consume `budget.move.line` with `balance = −amount`.

## Considered options

- **`budget.commitment.line` consume** — the reserve→obligate→consume pipeline's canonical เบิกจ่าย. Rejected: it is the management/commitment view, not the ledger of record, and can miss consumption posted directly to `budget.move` outside the commitment pipeline.

## Consequences

- The Actual engine reuses `budget_revenue_comparison`'s approach almost verbatim: one `read_group` on `budget.move.line` grouped by `["code", "date:month"]` (+ dimension leaves), fed to the same `B[...]`-style resolver — no new query pattern, and `code`/`date` are already stored columns.
- Consume balances are **negative** on this ledger (credit side); negate to read เบิกจ่าย as a positive figure; a refund (a positive-balance consume reversal) nets it down.
- **Build-time caveat:** dimension attribution on `budget.move.line` varies by move type — `department_analytic_id` is computed only for `appropriation` moves, `fund_analytic_id` is a plain input field, and activity/project/plan derive from `analytic_distribution`. Verify that consume lines actually carry the Activity / Fund / ส่วนงาน needed for scoping; where a typed column is unreliable on consume lines, filter through `analytic_distribution` (the source of truth) with the same `("analytic_distribution", "in", ids)` leaf `budget_revenue_comparison` uses, rather than trusting the stored convenience column.
