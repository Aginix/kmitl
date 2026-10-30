# Procurement Plan

Annual procurement planning (แผนจัดซื้อจัดจ้าง) for KMITL. A plan stands on its own: it is created directly, carries the classification dimensions, and moves through a self-contained workflow — no budget involved. Budget backing (reservation) and origination from a budget appropriation are optional capabilities layered on by separate modules.

## Language

### The plan

**Procurement Plan (แผนจัดซื้อจัดจ้าง)**:
A single planned procurement. Created manually (or, with the budget-appropriation layer, born from a posted appropriation line). Carries the four classification dimensions (ส่วนงาน / แหล่งเงิน / กองทุน / กิจกรรม) via `analytic_distribution`, and owns its own analytic account in the `procurement_plan` dimension once submitted. It belongs to its **unit** (operating unit), not to a person — anyone with plan rights in that unit may work on it. Realised through one or more purchase requests (พ.1), never approved on its own ([ADR-0002](./docs/adr/0002-no-per-plan-approval-annual-plan-is-published-unit.md)).
_Avoid_: purchase plan, procurement request

**Annual Procurement Plan (แผนจัดซื้อจัดจ้างประจำปี)**:
The collection of one unit's **Procurement Plans** for one fiscal year, from รอดำเนินการ (`verified`) onward — the thing that is approved and published under พ.ร.บ.การจัดซื้อจัดจ้างฯ 2560 ม.11. A view over plans (report / public portal), never a record of its own. See [ADR-0002](./docs/adr/0002-no-per-plan-approval-annual-plan-is-published-unit.md).
_Avoid_: plan (unqualified — that is one Procurement Plan); approval of a plan

**Plan analytic account (มิติแผนจัดซื้อจัดจ้าง)**:
The `account.analytic.account` in the `procurement_plan` dimension that *is* this plan — its identity as a dimension value, so other documents can be tagged to it. Minted when the plan is first submitted (draft → รอตรวจสอบข้อมูล). Exists independently of any budget.
_Avoid_: dimension, tag

**Plan Amount (วงเงินตามแผน, `total_price`)**:
What the plan **asks for** — the procurement's estimated value as planned. The yardstick that **Plan Budget** is measured against; never reserved by itself.
_Avoid_: budget, Plan Budget (that is what was actually received)

**Responsible (เจ้าหน้าที่ผู้รับผิดชอบ, `responsible_id`)**:
The officer who looks after the plan day to day. A contact, not an owner: they follow the plan and are told of every status change, but grant no rights the unit's plan users don't already have. Optional, and may change at any time until the plan is closed or cancelled.
_Avoid_: owner, coordinator (plans have neither — unlike a KMITL Project); ผู้จัดทำ

**Preparer (ผู้จัดทำ, `user_id`)**:
Who drew the plan up — defaults to its creator (or the appropriation's user for a plan born from an appropriation) and is fixed once the plan is submitted. Drives "แผนของฉัน". Not the Responsible.
_Avoid_: owner, responsible

**Installment (งวดงาน, `procurement.plan.payment`)**:
A planned disbursement tranche of a plan. Optional; when a plan has any, they must add up to the **Plan Amount** before the plan is submitted, and only warn on a mismatch afterwards. Purely informational at the core level — the rows are the *plan*, not a ledger.
_Avoid_: payment, period

### Lifecycle

**Submit (ส่งเข้ารอจัดสรรงบประมาณ)**:
The draft → รอตรวจสอบข้อมูล transition. The single act that takes a plan out of drafting and mints its plan analytic account. Budget-free at the core level.
_Avoid_: confirm, activate, ปรับแผน

**Close Plan (ปิดแผน)**:
The manual act that finishes a plan in progress (อยู่ในระหว่างดำเนินการ → จัดซื้อจัดจ้างเสร็จสิ้น), by a plan manager. Waits until no purchase request, purchase order or disbursement request on the plan is still open, and returns the unspent reservation (คืนจอง) — the money itself stays at the plan's dimension as **Held Money**. Never happens automatically when the reservation is used up. See [ADR-0005](./docs/adr/0005-plan-close-and-deletion-follow-project.md).
_Avoid_: done / auto-close, cancel

**Plan Deletion (ลบแผน)**:
The single way to take a plan out of use. A plan with no **Ledger Footprint** is deleted for good together with its analytic account; one with a footprint that has never spent is **soft-deleted** — it becomes ยกเลิก and both it and its analytic account are archived, and resetting it to draft brings both back with the same number. A plan that has spent cannot be deleted; it is closed instead. Waits until the plan holds no **Held Money** and has no open purchase request, purchase order or disbursement request. A numbered plan may be deleted only by plan managers. See [ADR-0005](./docs/adr/0005-plan-close-and-deletion-follow-project.md).
_Avoid_: cancel as a separate act (ยกเลิก is only the state a soft-deleted plan ends in)

**Ledger Footprint (ประวัติในบัญชีงบประมาณ)**:
Whether the plan's analytic account has ever been recorded on any other document — a budget movement, a reservation, a transfer, a purchase request, in any state, even cancelled. A plan with a footprint is part of the budget history, so its analytic account is kept (archived), never deleted.
_Avoid_: balance (a footprint can exist even when every figure nets to 0)

### Money at the plan (budget layers)

**Plan Budget (งบที่ได้รับการจัดสรร, `budget_amount`)**:
The amount the plan has actually **received** at its own dimension — the net of the posted allocation, transfer and budget-entry lines (`appropriation` / `entry` buckets) carrying its `procurement_plan` dim — reserve, obligate and consume events are not counted. Read from the budget ledger, never typed. It is what the plan reserves and what caps its purchase requests. See [ADR-0003](./docs/adr/0003-plan-reserves-received-not-plan-amount.md).
_Avoid_: Plan Amount / วงเงินตามแผน (the ask, a different quantity)

**Plan Budget Remaining (งบคงเหลือ)**:
**Plan Budget** (received) minus what has actually been **consumed (เบิกจ่าย)** at the plan's dimension. Meaningful in every state; after closing it shows the leftover still held at the plan until a **Floating Return**.
_Avoid_: remaining (unqualified — clashes with budget's Remaining (f)); reserved − obligated (one reservation's view); Plan Amount − anything

**Held Money (เงินค้างในมิติแผน)**:
Money still tied to the plan's dimension: a non-zero net allocation on any coordinate in any fiscal year, an active reservation, or a transfer into or out of the dimension still in progress. While a plan holds any, its รหัสงบ and dimensions cannot change and it cannot be deleted; a **Floating Return** clears it.
_Avoid_: Plan Budget Remaining (only one part of it)

**Direct Floating Allocation (จัดสรรงบประมาณ (งบลอย))**:
A budget user moving money from the floating pool that covers the plan's coordinate into the plan's own dimension, from the plan itself, taking effect at once with no transfer approval. In the ledger an ordinary budget transfer. Same meaning as for a [KMITL Project](../kmitl_project/CONTEXT.md), separately implemented ([ADR-0006](./docs/adr/0006-plan-money-tools-separate-from-project.md)).
_Avoid_: quick transfer, งบลอย as the name of the pool

**Floating Return (โอนคืนงบลอย)**:
The reverse of a **Direct Floating Allocation**: money at the plan's dimension sent back to the floating pool at once. Reserved-but-unobligated money leaves the reservation in the same move; obligated or consumed money cannot be returned. The only way to clear **Held Money**.
_Avoid_: refund / คืนเงิน; คืนจอง (that only releases a reservation and leaves the money at the plan)

**Plan Budget Overview (บัญชีแผน)**:
The one place a plan's budget is followed and moved: **Plan Budget** received − consumed = **Plan Budget Remaining** against the **Plan Amount**, its **Plan Budget Movements**, its reservation and the money actions open to the viewer. Budget side only.
_Avoid_: GL account, bank account — "บัญชี" is the plan's budget book, not accounting

**Plan Budget Movements (การเคลื่อนไหวงบ)**:
The plan's read-only list of every budget movement on its dimension (allocation, transfer in/out, budget entry, consumption), each with a signed amount and status, readable without budget rights. Reservations are not movements and are not listed.
_Avoid_: ledger / budget move (users still have no access to `budget.move`)
