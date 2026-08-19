# Procurement Plan

Annual procurement planning (แผนจัดซื้อจัดจ้าง) for KMITL. A plan stands on its own: it is created directly, carries the classification dimensions, and moves through a self-contained workflow — no budget involved. Budget backing (reservation) and origination from a budget appropriation are optional capabilities layered on by separate modules.

## Language

**Procurement Plan (แผนจัดซื้อจัดจ้าง)**:
A single planned procurement. Created manually (or, with the budget-appropriation layer, born from a posted appropriation line). Carries the four classification dimensions (ส่วนงาน / แหล่งเงิน / กองทุน / กิจกรรม) via `analytic_distribution`, and owns its own analytic account in the `procurement_plan` dimension once submitted.
_Avoid_: purchase plan, procurement request

**Plan analytic account (มิติแผนจัดซื้อจัดจ้าง)**:
The `account.analytic.account` in the `procurement_plan` dimension that *is* this plan — its identity as a dimension value, so other documents can be tagged to it. Minted when the plan is first submitted (draft → รอตรวจสอบข้อมูล). Exists independently of any budget.
_Avoid_: dimension, tag

**Submit (ส่งเข้ารอจัดสรรงบประมาณ / ปรับแผน)**:
The draft → รอตรวจสอบข้อมูล transition. The single act that takes a plan out of drafting and mints its plan analytic account. Budget-free at the core level.
_Avoid_: confirm, activate

**Installment (งวดงาน, `procurement.plan.payment`)**:
A planned disbursement tranche of a plan. Purely informational at the core level — the rows are the *plan*, not a ledger.
_Avoid_: payment, period
