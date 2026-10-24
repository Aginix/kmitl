# Procurement Plan — Budget

Makes a [Procurement Plan](../procurement_plan/CONTEXT.md) budget-backed: it carries a budget code, and reserves the budget it has actually received against the budget pipeline when it is verified. This is the layer that connects the standalone plan to the KMITL budget engine; the plan itself (workflow, dimensions, analytic identity) lives in core.

## Language

**Reserve (จองงบ)**:
The plan's earmark against the budget pool, sized to its **Plan Budget** (what it has actually received at its dimension) — not its วงเงินตามแผน. Created automatically on verify (รอตรวจสอบข้อมูล → รอดำเนินการ) when the plan has received at least its วงเงินตามแผน; an under-funded plan is reserved by a budget user by hand, with a warning. Money received later tops the reservation up. One `budget.commitment` per plan; nothing downstream reserves again — the plan's purchase requests only *draw* this reservation down. See [ADR-0003](../procurement_plan/docs/adr/0003-plan-reserves-received-not-plan-amount.md).
_Avoid_: allocate, commit

**Budget code (รหัสงบประมาณ, `budget_account_id`)**:
The `budget.account` a plan reserves against. Restricted to accounts flagged for procurement (`procurement_plan = True`, i.e. investment budget). Required to verify a plan at this layer.
_Avoid_: budget account (generic), GL account
