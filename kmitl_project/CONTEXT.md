# KMITL Project

Institutional project/activity planning (โครงการ/กิจกรรม) for KMITL. A project is authored against a *floating* project-type budget code, reserves its full budget when confirmed, and is then spent down through purchase requests and disbursements — behaving like a procurement plan from the reserve point onward.

## Language

**Project (โครงการ/กิจกรรม)**:
The default kind of `kmitl.project` (`project_type = project`) — a unit of planned activity with objectives, targets, outputs and a budget envelope. Does not require strategic-plan alignment.
_Avoid_: activity (the record is the whole โครงการ/กิจกรรม, not a single กิจกรรม)

**Strategic Project (โครงการยุทธศาสตร์)**:
A `kmitl.project` with `project_type = strategic_project` — same shape as a Project but must align to all four strategic-plan levels (national → master → NESDC → KMITL).
_Avoid_: strategic plan (that names the `project.strategic.plan` it aligns to, not the project)

**Project Budget (`budget_amount`)**:
The full amount a project earmarks from its floating budget code. Reserved as one shared `budget.commitment` when the project is confirmed (`draft→new`); drawn down by the project's purchase requests and disbursements. See [budget » Reserve / Floating Budget](../budget/CONTEXT.md).
_Avoid_: allocation, cost

**Project Number (เลขที่รันโครงการ, `key`)**:
A sequential running number that identifies a Project. Minted once, when the project is first confirmed (`draft→new`), and stable for the project's life — a later reset-to-draft never re-issues or clears it. Stamped with the project's **fiscal year** (`account_fiscal_year_id`), which is therefore frozen once a Project Number exists. Reused as the `code` of the project's analytic account.
_Avoid_: Project Code (รหัสโครงการ) — a distinct approval-time identifier, **not yet implemented**; do not conflate it with the Project Number even though both currently share the `key` field.

**Project Budget Remaining (งบประมาณคงเหลือ)**:
A project's reserved `budget_amount` minus what has actually been **consumed (เบิกจ่าย)** from its commitment — the project money still available to spend. It is the project's own reservation-vs-spend, **not** the budget account's disbursement *Remaining (f)*, and **not** the พ.1 planning headroom (`budget_amount − Σ estimated_cost`) that caps how many purchase requests a project may raise.
_Avoid_: remaining (unqualified — clashes with [budget » Remaining (f)](../budget/CONTEXT.md))

**Project Budget Plan (แผนงบประมาณโครงการ)**:
The project's own itemised plan of expected income (รายรับ) and expenses (รายจ่าย), kept for internal management of the project. Realised as `project.budget.line` records on the project, each picking a catalog **Budget Item** (`project.budget.item`). Independent of the [budget](../budget/CONTEXT.md) engine and of the **Project Budget** (`budget_amount`) envelope — the two are never reconciled automatically.
_Avoid_: Project Budget / งบประมาณ (that names the reserved `budget_amount` envelope, a different thing); budget (the appropriation engine); the monthly spending schedule (`project.plan`, แผนการดำเนินงานและแผนการใช้จ่ายงบประมาณ) — a separate concept on its own tab

**Budget Item (รายการงบประมาณ)**:
A reusable catalog entry (`project.budget.item`) a Project Budget Plan line points at, classified income or expense and arranged in a hierarchy whose expense roots are the ประเภทงบ categories (งบบุคลากร/งบดำเนินงาน/งบอุดหนุน).
_Avoid_: expense item (income items exist too), product (not an `product.product`)
