# Procurement Plan — Budget

Makes a [Procurement Plan](../procurement_plan/CONTEXT.md) budget-backed: it carries a budget code, and reserves its full amount against the budget pipeline when it is verified. This is the layer that connects the standalone plan to the KMITL budget engine; the plan itself (workflow, dimensions, analytic identity) lives in core.

## Language

**Reserve (จองงบ)**:
The plan's full-amount earmark against the budget pool, created the moment the plan is verified (รอตรวจสอบข้อมูล → รอดำเนินการ). One `budget.commitment` per plan; nothing downstream reserves again — a plan-driven purchase request only *draws* this reservation down.
_Avoid_: allocate, commit

**Budget code (รหัสงบประมาณ, `budget_account_id`)**:
The `budget.account` a plan reserves against. Restricted to accounts flagged for procurement (`procurement_plan = True`, i.e. investment budget). Required to verify a plan at this layer.
_Avoid_: budget account (generic), GL account
