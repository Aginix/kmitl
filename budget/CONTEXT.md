# Budget

Budget appropriation, reservation and disbursement tracking for KMITL. Money is appropriated to budget accounts (`budget.move`), then reserved → obligated → consumed against those accounts (`budget.commitment`). Availability is the appropriated pool minus what the commitment pipeline has locked.

## Language

### Access & scope

**Operating Unit (OU, หน่วยงาน)**:
The access-control boundary (`operating.unit`, from OCA). A user only sees budget moves/commitments whose `operating_unit_id` is among their allowed OUs (central-planning staff are granted all). It gates *visibility* — it is not a financial dimension and is never summed or shown as a report axis.
_Avoid_: department, faculty (those name the financial dimension)

**Department (ส่วนงาน, `department_analytic_id`)**:
One of the six financial dimensions (the `departments` analytic plan), carried on move/commitment lines and used as a report **filter**. Mirrors the Operating Unit in meaning but is a separate field used for financial breakdown, not for access.
_Avoid_: operating unit, OU

### Budget structure

**Budget Account (รหัสงบประมาณ)**:
A node in the hierarchical chart of budget codes (`budget.account`). Carries a `budget_type` (revenue / expense) and rolls up parent→child. The row axis of any budget report.
_Avoid_: account (ambiguous with `account.account`), category

**Budget Pool**:
The appropriated money available on a budget account for a fiscal year, before any commitment activity. Built up from appropriation and transfer moves.
_Avoid_: allocation (reserve "allocation" for the initial act of appropriating)

### Appropriation side (`budget.move`)

**Initial Appropriation (งบประมาณจัดสรรต้นปี)**:
The budget allocated at the start of the fiscal year, excluding any later adjustment or transfer. Identified by `appropriation_type = 'initial'`.
_Avoid_: original budget, opening budget

**Current Budget / งบประมาณ (a)**:
The budget pool after all latest adjustments = initial + supplementary appropriations + net transfers in/out. The denominator for "remaining". Defined as the net of every posted move that raises or lowers the pool (appropriation and entry/transfer moves), **excluding** consumption.
_Avoid_: total budget, final budget

**Budget Transfer (การโอนงบ)**:
A balanced move (`budget.transfer` → `budget.move` of type `entry`) that shifts pool from one budget account to another. Increases Current Budget at the destination, decreases it at the source. Part of "adjustments", so it is reflected in Current Budget (a).
_Avoid_: reallocation

**Adjustment (ปรับปรุง/ปรับโอน)**:
The in-year movement on the pool = Current Budget − Initial Appropriation = supplementary appropriations + net transfers. Shown as its own column between (1) and (a).
_Avoid_: change, revision

### Disbursement side (`budget.commitment`)

A commitment holds one cap and a ledger of lines; each line is a reserve/obligate/consume entry. The three operations are **independent primitives** — a flow may fire them at different times (procurement instalments) or together (PO disbursement).

**Approved Spending Limit (วงเงินอนุมัติ) / ขอใช้ทั้งหมด (3)**:
The per-commitment cap (`commitment.amount`) — the amount a request was approved to spend. Dashboard column (3) = sum of caps over commitments still active (not cancelled). May exceed what is actually reserved.
_Avoid_: budget, reserved amount

**Reserve (จองงบ)**:
Earmarking pool against a commitment the moment it is approved (e.g. a procurement plan reserves its full amount at once). A `reserve` ledger line.
_Avoid_: allocate, commit

**Obligate (ผูกพัน)**:
Binding earmarked money to an obligation (contract / PO / disbursement request). An `obligate` ledger line, posted before its matching consume.
_Avoid_: encumber, commit

**Consume (ตัดงบ / เบิกจ่าย)**:
The actual disbursement — money leaves the pool for good. A `consume` ledger line.
_Avoid_: spend, pay, disburse (pick "consume" in code, "เบิกจ่าย" in UI)

**Reserved (b) / Obligated (c) / Disbursed (d) / Used (e) / Remaining (f)**:
The disbursement waterfall for an account: `b` = reserved-but-not-yet-obligated (`total_reserved − total_obligated`); `c` = obligated-but-not-yet-disbursed (`total_obligated − total_consumed`); `d` = disbursed (`total_consumed`); `e` = total locked = `b + c + d = total_reserved`; `f` = `Current Budget (a) − e`. When obligate and consume fire together (PO), `c` stays ~0; when separated in time (procurement instalments), `c` carries the standing obligation.
_Avoid_: spent (ambiguous between c, d, e)
