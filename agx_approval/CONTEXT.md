# Approval Request (Expense Plan)

The expense-approval application (`agx_approval`): a requester fills a form to get an expense **approved before** the money is spent. The form-filling stage is framed as proposing an **expense plan** — what is planned to be spent and who is involved — not a settled bill. After the mission the requester records only **what was actually spent** (item, description, amount) plus evidence; who is paid, how, and on which ใบขอเบิก is decided by finance, who bills the request into one or more disbursements ([ADR-0009](docs/adr/0009-finance-authors-disbursements-from-actuals.md)).

Approval itself is **routed through e-Saraban**: a submitted request spawns a หนังสือ that circulates for sign-off, and the หนังสือ's outcome drives the request's state (completed → approved, returned → returned, rejected → rejected). The internal approve button is not the approval path when the Sarabun bridge is installed.

## Language

**Approval Request (ใบขออนุมัติ)**:
The `approval.request` document. Spans two moments of one activity: the **plan** (approved before the money is spent) and the **actual expense record** (filled after the mission, before billing). Reserves budget on approval.
_Avoid_: expense request, claim, bill

**Approval Category (ประเภทค่าใช้จ่าย)**:
A fine-grained expense type (`approval.category`), one per government budget code (~90 of them) — **not** a broad request kind. The category **owns its product**: single-product by default (`multi_product = False`, exactly one `allowed_product_ids`), so the product is a foregone conclusion the user never picks. A handful (5) of travel/training categories set `multi_product = True` and expose a small pick-list of sub-items (ค่าหลักสูตร/ค่าเดินทาง/ค่าเบี้ยเลี้ยง/ค่าที่พัก/อื่นๆ) instead. Also **scopes** what a request of that kind may use — allowed people, and its **budget code**: when it pins a budget code that code becomes the request's constraint (not just a default); when it leaves the code blank the request selects freely from the non-procurement expense codes. See [ADR-0006](docs/adr/0006-category-owned-product-single-product-plan.md).
_Avoid_: request type, request kind, template, budget preset

**Expense Plan (แผนค่าใช้จ่าย)**:
The planned spending captured while filling the form — the purpose of the entry stage. What is approved and what budget is reserved against.
_Avoid_: budget, estimate, quotation

**Expense (ค่าใช้จ่าย)**:
A single **planned** line (`approval.request.line`): รายการ (product) + รายละเอียด (detail) + จำนวนเงิน (planned amount). Broken down **by expense type, not by person**, and carries **no payee** — a plan line says what is spent, not who is paid. For a single-product category the product is implicit (the category's own product) and the form shows only a bare จำนวนเงิน (`plan_amount`) on the header, mirrored onto this line behind the scenes; the per-line product picker is shown **only** for the 5 multi-product (travel/training) categories, where จำนวนเงิน is instead the Spending Ceiling ([ADR-0006](docs/adr/0006-category-owned-product-single-product-plan.md)).
_Avoid_: request line, payee line, actual expense

**Spending Ceiling (เพดานค่าใช้จ่าย)**:
On a multi-product request, the จำนวนเงิน the requester declares up front; the plan lines must add up to exactly this amount before the request can move to the next step. On a single-product request จำนวนเงิน is simply the one line's amount.
_Avoid_: budget limit, reserved amount (that is the ใบจองงบประมาณ's)

**Participant (รายชื่อ)**:
A person involved in the activity — traveller, attendee, or related person — listed on the plan (person + note, no bank, no amount). Not a payee list: who is paid is decided by finance on the ใบขอเบิก.
_Avoid_: payee, recipient (ผู้รับเงิน)

**Actual Expense Allocation (ค่าใช้จ่ายจริง)**:
The after-mission record the requester enters on the request: rows of (expense product from the plan, description, **actual** amount), plus request-level evidence files. Carries **no recipient, bank or payment type** — it says what was spent, not who is paid. Bounded by the plan per product and by the reserved budget in total, and it caps what finance may bill.
_Avoid_: expense plan (the pre-spend estimate), recipient row, payee, payment type (those live on the ใบขอเบิก)

**Finance-authored Disbursement (ใบขอเบิกที่การเงินตั้ง)**:
A ใบขอเบิก that a disbursement user creates from a request in รอการเงินตรวจสอบ/ส่งเบิก. A request may have **many**; each starts with the request's header (reservation, budget code, dimensions) and no lines, and finance enters recipients, items, amounts, banks and its payment type. Together the non-cancelled ones may not exceed the request's actual total — less is normal.
_Avoid_: billing the request (that is closing), one DR per request

**Close billing (ตั้งเบิกครบแล้ว)**:
Finance declaring that every ใบขอเบิก for a request has been created; moves the request to `billed` and stops further ใบขอเบิก. Does **not** return the unused reservation — that is คืนจอง on the ใบจองงบประมาณ, done separately by budget staff.
_Avoid_: auto-billing, คืนจอง

**Awaiting Verification (รอตรวจสอบข้อมูล — `to_verify`)**:
The step after ส่งคำขอ where the Request Verifier checks the request and may fill in the budget code and dimensions, which need not be complete yet. Ends with ยืนยันตรวจสอบ (to the next step) or ตีกลับ (to draft).
_Avoid_: รอตรวจสอบ / จองงบประมาณ (the old combined step), reserve step

**Awaiting Budget Confirmation (รอยืนยันงบประมาณ — `to_commit`)**:
The step after verification where the Budget Confirmer completes the budget code and dimensions and presses ยืนยันงบประมาณ, which reserves the budget and moves the request on to รอส่งขออนุมัติ. ตีกลับ returns it to รอตรวจสอบข้อมูล.
_Avoid_: รอตรวจสอบ / จองงบประมาณ, verify step

**Request Verifier (ผู้ตรวจสอบคำขอ)**:
The person who confirms a submitted request's data at รอตรวจสอบข้อมูล. May enter budget code and dimensions but **cannot reserve budget**. A separate duty from the Budget Confirmer: holding one does not grant the other.
_Avoid_: budget officer, เจ้าหน้าที่งบ

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
The up-front choice of how a request gets its budget (`budget_selection_mode`). Base ships **`normal`** (ใช้เงินจากแผน — reserve a new commitment against a budget code and dimensions entered directly on the form, scoped by the category's non-procurement baseline and any pinned code, [ADR-0004](docs/adr/0004-budget-code-selection-scoped-by-category-non-procurement.md)). A bridge (`kmitl_project_agx_approval`) adds **`project`** (โครงการ/กิจกรรม — draw down a commitment a `kmitl.project` already reserved for itself; the category pin does not apply). A UI affordance only — the server always keys draw-down off `reservation_commitment_id`, never off this field.
_Avoid_: the removed generic "draw any existing reservation" mode — each mode now scopes its own draw-eligible slips

**Project-Funded Request (คำขอใช้งบโครงการ)**:
An approval request in `project` mode. Its money was already authorized when the `kmitl.project` itself was approved (kmitl_project [ADR-0005](../kmitl_project/docs/adr/0005-approval-gated-lifecycle-esaraban.md)), so spending it is bookkeeping, not a fresh authorization — the request **skips e-Saraban entirely**, jumping `to_commit → approved` on draw ([ADR-0005](docs/adr/0005-project-mode-auto-approve-skips-esaraban.md)). No expense-side manager approval, no หนังสือ, no expense-side PDF (the project's own letter is the authority). Drawable only from a project in `in_progress` — a project reserves its slip *before* its own approval, so the slip alone is not the authorization the skip relies on.
_Avoid_: assuming every request routes through e-Saraban when the Sarabun bridge is installed — project mode is the one path that deliberately does not; and assuming any reserved project slip is drawable — the project must be approved first

**Requesting Unit (หน่วยงานผู้ขอ)**:
The unit the requester files the expense under (`requesting_department_id`), declared at entry — required while the plan is editable, defaulting to the current user's most recently used unit. Distinct from the budget dimension ส่วนงาน (`department_analytic_id`, the charged unit chosen by the Request Verifier / Budget Confirmer, and overwritten by the mode switch/project draw-down): the two may differ, e.g. a project-funded request charged to the project's own ส่วนงาน while the requester still belongs to their own unit. No check compares them. See [ADR-0007](docs/adr/0007-requesting-unit-separate-from-budget-department.md).
_Avoid_: ส่วนงาน/department (ambiguous with the budget dimension), OU
