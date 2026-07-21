# Approval Request (Expense Plan)

The expense-approval application (`agx_approval`): a requester fills a form to get an expense **approved before** the money is spent. The form-filling stage is framed as proposing an **expense plan** — what is planned to be spent and who is involved — not a settled bill. Who actually receives the money is *not* decided on the plan; it is recorded later, **after the mission**, when actual expenses are broken down per recipient on the same request, and only then billed into a disbursement.

Approval itself is **routed through e-Saraban**: a submitted request spawns a หนังสือ that circulates for sign-off, and the หนังสือ's outcome drives the request's state (completed → approved, returned → returned, rejected → rejected). The internal approve button is not the approval path when the Sarabun bridge is installed.

## Language

**Approval Request (ใบขออนุมัติ)**:
The `approval.request` document. Spans two moments of one activity: the **plan** (approved before the money is spent) and the **actual expense record** (filled after the mission, before billing). Reserves budget on approval.
_Avoid_: expense request, claim, bill

**Expense Plan (แผนค่าใช้จ่าย)**:
The planned spending captured while filling the form — the purpose of the entry stage. What is approved and what budget is reserved against.
_Avoid_: budget, estimate, quotation

**Expense (ค่าใช้จ่าย)**:
A single **planned** line (`approval.request.line`): รายการ (product) + รายละเอียด (detail) + จำนวนเงิน (planned amount). Broken down **by expense type, not by person**, and carries **no payee** — a plan line says what is spent, not who is paid.
_Avoid_: request line, payee line, actual expense

**Participant (รายชื่อ)**:
A person involved in the activity — traveller, attendee, or related person — listed on the plan (person + note, no bank, no amount). The roster from which recipients are later chosen: to pay someone they must first appear here.
_Avoid_: payee, recipient (ผู้รับเงิน)

**Actual Expense Allocation (ค่าใช้จ่ายจริง / จัดสรรรายคน)**:
The after-mission breakdown recorded on the request: rows of (**recipient**, expense product, **actual** amount, bank). One row = one disbursement line; grouped by recipient it *is* the งบหน้าใบสำคัญคู่จ่าย view. Recipients are drawn from the participants.
_Avoid_: expense plan (that is the pre-spend estimate), payee sync

**Recipient (ผู้รับเงิน)**:
A participant who actually receives money — known only after the mission, named on an Actual Expense Allocation row with their bank. A single request may pay **several** recipients.
_Avoid_: participant, payee-per-plan-line

**Pull back (ดึงกลับ — pre-routing)**:
The clerk returning a *not-yet-sent* request to `draft` (via a confirm wizard, releasing the budget reservation), available only before the หนังสือ is sent to e-Saraban. **Distinct** from e-Saraban's own ดึงกลับ/ตีกลับ, which act on a *circulating* หนังสือ and land the request in `returned`.
_Avoid_: recall (that is e-Saraban's, on a circulating document), reset

**Disbursement Voucher Cover Sheet (งบหน้าใบสำคัญคู่จ่าย)**:
The formal **PDF report** over the Actual Expense Allocation — adds withholding-tax columns, the ผู้ทดรองจ่าย designation and the dean's signature. Deferred to a later phase; the underlying *data* already lives in the allocation.
_Avoid_: disbursement request (that is the payment document itself)
