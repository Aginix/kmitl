# Expense Plan

Annual, monthly **แผนการเบิกจ่าย**: each ส่วนงาน plans how much it expects to เบิกจ่าย each month of a fiscal year, per budget line, and that plan is set beside actual expense (ผล). The structure is composed centrally as a Template — which budget lines sit under each fund, and which funds sit under each activity — while each ส่วนงาน **chooses which activities it will plan** and fills in the monthly Plan figures; the Actual figures are derived from budget consume.

Shares the financial-dimension vocabulary of [Budget](../budget/CONTEXT.md) — **Activity (กิจกรรม)**, **Fund (กองทุน)**, **Department (ส่วนงาน)**, **Consume (เบิกจ่าย)** — and reuses the two-namespace formula idea from [Budget Revenue Comparison](../budget_revenue_comparison/CONTEXT.md).

## Language

**Expense Plan (แผนการเบิกจ่าย)**:
The subject as a whole, and specifically a ส่วนงาน's monthly plan of expected เบิกจ่าย for one fiscal year and one แหล่งเงิน, set row-by-row beside Actual.
_Avoid_: spending plan, cash-flow plan; do **not** confuse with Procurement Plan (แผนจัดซื้อจัดจ้าง — a per-procurement plan) nor with the installment section also called "แผนการเบิกจ่าย" inside a procurement plan.

**Budget Line (รายการงบ)**:
A catalog record defining one plannable **column**: a label, its Category, and an `expr`. It is **not** a budget.account — it *curates* one or more budget.account codes (via `expr`) whose consume rolls into this column. Examples: ค่าจ้างพนักงาน, ค่าใช้สอย, ค่าครุภัณฑ์.
_Avoid_: budget account / รหัสงบประมาณ (that is the underlying budget.account node); งบประมาณ (too broad — reserve it for the general notion).

**Category (หมวดงบรายจ่าย)**:
One of the five expense roots of budget.account — 51000 งบบุคลากร, 52000 งบดำเนินงาน, 53000 งบลงทุน, 54000 งบเงินอุดหนุน, 55000 งบรายจ่ายอื่น (with 07020 งบกองทุนสำรอง as a sixth root in the chart). Every Budget Line belongs to exactly one.
_Avoid_: budget type (that is the revenue/expense flag on budget.account).

**expr (สูตรดึงผล)**:
The free-text formula on a Budget Line, evaluated by `safe_eval` over budget.account codes, resolving to the monthly consume for that column. Mirrors Budget Revenue Comparison's `B['<code>']` accessor but sums เบิกจ่าย (consume) instead of appropriation.
_Avoid_: domain, filter (it is an arithmetic code expression, not an Odoo domain).

**Template (แม่แบบแผนเบิกจ่าย)**:
The central definition — one per (แหล่งเงิน × ปีงบประมาณ) — holding two compositions (ADR-0004): **Fund → Budget Lines** (which รายการงบ sit under each กองทุน) and **Activity → Funds** (which กองทุน sit under each ด้าน/แผนงาน). It is the shared structure behind every Plan Document; a ส่วนงาน selects which Activities to plan and the funds + budget lines follow from these compositions. Edited in draft and **published** to become usable; a Template edit propagates live (ADR-0002).
_Avoid_: report layout (the Template is master data, not a rendering); config; "active" (that names a Plan Document state, not the Template's — the Template is *published*).

**Plan Document (เอกสารแผนเบิกจ่าย)**:
One ส่วนงาน's holder of Plan figures for a (แหล่งเงิน, ปีงบ) — carries state, ownership, access, the ส่วนงาน's **chosen Activities**, and a sparse set of monthly Plan amounts keyed by (Activity, Fund, Budget Line, month). Its grid is **not** a snapshot: it is rendered live from the ส่วนงาน's chosen Activities crossed with the current Template's compositions, so a Template edit or an activity de/selection shows immediately (a de-selected activity's amounts persist, hidden, and reappear when re-added). Actual figures are derived, never entered.
_Avoid_: template (a Plan Document is an *instance* of a Template, not the Template itself).

**Required Department (ส่วนงานที่ต้องทำแผน)**:
A configured ส่วนงาน (`department_analytic_id`) obligated to produce a Plan Document. The setup screen listing them drives who-must-plan tracking and document generation.
_Avoid_: operating unit (OU gates *access*; ส่วนงาน is the financial dimension and the plan's unit).

**Plan (แผน)**:
The manually-entered figure — the amount a ส่วนงาน expects to เบิกจ่าย for a given (Activity, Fund, Budget Line) in a given month.
_Avoid_: budget, appropriation (the appropriated pool is a different quantity).

**Actual (ผล)**:
The derived figure beside Plan — real เบิกจ่าย read from the budget **ledger** `budget.move.line` where `move_type='consume'` (posted, net of refunds), for the budget codes named by the Budget Line's `expr` and matching dimensions, in that month. Read from the ledger of record, **not** from `budget.commitment.line` (see ADR-0003). Never hand-entered.
_Avoid_: consume (use "consume" in code, "ผล / เบิกจ่ายจริง" in UI); disbursed; commitment consume (that is the pipeline ledger, not the source here).

**Confirmed (ยืนยันแผน)**:
Plan Document state — the ส่วนงาน has finished entering and submitted its แผน. Still reopenable, but signals "done from the unit side."
_Avoid_: approved, active (approval/lock is the next state).

**Active (แผนใช้งาน)**:
Plan Document state — central (กองแผน) has reviewed and approved the plan, and the document is **locked**: แผน figures can no longer be edited. This is the baseline that ผล is compared against.
_Avoid_: confirmed (that is the unit-side submit); the Odoo `active` archive flag (unrelated).
