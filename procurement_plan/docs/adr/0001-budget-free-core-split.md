# Split procurement_plan into a budget-free core plus budget layers

## Context

`procurement_plan` was born coupled to budget: a plan could only exist as the by-product of a posted `budget.appropriation` line, it reserved its full amount the instant it appeared, and the module depended on `budget`. This made standalone procurement planning impossible and put budget-engine wiring in the same module as the plan document.

## Decision

Three modules, dependency-ordered:

- **`procurement_plan`** (core) — depends only on `web` + `account_analytic_kmitl`, no budget. Owns the plan document, the four classification dimensions, the `procurement_plan` analytic dimension **and its minting** (the analytic account is pure `account.analytic` — no budget needed), and a self-contained workflow `draft → to_verify → verified → in_progress → done` (+ `cancel`). `to_verify` mints the plan's analytic account; core `verified` is a plain "ยืนยัน" with no budget effect.
- **`procurement_plan_budget`** — adds `budget_account_id` (restricted to `procurement_plan` = investment accounts) and makes the `to_verify → verified` step **reserve** the plan's budget (จองงบ). This is the only place a reservation is created. Also carries the `budget.account` flag, the `budget.move.line` / `budget.commitment` links + auto-close, and the budget overview section.
- **`procurement_plan_budget_appropriation`** — plans born from a posted appropriation line: it **reuses** the core/budget transitions (`action_send_to_verify` to mint, `action_verify` to reserve) rather than reimplementing mint/reserve, and drives the plan straight to `verified` in one transaction.

## Consequences

- The old states `new`, `ready`, `on_hold` are gone; `ready` (the ETA gate) becomes `verified` and no longer requires ETAs or a procurement method (both now fully optional).
- Reservation release logic (formerly on `on_hold`) moves onto `action_reset_to_draft` / `action_cancel` and stays a budget-layer concern.
- The PR↔plan bridge is renamed `purchase_request_budget_procurement` → `purchase_request_procurement_plan`; consumers re-point their `depends`.
- The plan's running number resets per `account_fiscal_year_id` (per-fiscal-year sequence, drawn on the fiscal year's end date — the `kmitl_project` idiom).
- The whole procurement_plan family is pre-deployment: no data migration, no version bumps.
