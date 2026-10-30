# Approval Request (Expense Plan)

The expense-approval application (`agx_approval`): a requester fills a form to get an expense **approved before** the money is spent. The form-filling stage is framed as proposing an **expense plan** — what is planned to be spent and who is involved — not a settled bill. Approval is where the request's own work ends: the requester records nothing afterwards. Finance then disburses it over time through any number of ใบขอเบิก, each line paying one planned Expense, and reads the request's Remaining at a glance.

Approval itself is **routed through e-Saraban**: a submitted request spawns a หนังสือ that circulates for sign-off, and the หนังสือ's outcome drives the request's state (completed → approved, returned → returned, rejected → rejected). The internal approve button is not the approval path when the Sarabun bridge is installed.

## Language

**Approval Request (ใบขออนุมัติ)**:
The `approval.request` document: the plan, approved before the money is spent. Reserves budget on approval and is then disbursed against, never edited again.
_Avoid_: expense request, claim, bill

**Approval Category (ประเภทค่าใช้จ่าย)**:
A fine-grained expense type (`approval.category`), one per government budget code (~90 of them) — **not** a broad request kind. Decides whether its requests itemize: by default a request of the category carries **one** Expense (a single amount); a category that **has Expense Items** (มีรายการค่าใช้จ่ายย่อย) lets the requester break the plan down into several Expenses, each naming one of the category's own Expense Items. Also **scopes** what a request of that kind may use — allowed people, and its **budget code**: when it pins a budget code that code becomes the request's constraint (not just a default); when it leaves the code blank the request selects freely from the **Approval-eligible Budget Codes**.
_Avoid_: request type, request kind, template, budget preset; product (categories no longer own a product)

**Expense Item (รายการค่าใช้จ่ายย่อย)**:
A named kind of spending configured **on one category and owned by it** — never shared across categories (e.g. ค่ารับรองและพิธีการ → อาหารว่างและเครื่องดื่ม, อาหารกลางวัน, ของที่ระลึก). Exists only on a category that has Expense Items; an Expense of such a category names one, and several Expenses may name the same one (e.g. อาหารว่าง เช้า and บ่าย). Retired by deactivating, never deleted, since past requests name it. Carries no rate limit. Not a product.
_Avoid_: product, sub-product, รายการย่อย (the old name of the travel/training product pick-list)

**Other Expense (อื่น ๆ)**:
An Expense of a category with Expense Items that names none of them: the requester picks อื่น ๆ and types what it is (ระบุรายการ), separately from its รายละเอียด. Shown as "อื่น ๆ: <what was typed>" so it reads as non-standard. Allowed per category (on by default); typing one never adds an Expense Item — an administrator does that.
_Avoid_: a free-text Expense Item, an auto-learned item

**Approval-eligible Budget Code (รหัสงบที่ใช้ในคำขออนุมัติได้)**:
A budget code an administrator has explicitly marked usable from a ใบขออนุมัติ. Independent of whether it is also a procurement code: a code may be usable from a ใบขอซื้อ, from a ใบขออนุมัติ, from both, or from neither. See [ADR-0004](docs/adr/0004-budget-code-selection-scoped-by-category-non-procurement.md) (amended).
_Avoid_: non-procurement code (the old rule; procurement codes may now be approval-eligible too)

**Expense Plan (แผนค่าใช้จ่าย)**:
The planned spending captured while filling the form — the purpose of the entry stage. What is approved and what budget is reserved against.
_Avoid_: budget, estimate, quotation

**Expense (ค่าใช้จ่าย)**:
A single **planned** line of the Expense Plan: จำนวนเงิน (amount) + an optional free-text รายละเอียด (where the requester writes how it adds up, e.g. 20 คน × 50), plus its Expense Item when the category has them. Carries **no payee** — it says what is spent, not who is paid. A request of a category without Expense Items has exactly one Expense; a category with them has as many as the requester itemizes. The unit finance disburses against: every ใบขอเบิก line pays one Expense.
_Avoid_: request line, payee line, actual expense, product line

**Spending Ceiling (เพดานค่าใช้จ่าย)**:
On a request whose category has Expense Items, the จำนวนเงิน the requester declares up front; its Expenses must add up to exactly this amount before the request can move to the next step. Otherwise จำนวนเงิน is simply the one Expense's amount. Equals the Approved Amount once approved.
_Avoid_: budget limit, reserved amount (that is the ใบจองงบประมาณ's)

**Participant (รายชื่อ)**:
A person involved in the activity — traveller, attendee, or related person — listed on the plan (person + note, no bank, no amount). Not a payee list: who is paid is decided by finance on the ใบขอเบิก.
_Avoid_: payee, recipient (ผู้รับเงิน)

**Finance-authored Disbursement (ใบขอเบิกที่การเงินตั้ง)**:
A ใบขอเบิก a disbursement user raises against an approved request — from the request itself (สร้างใบขอเบิก) or from the ใบขอเบิก side by naming it (อ้างอิงใบขออนุมัติ). References **exactly one** request, whose reservation, budget code and dimensions it inherits. A request may have **many**, raised over time — it is not cleared in one go. Its payee lines (who receives the money) are kept apart from its **Expense breakdown** (ค่าใช้จ่ายที่ขอเบิก): the recipient is not always the one who spent — it may be someone who advanced or borrowed the money — so the ใบขอเบิก states separately which of the request's Expenses it covers, with an explanation and amount each, adding up to its total. With a single Expense the breakdown is that Expense. Whoever may read a ใบขอเบิก may also read the request it references — read-only, its attachments included — so a reviewer in another unit sees what was approved. Disbursement evidence (receipts) is attached to each ใบขอเบิก, not to the request. The requester records nothing after approval: there is no actual-expense step on the request.
_Avoid_: billing the request, one DR per request, actual expense (ค่าใช้จ่ายจริง — the removed post-mission record)

**Approved Amount (ยอดอนุมัติ)**:
What this request may spend in total: its **Expense Plan total** — the cap on its ใบขอเบิก. For a request that reserved its own budget this equals its reservation; for one drawing from a shared reservation (a project's or procurement plan's) it is only this request's share of it, so the cap is the request's own guard, not the budget engine's. Never raised after approval: spending beyond it is not the request's to cover — there is no top-up or amendment.
_Avoid_: the reservation's total (จองเงิน) — shared reservations are larger than any one request

**Disbursed (เบิกจ่ายแล้ว)**:
The part of a request's ใบขอเบิก whose budget has been **consumed** (ตัดงบแล้ว). Not "paid": payment may still be pending.
_Avoid_: paid (จ่ายเงินแล้ว), billed

**In-progress Disbursement (อยู่ระหว่างเบิก)**:
Non-cancelled ใบขอเบิก of a request whose budget is **not yet consumed**, drafts included — held so concurrent ใบขอเบิก cannot overspend the request.
_Avoid_: pending payment

**Remaining (คงเหลือ)**:
Approved Amount − Disbursed − In-progress Disbursement − what was given back at Close, per request and per Expense — so a Completed request always reads zero. A single Expense may go below zero when finance shifts money between the request's Expenses (เกลี่ยระหว่างรายการ). The request as a whole may dip below zero only while a draft ใบขอเบิก overshoots — shown in red; no ใบขอเบิก can be submitted that leaves it below zero. Counted on each ใบขอเบิก's total as the budget consumes it (VAT included, before withholding tax).
_Avoid_: คงเหลือเบิกได้, available budget (the budget engine's figure), ถัวจ่าย (that is the budget module's multi-code cross-charge)

**Open for Disbursement (รอเบิก)**:
An approved request not yet Completed: finance may still raise ใบขอเบิก against it. Finance finds such requests itself, from the paperwork the requester sends in — the request raises no To-Do of its own. The requester is told (FYI) as its ใบขอเบิก are disbursed and when it closes.
_Avoid_: to_disburse / รอการเงินตรวจสอบ (the superseded hand-off state the requester triggered)

**Close (ปิดคำขอ)**:
Ending a request's disbursing: it becomes **Completed (เสร็จสิ้น)** and no further ใบขอเบิก may reference it. Happens by itself when Remaining reaches zero; otherwise finance closes it by hand once nothing is In-progress, which **returns the request's Remaining** to the budget (ส่งคืนเงินเหลือจ่าย, the budget module's คืนจอง) — only for a request that reserved its own budget. A request drawing from a shared reservation (a project's or procurement plan's) returns nothing: its Remaining simply stays in the shared reservation for the owner to use or return. Money a consumed ใบขอเบิก frees after the close (cancelled later) is given back the same way at once, so the request stays Completed and reads zero. A finance manager may reopen a Completed request, unless its leftover was already returned — that money is back in the pool, so a new request is needed instead.
_Avoid_: ตั้งเบิกครบแล้ว / billed (the superseded one-shot close), cancel

**Awaiting Verification (รอตรวจสอบข้อมูล — `to_verify`)**:
The step after ส่งคำขอ where the Request Verifier checks the request and may fill in the budget code and dimensions, which need not be complete yet. Ends with ยืนยันตรวจสอบ (to the next step) or ตีกลับ (to draft).
_Avoid_: รอตรวจสอบ / จองงบประมาณ (the old combined step), reserve step

**Awaiting Budget Confirmation (รอยืนยันงบประมาณ — `to_commit`)**:
The step after verification where the Budget Confirmer completes the budget code and dimensions and presses ยืนยันงบประมาณ, which reserves the budget and moves the request on to รอส่งขออนุมัติ. ตีกลับ returns it to รอตรวจสอบข้อมูล.
_Avoid_: รอตรวจสอบ / จองงบประมาณ, verify step

**Request Verifier (ผู้ตรวจสอบคำขอ)**:
The person who confirms a submitted request's data at รอตรวจสอบข้อมูล. May enter budget code and dimensions but **cannot reserve budget**. A separate duty from the Budget Confirmer: holding one does not grant the other.
_Avoid_: budget officer, เจ้าหน้าที่งบ

**Designated Verifier (ผู้ตรวจสอบที่ระบุ)**:
The one Request Verifier the requester names on a request, from those assigned to the request's operating unit. Advisory: it routes the รอตรวจสอบข้อมูล Todo to that person, but any Request Verifier may still confirm or send back. Must be named before ส่งคำขอ.
_Avoid_: Request Verifier (that is the role, held by many), approver

**Designated Budget Confirmer (ผู้ยืนยันงบประมาณที่ระบุ)**:
The one Budget Confirmer named on a request, from those assigned to the request's operating unit. Advisory like the Designated Verifier: it routes the รอยืนยันงบประมาณ Todo to that person instead of the role broadcast, but any Budget Confirmer may still reserve or send back. Must be named before ยืนยันตรวจสอบ.
_Avoid_: Budget Confirmer (that is the role, held by many)

**Budget Confirmer (ผู้ยืนยันงบประมาณ)**:
The person who, at รอยืนยันงบประมาณ, completes the budget code and dimensions and reserves the budget. The only role that reserves on an Approval Request.
_Avoid_: verifier, budget officer (ambiguous with the budget module's own roles)

**Send back (ตีกลับ — verification steps)**:
The Request Verifier or Budget Confirmer returning a request one step back, with a mandatory reason: รอยืนยันงบประมาณ → รอตรวจสอบข้อมูล, or รอตรวจสอบข้อมูล → draft. **Distinct** from Pull back (the requester's own action) and from e-Saraban's ตีกลับ (which lands a circulating request in `returned`).
_Avoid_: pull back, reject, returned

**Pull back (ดึงกลับ — pre-routing)**:
The clerk returning a *not-yet-sent* request to `draft` (via a confirm wizard, releasing the budget reservation), available only before the หนังสือ is sent to e-Saraban. **Distinct** from e-Saraban's own ดึงกลับ/ตีกลับ, which act on a *circulating* หนังสือ and land the request in `returned`.
_Avoid_: recall (that is e-Saraban's, on a circulating document), reset

**Budget Selection Mode (วิธีเลือกงบประมาณ)**:
The up-front choice of how a request gets its budget (`budget_selection_mode`). Base ships **`normal`** (ใช้เงินจากแผน — reserve a new commitment against a budget code and dimensions entered directly on the form, scoped to Approval-eligible Budget Codes and any pinned code, [ADR-0004](docs/adr/0004-budget-code-selection-scoped-by-category-non-procurement.md)). A bridge (`kmitl_project_agx_approval`) adds **`project`** (โครงการ/กิจกรรม — draw down a commitment a `kmitl.project` already reserved for itself; the category pin does not apply). A UI affordance only — the server always keys draw-down off `reservation_commitment_id`, never off this field.
_Avoid_: the removed generic "draw any existing reservation" mode — each mode now scopes its own draw-eligible slips

**Project-Funded Request (คำขอใช้งบโครงการ)**:
An approval request in `project` mode. Its money was already authorized when the `kmitl.project` itself was approved (kmitl_project [ADR-0005](../kmitl_project/docs/adr/0005-approval-gated-lifecycle-esaraban.md)), so spending it is bookkeeping, not a fresh authorization — the request **skips e-Saraban entirely**, jumping `to_commit → approved` on draw ([ADR-0005](docs/adr/0005-project-mode-auto-approve-skips-esaraban.md)). No expense-side manager approval, no หนังสือ, no expense-side PDF (the project's own letter is the authority). Drawable only from a project in `in_progress` — a project reserves its slip *before* its own approval, so the slip alone is not the authorization the skip relies on.
_Avoid_: assuming every request routes through e-Saraban when the Sarabun bridge is installed — project mode is the one path that deliberately does not; and assuming any reserved project slip is drawable — the project must be approved first

**Requesting Unit (หน่วยงานผู้ขอ)**:
The unit the requester files the expense under (`requesting_department_id`), declared at entry — required while the plan is editable, defaulting to the current user's most recently used unit. Distinct from the budget dimension ส่วนงาน (`department_analytic_id`, the charged unit chosen by the Request Verifier / Budget Confirmer, and overwritten by the mode switch/project draw-down): the two may differ, e.g. a project-funded request charged to the project's own ส่วนงาน while the requester still belongs to their own unit. No check compares them. See [ADR-0007](docs/adr/0007-requesting-unit-separate-from-budget-department.md).
_Avoid_: ส่วนงาน/department (ambiguous with the budget dimension), OU
