# KMITL Project

Institutional project/activity planning (โครงการ/กิจกรรม) for KMITL. A project is authored against a project-type budget code, is then **allocated budget into its own dimension by งานแผน** (ปรับเข้าแผน), reserves that allocation as a shared `budget.commitment` inside an **e-Saraban-routed approval**, and is finally spent down through purchase requests and disbursements — behaving like a procurement plan from the reserve point onward. See [ADR-0006](./docs/adr/0006-project-allocation-before-reserve.md).

## Language

**Project (โครงการ/กิจกรรม)**:
The default kind of `kmitl.project` (`project_type = project`) — a unit of planned activity with objectives, targets, outputs and a budget envelope. Does not require strategic-plan alignment.
_Avoid_: activity (the record is the whole โครงการ/กิจกรรม, not a single กิจกรรม)

**Strategic Project (โครงการยุทธศาสตร์)**:
A `kmitl.project` with `project_type = strategic_project` — same shape as a Project but must align to all four strategic-plan levels (national → master → NESDC → KMITL).
_Avoid_: strategic plan (that names the `project.strategic.plan` it aligns to, not the project)

**Project Approval (ขออนุมัติจัดโครงการและค่าใช้จ่าย)**:
The formal authorization a project obtains before it may execute — a หนังสือ (e-Saraban Document) requesting approval to *run the project and incur its expenses*, routed through the endorsement/signing chain. The project reserves its budget first, then raises the หนังสือ; when the หนังสือ is signed the project is authorized and **execution begins immediately** (it may raise purchase requests and disbursements at once — there is no idle "approved, not started" resting state). Carried on `kmitl.project` itself (the project *is* the approvable entity) through the `kmitl_project_sarabun` bridge, mirroring [Approval Request](../agx_approval/CONTEXT.md)'s approval front.
_Avoid_: approval request (that is the separate `agx_approval` เอกสาร; a project carries its **own** approval states — it does not spawn an `approval.request`)

**Project Allocation (ปรับเข้าแผน)**:
The act by งานแผน of moving budget **into a project's own `kmitl_project` dimension** — a `budget.transfer` whose destination carries the project's analytic dim on top of the four base dimensions, turning pool/floating money into money earmarked at the project. It is what a project waits for in `to_verify` and what makes its (computed) **Project Budget** rise above zero and unlock the จองงบ step. Distinct from budget's **Initial Appropriation** (funding a code at year start) and generic **Budget Transfer** (a move between codes with no project meaning). See [ADR-0006](./docs/adr/0006-project-allocation-before-reserve.md); the transfer's project-dimension support ships in branch `budget-transfer-multi-dimension`.
_Avoid_: allocation (unqualified — clashes with budget's appropriation sense), funding (clashes with the กองทุน/fund dimension), appropriation

**Project Budget (`budget_amount`)**:
The amount a project actually **received via Project Allocation** — a *computed* mirror of Current Budget (a) at the project's own dimension (the net of every posted budget move carrying its `kmitl_project` dim), so it always reads the current, real figure and is never typed by hand. Reserved as one shared `budget.commitment` at the **จองงบ step** (state `to_verify → to_send`, *before* the ขออนุมัติ หนังสือ is sent) and **released if the approval is rejected**; drawn down by the project's purchase requests and disbursements. Reads 0 (shown as "ยังไม่ได้รับการจัดสรรงบประมาณ") until งานแผน allocates. See [budget » Reserve / Floating Budget](../budget/CONTEXT.md).
_Avoid_: allocation, cost; the **Project Budget Plan** total (`budget_expense_total`, the project's *ask*, a different quantity — the two are never reconciled automatically)

**Project Number (เลขที่รันโครงการ, `key`)**:
A sequential running number that identifies a Project. Minted once, when the project is **submitted to งานแผน** (`draft→to_verify`, ส่งเข้าแผน — the moment its analytic account is created and its budget target is locked, ahead of the allocation), and stable for the project's life — a later reset-to-draft never re-issues or clears it. Stamped with the project's **fiscal year** (`account_fiscal_year_id`), which stays freely editable while the project is a first draft and is frozen once a Project Number exists. Reused as the `code` of the project's analytic account.
_Avoid_: Project Code (รหัสโครงการ) — a distinct approval-time identifier, **not yet implemented**; do not conflate it with the Project Number even though both currently share the `key` field.

**Project Budget Remaining (งบประมาณคงเหลือ)**:
A project's reserved `budget_amount` minus what has actually been **consumed (เบิกจ่าย)** from its commitment — the project money still available to spend. It is the project's own reservation-vs-spend, **not** the budget account's disbursement *Remaining (f)*, and **not** the พ.1 planning headroom (`budget_amount − Σ estimated_cost`) that caps how many purchase requests a project may raise.
_Avoid_: remaining (unqualified — clashes with [budget » Remaining (f)](../budget/CONTEXT.md))

**Project Budget Plan (แผนงบประมาณโครงการ)**:
The project's own itemised plan of expected income (รายรับ) and expenses (รายจ่าย), kept for internal management of the project. Realised as `project.budget.line` records whose identity is a **free-text `name`** typed by the planner (a catalog **Budget Item** may optionally be picked to pre-fill it — ADR-0004). Expenses are always planned and grouped into nested **ประเภทงบ** sections that follow the ประเภทงบ hierarchy (each level with its own roll-up subtotal in its header and its own "add line" action); income is optional per project (the `has_income` flag) and kept as one flat list. A line's amount is entered manually — never computed from the item's unit price (ADR-0002). Independent of the [budget](../budget/CONTEXT.md) engine and of the **Project Budget** (`budget_amount`) envelope — the two are never reconciled automatically.
_Avoid_: Project Budget / งบประมาณ (that names the reserved `budget_amount` envelope, a different thing); budget (the appropriation engine); the monthly spending schedule (`project.plan`, แผนการดำเนินงานและแผนการใช้จ่ายงบประมาณ) — a separate concept on its own tab

**Budget Item (รายการงบประมาณ)**:
An **optional**, reusable, flat catalog entry (`project.budget.item`) a Project Budget Plan line may pick to pre-fill its free-text `name` (and its ประเภทงบ / reference unit & unit price) — classified income or expense. Lines are not required to reference one; the expense catalog ships empty and managers may populate it (ADR-0004). An expense catalog item is filed under one **ประเภทงบ** (`category_id`); an income item has none. Its `complete_name` shows the "ประเภทงบ / รายการ" path but the line's picker displays just the leaf name.
_Avoid_: expense item (income items exist too); product (not a `product.product`); treating the item as required (it is an optional convenience — see ADR-0004); treating the item as the category (the ประเภทงบ tree is a separate model — see ADR-0003)

**ประเภทงบ (Budget Type category)**:
The expense budget-type classification — งบบุคลากร (personnel), งบดำเนินงาน (operating), งบเงินอุดหนุน (subsidy) and their sub-levels — its **own hierarchical master-data model** `project.budget.category` (up to three levels in practice; seeded two deep, e.g. งบดำเนินงาน → ค่าใช้สอย). A Project Budget Plan expense line is filed under one via `category_id` — set directly on the line, defaulted from the section it is added under, or copied from a picked **Budget Item**. They divide the expense side of a Project Budget Plan into nested, subtotalled sections. Income has no ประเภทงบ.
_Avoid_: the `budget_type` field on `project.budget.line`/`project.budget.item` (that is the income-vs-expense axis, a different thing); `budget.account`'s `budget_type` (expense vs revenue, unrelated); the former roots of `project.budget.item` (ประเภทงบ is now its own model, not item roots)
