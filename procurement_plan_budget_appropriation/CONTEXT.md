# Procurement Plan — Budget Appropriation

Plans born from a posted budget appropriation line, instead of created by hand. Reuses the [Procurement Plan](../procurement_plan/CONTEXT.md) core transitions and the [Reserve](../procurement_plan_budget/CONTEXT.md) budget layer rather than reimplementing mint/reserve: posting the appropriation drives the plan straight to `verified` in one transaction.

## Language

**Appropriation-born plan (แผนที่เกิดจากใบจัดสรรงบประมาณ)**:
A `procurement.plan` created by `budget.appropriation.line._create_procurement_plan()` when its `enable_procurement_plan` flag is set. Runs `draft → to_verify → verified` inside `budget.appropriation.action_post()`: `to_verify` mints the plan's analytic account (core), `verified` reserves its budget (the budget layer's `_on_verify` hook) — the same code paths a manually-created plan uses.
_Avoid_: generated plan, auto plan

**Locked (can_edit = False)**:
Once a `budget.appropriation.line` links to the plan, the plan can no longer be edited directly — it is driven by the appropriation, not by hand.
_Avoid_: read-only, frozen
