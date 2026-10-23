# KMITL Project

Institutional project/activity planning (โครงการ/กิจกรรม) for KMITL. A project is authored against a project-type budget code, is then **allocated budget into its own dimension by งานแผน** (ปรับเข้าแผน), confirms that allocation, obtains an **e-Saraban-routed approval**, reserves the allocation as a shared `budget.commitment` the moment it is approved, and is finally spent down through purchase requests and disbursements — behaving like a procurement plan from the reserve point onward. See [ADR-0006](./docs/adr/0006-project-allocation-before-reserve.md) and [ADR-0010](./docs/adr/0010-project-reserves-on-approval.md).

## Language

**Project (โครงการ/กิจกรรม)**:
The default kind of `kmitl.project` (`project_type = project`) — a unit of planned activity with objectives, targets, outputs and a budget envelope. Does not require strategic-plan alignment.
_Avoid_: activity (the record is the whole โครงการ/กิจกรรม, not a single กิจกรรม)

**Strategic Project (โครงการยุทธศาสตร์)**:
A `kmitl.project` with `project_type = strategic_project` — same shape as a Project but must align to all four strategic-plan levels (national → master → NESDC → KMITL).
_Avoid_: strategic plan (that names the `project.strategic.plan` it aligns to, not the project)

**Project Approval (ขออนุมัติจัดโครงการและค่าใช้จ่าย)**:
The formal authorization a project obtains before it may execute — a หนังสือ (e-Saraban Document) requesting approval to *run the project and incur its expenses*, routed through the endorsement/signing chain. The project confirms its allocated budget first, then raises the หนังสือ; when the หนังสือ is signed the project is authorized, its budget is reserved, and **execution begins immediately** (it may raise purchase requests and disbursements at once — there is no idle "approved, not started" resting state). Carried on `kmitl.project` itself (the project *is* the approvable entity) through the `kmitl_project_sarabun` bridge, mirroring [Approval Request](../agx_approval/CONTEXT.md)'s approval front.
_Avoid_: approval request (that is the separate `agx_approval` เอกสาร; a project carries its **own** approval states — it does not spawn an `approval.request`)

**Project Allocation (ปรับเข้าแผน)**:
The act by งานแผน of moving budget **into a project's own `kmitl_project` dimension** — a `budget.transfer` whose destination carries the project's analytic dim on top of the four base dimensions, turning pool/floating money into money earmarked at the project. It is what a project waits for in `to_verify` and what makes its (computed) **Project Budget** rise above zero and unlock the ยืนยันงบ step. Distinct from budget's **Initial Appropriation** (funding a code at year start) and generic **Budget Transfer** (a move between codes with no project meaning). See [ADR-0006](./docs/adr/0006-project-allocation-before-reserve.md); the transfer's project-dimension support ships in branch `budget-transfer-multi-dimension`.
_Avoid_: allocation (unqualified — clashes with budget's appropriation sense), funding (clashes with the กองทุน/fund dimension), appropriation

**Direct Floating Allocation (จัดสรรงบประมาณ (งบลอย))**:
A **Project Allocation** a Budget User makes from the project itself, drawing the **Floating Budget** pool that already covers the project's own coordinate (its รหัสงบ + four dimensions, or the coarser pool above them) and taking effect at once — no หนังสือขออนุมัติโอนงบประมาณ, no approval step. In the ledger it is still an ordinary Budget Transfer (FROM the pool, TO the project's dimension), so it shows as รับโอนเข้า among the **Project Budget Movements**. Available from ส่งเข้าแผน until the project closes and may be repeated to top up. See [ADR-0009](./docs/adr/0009-direct-floating-allocation-skips-transfer-approval.md).
_Avoid_: quick transfer, งบลอย as the name of the pool (the pool is the Floating Budget / เงินลอย; "งบลอย" only labels this action)

**Floating Return (โอนคืนงบลอย)**:
The reverse of a **Direct Floating Allocation**: a Budget User sends money that sits at the project's dimension back to the **Floating Budget** pool covering the project's own coordinate (its รหัสงบ + four dimensions — the pool a Direct Floating Allocation draws from), taking effect at once — no หนังสือขออนุมัติโอนงบประมาณ. Money that is reserved but not yet obligated comes out of the reservation in the same move; money obligated, consumed or claimed by the project's พ.1 / ใบขออนุมัติ / ใบขอเบิก cannot be returned. It is the only way to clear a project's **Held Money**, so it is what a project needs before it can be deleted or retargeted. Not possible while the ขออนุมัติ หนังสือ quotes the budget (`to_send`, `sent`). In the ledger it is an ordinary Budget Transfer, shown as โอนออก among the **Project Budget Movements**. See [ADR-0011](./docs/adr/0011-project-deletion-replaces-cancel.md).
_Avoid_: refund / คืนเงิน (money already spent is never returned this way); คืนจอง (that only releases a reservation and leaves the money at the project)

**Supported Project (โครงการที่มีการสนับสนุนจากหน่วยงานอื่น)**:
A project flagged as receiving budget from **another unit**. Its project dimension is opened to every unit (not just the owning one), so a supporting unit can raise a **Project Allocation** into it — always onto the project's **own** coordinate (the owning unit's ส่วนงาน/กิจกรรม/กองทุน + the project's dimension), never the supporter's. The flag only widens who may *pick* the project; it never moves where the money sits. See [ADR-0008](./docs/adr/0008-supported-project-opens-analytic-ou.md).
_Avoid_: shared / co-owned project (the project still belongs to one unit and its money sits at that unit's coordinate)

**Project Budget (`budget_amount`)**:
The amount a project actually **received via Project Allocation** — a *computed* mirror of Current Budget (a) at the project's own dimension (the net of every posted budget move carrying its `kmitl_project` dim), so it always reads the current, real figure and is never typed by hand. Confirmed at the **ยืนยันงบ step** (state `to_verify → to_send`, *before* the ขออนุมัติ หนังสือ is sent) and reserved as one shared `budget.commitment` **when the project is approved** (หนังสือ signed → `in_progress`; a failed reservation is noted in the chatter and retried from the project, [ADR-0010](./docs/adr/0010-project-reserves-on-approval.md)); drawn down by the project's purchase requests and disbursements. Reads 0 (shown as "ยังไม่ได้รับการจัดสรรงบประมาณ") until งานแผน allocates. See [budget » Reserve / Floating Budget](../budget/CONTEXT.md).
_Avoid_: allocation, cost; the **Project Budget Plan** total (`budget_expense_total`, the project's *ask*, a different quantity — the two are never reconciled automatically)

**Project Coordinator (ผู้ประสานงาน)**:
An internal user (`coordinator_ids`) who coordinates a project day to day. They are told of every **status** change, follow its chatter, and can be added or removed at any point in the project's life, because they are a contact, not part of the approved content; a removed coordinator also stops following it (unless still an owner). A project may have several. Each must be a KMITL Project user.
_Avoid_: Project Manager / หัวหน้าโครงการ (`manager_id`, the employee who leads the project, a different person and field)

**Project Owner (เจ้าของโครงการ)**:
Any of a project's หัวหน้าโครงการ, **Project Coordinator** or creator. A Project Owner has the project as **Own Project**: they read and edit it and all its tabs (still subject to each state's field locks), see it whatever their operating unit, and may raise its **Project Approval** หนังสือ. Project officers (Officer/Manager) may do all of this for every project in their own operating units. See [ADR-0008](./docs/adr/0008-project-owner-coordinator-extension.md).
_Avoid_: "Responsible" (the label of the creator field `creating_user_id`) as a synonym for owner

**Project Budget Estimate (งบประมาณโครงการ, `budget_estimate`)**:
The amount the project's author **sets out to raise** ("ตั้งเงินไว้ 1 ล้าน") — a hand-typed target, the yardstick against which the money actually received from Funding Units is tracked. Never moves money and is never reserved.
_Avoid_: Project Budget (that is the received, computed `budget_amount`); budget plan total

**Funding Unit (ส่วนงานต้นทาง)**:
The ส่วนงาน (`departments` dimension) on the **FROM side** of a transfer that moves money into a project's dimension — i.e. who the money came from. Each Funding Unit sends its support in **its own transfer**, so one transfer has exactly one Funding Unit. The transfer's OU (who keyed it, e.g. งานแผน on a unit's behalf) and the TO side's ส่วนงาน (always the project's own) never identify it.
_Avoid_: OU / operating unit (the operator, not the funder); beneficiary unit (budget's reservation term, ADR-0011)

**Project Budget Movements (การเคลื่อนไหวงบประมาณโครงการ)**:
The project's read-only list of every budget movement on its dimension, one row per movement line, each with a **Movement Kind**, a **Movement Status**, a signed amount (in positive, out negative), the **Funding Unit** on transfer rows and the source document on ตัดงบ rows. Reservations (จองงบ/ผูกพัน) are not movements and are not listed. Posted allocation, transfer and budget-entry rows net to the **Project Budget**. Readable without any budget rights by every **Project Owner** (from any operating unit) and by project officers. See [ADR-0007](./docs/adr/0007-project-budget-movements-instead-of-ledger-access.md).
_Avoid_: Funding Summary / เงินสนับสนุนที่ได้รับ (the earlier, inflow-only version of this list); budget move / ledger (this is a project-level view, not access to `budget.move`)

**Project Budget Overview (บัญชีโครงการ)**:
The one place a project's budget is followed and moved: its figures (**Project Budget** received, reserved, consumed and **Project Budget Remaining**, against the **Project Budget Estimate**), its **Project Budget Movements**, its reservation and the money actions open to the viewer. It covers the **budget** side only — everything that passes through the budget engine; whether a spending document has actually been paid is shown only as that document's status, never as a movement.
_Avoid_: GL / general-ledger account, bank account (บัญชีธนาคาร) — "บัญชี" here is the project's budget book, not accounting; Project Account (in Odoo "account" reads as accounting); ledger (the project's users still have no access to `budget.move`)

**Movement Kind (ประเภทการเคลื่อนไหว)**:
What a movement did to the project's money: **จัดสรร** (an appropriation), **รับโอนเข้า** / **โอนออก** (the TO / FROM side of a transfer), **บันทึกงบประมาณ** (a budget entry keyed directly by budget staff, not via a transfer) or **ตัดงบ** (consumption by a purchase request, disbursement or other spending document).
_Avoid_: ปรับปรุงงบ / adjustment for a budget entry (budget's Adjustment also covers transfers)

**Movement Status (สถานะการเคลื่อนไหว)**:
Whether a movement has taken effect: **ผ่านแล้ว** (posted), **อยู่ระหว่างดำเนินการ** (a transfer submitted, in e-Saraban or returned — not yet counted in the Project Budget; only transfers have this status), **ต่างปีงบประมาณ** (it carries the project's dimension in another fiscal year, e.g. carried-over เงินกันเหลื่อมปี and its spending — legitimate, but outside the project's year) or **พิกัดไม่ตรงกับโครงการ** (off-target: in the project's year, but its รหัสงบ or a base dimension misses the project's coordinate — likely mis-keyed). The last two count in no total yet stay visible. Draft, rejected and cancelled movements are not listed.
_Avoid_: received (only inflows are "received"; ตัดงบ rows are posted, not received)

**Project Number (เลขที่รันโครงการ, `key`)**:
A sequential running number that identifies a Project. Minted once, when the project is **submitted to งานแผน** (`draft→to_verify`, ส่งเข้าแผน — the moment its analytic account is created and its budget target is locked, ahead of the allocation), and stable for the project's life — a later reset-to-draft never re-issues or clears it. Stamped with the project's **fiscal year** (`account_fiscal_year_id`), which stays freely editable while the project is a first draft and is frozen once a Project Number exists. Reused as the `code` of the project's analytic account. A soft-deleted project keeps its number.
_Avoid_: Project Code (รหัสโครงการ) — a distinct approval-time identifier, **not yet implemented**; do not conflate it with the Project Number even though both currently share the `key` field.

**Project Deletion (ลบโครงการ)**:
The single way to take a project out of use. A project with no **Ledger Footprint** is deleted for good together with its analytic account; one that has a footprint but has never spent is **soft-deleted** — it becomes ยกเลิก (`cancel`) and both it and its analytic account are archived, and resetting it to draft brings both back with the same **Project Number**. A project that has spent money cannot be deleted; it is closed (ปิดโครงการ) instead. Deletion never moves money: it waits until the project holds no **Held Money**, has no open purchase request, approval request or disbursement, and has no หนังสือ circulating. A project with no Project Number may be deleted by any Project Owner; one with a number only by project officers. See [ADR-0011](./docs/adr/0011-project-deletion-replaces-cancel.md).
_Avoid_: cancel as a separate act (ยกเลิก is now only the state a soft-deleted project ends in)

**Ledger Footprint (ประวัติในบัญชีงบประมาณ)**:
Whether the project's analytic account has ever been recorded on any other document — a budget movement, a reservation, a transfer, a purchase request, in any state, even cancelled. A project with a footprint is part of the budget history, so its analytic account is kept (archived), never deleted.
_Avoid_: balance (a footprint can exist even when every figure nets to 0)

**Held Money (เงินค้างในมิติโครงการ)**:
Money still tied to the project's dimension: a non-zero net allocation on any coordinate in any fiscal year, an active reservation, or a transfer into or out of the dimension that is still in progress. While a project holds any, its รหัสงบ and budget dimensions cannot change and it cannot be deleted; a **Floating Return** clears it. Closing a project returns its unspent reservation (คืนจอง) but leaves the money held until a Floating Return.
_Avoid_: Project Budget Remaining (that is reserved minus spent, only one part of it)

**Project Budget Remaining (งบประมาณคงเหลือ)**:
The money still sitting at the project: its **Project Budget** (received) minus what has actually been **consumed (เบิกจ่าย)** on its coordinate. Meaningful in every state — before the reservation it equals the Project Budget; after closing it shows the leftover still held at the project's dimension until a **Floating Return**. Money received after spending began is counted here even though it is not yet reserved (and so not yet spendable through a พ.1) — the **Project Budget Overview** flags that gap. It is **not** reserved-minus-consumed, **not** the budget account's disbursement *Remaining (f)*, and **not** the พ.1 planning headroom (`budget_amount − Σ estimated_cost`) that caps how many purchase requests a project may raise.
_Avoid_: remaining (unqualified — clashes with [budget » Remaining (f)](../budget/CONTEXT.md)); the commitment form's คงเหลือ (reserved − obligated, one reservation's view)

**Project Budget Plan (แผนงบประมาณโครงการ)**:
The project's own itemised plan of expected income (รายรับ) and expenses (รายจ่าย), kept for internal management of the project. Realised as `project.budget.line` records whose identity is a **free-text `name`** typed by the planner (a catalog **Budget Item** may optionally be picked to pre-fill it — ADR-0004). Expenses are always planned and grouped into nested **ประเภทงบ** sections that follow the ประเภทงบ hierarchy (each level with its own roll-up subtotal in its header and its own "add line" action); income is optional per project (the `has_income` flag) and kept as one flat list. A line's amount is entered manually — never computed from the item's unit price (ADR-0002). Independent of the [budget](../budget/CONTEXT.md) engine and of the **Project Budget** (`budget_amount`) envelope — the two are never reconciled automatically.
_Avoid_: Project Budget / งบประมาณ (that names the reserved `budget_amount` envelope, a different thing); budget (the appropriation engine); the monthly spending schedule (`project.plan`, แผนการดำเนินงานและแผนการใช้จ่ายงบประมาณ) — a separate concept on its own tab

**Budget Item (รายการงบประมาณ)**:
An **optional**, reusable, flat catalog entry (`project.budget.item`) a Project Budget Plan line may pick to pre-fill its free-text `name` (and its ประเภทงบ / reference unit & unit price) — classified income or expense. Lines are not required to reference one; the expense catalog ships empty and managers may populate it (ADR-0004). An expense catalog item is filed under one **ประเภทงบ** (`category_id`); an income item has none. Its `complete_name` shows the "ประเภทงบ / รายการ" path but the line's picker displays just the leaf name.
_Avoid_: expense item (income items exist too); product (not a `product.product`); treating the item as required (it is an optional convenience — see ADR-0004); treating the item as the category (the ประเภทงบ tree is a separate model — see ADR-0003)

**ประเภทงบ (Budget Type category)**:
The expense budget-type classification — งบบุคลากร (personnel), งบดำเนินงาน (operating), งบเงินอุดหนุน (subsidy) and their sub-levels — its **own hierarchical master-data model** `project.budget.category` (up to three levels in practice; seeded two deep, e.g. งบดำเนินงาน → ค่าใช้สอย). A Project Budget Plan expense line is filed under one via `category_id` — set directly on the line, defaulted from the section it is added under, or copied from a picked **Budget Item**. They divide the expense side of a Project Budget Plan into nested, subtotalled sections. Income has no ประเภทงบ.
_Avoid_: the `budget_type` field on `project.budget.line`/`project.budget.item` (that is the income-vs-expense axis, a different thing); `budget.account`'s `budget_type` (expense vs revenue, unrelated); the former roots of `project.budget.item` (ประเภทงบ is now its own model, not item roots)
