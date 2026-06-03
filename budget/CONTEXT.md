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
A node in the hierarchical chart of budget codes (`budget.account`). Carries a `budget_type` (revenue / expense) and rolls up parent→child. The default (innermost) row axis of budget reports; the monitoring dashboard can optionally nest it under a financial dimension such as Activity.
_Avoid_: account (ambiguous with `account.account`), category

**Activity (กิจกรรม, `activity_analytic_id`)**:
One of the six financial dimensions (the `activities` analytic plan) — a hierarchical program classification whose levels read ด้าน → แผนงาน → กิจกรรม → กิจกรรมย่อย, so a node's kind depends on its depth. Carried on move/commitment lines; used as a report filter and as the optional outer row axis of the monitoring dashboard.
_Avoid_: ด้าน/แผนงาน/กิจกรรม (the descriptive long form — prefer the short label "กิจกรรม"), program, task

**Budget Pool**:
The appropriated money available on a budget account for a fiscal year, before any commitment activity. Built up from appropriation and transfer moves.
_Avoid_: allocation (reserve "allocation" for the initial act of appropriating)

**Floating Budget (เงินลอย)**:
The appropriated pool on a *project-type* budget account (`is_project`) that has been posted but not yet reserved by any project. It carries the four dimensions (activities/departments/funds/sources) but **no `kmitl_project` dimension** — projects are authored later and reserve against it. The procurement-plan path has no floating stage (it reserves the instant its appropriation posts); the project path deliberately does (ADR-0007).
_Avoid_: unallocated budget, งบคงเหลือ (that is Remaining (f), a different quantity)

**Budgetable (ระบุงบประมาณได้, `budgetable`)**:
A budget account where budget may be specified — both reserved against and appropriated to. Reservations are restricted to budgetable accounts; it is the flag that marks a node as a legitimate place to control budget.
_Avoid_: leaf, allocatable

**Cross-charge (ถัวจ่าย, `cross_chargeable`)**:
Pooling more than one budget code inside a *single* reservation. A reservation normally carries one budget code; it may carry several reserve lines only when every line's budget account is flagged `cross_chargeable`. The flag alone governs eligibility — flagged codes may be pooled together regardless of category.
_Avoid_: transfer (that is `budget.transfer`, a balanced move *between* accounts; cross-charge moves nothing — it spends several pools in one reservation), virement

**Control Node (โหนดคุมงบ)**:
The budgetable account at which a reservation's pool is actually controlled — the nearest budgetable ancestor-or-self of the reserved account that carries appropriation. A reservation draws from its control node, and all usage in that node's subtree rolls up to it. Mostly the control node *is* the reserved account itself; for coarsely-budgeted lines (personnel, project) it is an ancestor. Appropriation may sit at or above the reservation node, **never below** it (one-way, up only). The same nearest-funded-ancestor rule applies independently on each hierarchical analytic dimension (resolved from `account.analytic.account` parent paths; flat dimensions like Source match exactly).
_Avoid_: parent, category (those name tree position, not the control role)

**Available (งบที่จองได้)**:
Remaining (f) evaluated at the control node — the amount a new reservation may draw. The figure the reservation check enforces and the picker shows on a row.
_Avoid_: remaining (keep "remaining" for the report column; "available" is the reservation-time check at the control node)

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
Earmarking pool against a commitment; a `reserve` ledger line. **Timing depends on the allocation path.** For a *procurement plan* it fires the moment its source budget **appropriation is posted** — reserving the full `total_price` at once (not at *ready*; see ADR-0005). For a *project* the appropriation leaves the pool **floating** (see Floating Budget) and the reserve fires later, when the `kmitl.project` is confirmed (`draft→new`), reserving its full `budget_amount` — a deliberate divergence from the procurement-plan timing in ADR-0005 (see ADR-0007).
_Avoid_: allocate, commit

**Obligate (ผูกพัน)**:
Binding earmarked money to an obligation (contract / PO / disbursement request). An `obligate` ledger line, posted before its matching consume.
_Avoid_: encumber, commit

**Consume (ตัดงบ / เบิกจ่าย)**:
The actual disbursement — money leaves the pool for good. A `consume` ledger line.
_Avoid_: spend, pay, disburse (pick "consume" in code, "เบิกจ่าย" in UI)

**Reserved (b) / Obligated (c) / Disbursed (d) / Used (e) / Remaining (f)**:
The disbursement waterfall for an account: `b` = reserved-but-not-yet-obligated (`total_reserved − total_obligated`); `c` = obligated-but-not-yet-disbursed (`total_obligated − total_consumed`); `d` = disbursed (`total_consumed`); `e` = total locked = `b + c + d = total_reserved`; `f` = `Current Budget (a) − e`. Both KMITL flows fire obligate and consume **together** — the PO flow, and the procurement-plan flow (per งวด at each disbursement request) — so `c` stays ~0 in practice. The not-yet-disbursed remainder of a reserved procurement plan therefore sits in `b` (reserved-but-not-obligated), **not** `c`. `c` only carries a standing balance if some flow posts an obligate without an immediate matching consume (a capability the ledger supports but no current flow uses).
_Avoid_: spent (ambiguous between c, d, e)
