# Approval Request (Expense Plan)

The expense-approval application (`agx_approval`): a requester fills a form to get an expense **approved before** the money is spent. The form-filling stage is framed as proposing an **expense plan** — what is planned to be spent and who is involved — not a settled bill. Who actually receives the money is *not* decided on the plan; it is recorded later, **after the mission**, when actual expenses are broken down per recipient on the same request, and only then billed into a disbursement.

Approval itself is **routed through e-Saraban**: a submitted request spawns a หนังสือ that circulates for sign-off, and the หนังสือ's outcome drives the request's state (completed → approved, returned → returned, rejected → rejected). The internal approve button is not the approval path when the Sarabun bridge is installed.

## Language

**Approval Request (ใบขออนุมัติ)**:
The `approval.request` document. Spans two moments of one activity: the **plan** (approved before the money is spent) and the **actual expense record** (filled after the mission, before billing). Reserves budget on approval.
_Avoid_: expense request, claim, bill

**Approval Category (ประเภทคำขออนุมัติ)**:
The kind of request (`approval.category`) — travel, honorarium, etc. Not a mere label: it **scopes** what a request of that kind may use — its allowed expenses, allowed people, and its **budget code**. When it pins a budget code that code becomes the request's constraint (not just a default); when it leaves the code blank the request selects freely from the non-procurement expense codes.
_Avoid_: request type, template, budget preset

**Expense Plan (แผนค่าใช้จ่าย)**:
The planned spending captured while filling the form — the purpose of the entry stage. What is approved and what budget is reserved against.
_Avoid_: budget, estimate, quotation

**Expense (ค่าใช้จ่าย)**:
A single **planned** line (`approval.request.line`): รายการ (product) + รายละเอียด (detail) + จำนวนเงิน (planned amount). Broken down **by expense type, not by person**, and carries **no payee** — a plan line says what is spent, not who is paid.
_Avoid_: request line, payee line, actual expense

**Participant (รายชื่อ)**:
A person involved in the activity — traveller, attendee, or related person — listed on the plan (person + note, no bank, no amount). The roster from which recipients are later chosen: to pay someone they must first appear here.
_Avoid_: payee, recipient (ผู้รับเงิน)

**Borrowing Participant (ผู้ยืมในคำขอ)**:
A Participant who drew a สัญญายืม against this request rather than fronting the cost. Borrowing is **per person and discretionary** — each participant decides for themselves once the request is approved and *before* the money is spent — and the amount is the borrower's own declaration, since the plan apportions nothing per person. A request may have none, one borrowing on the group's behalf, several borrowing their own, or any mix with people who front the cost instead.
_Avoid_: recipient (that is the post-mission ผู้รับเงิน), payee, advance row, per-line borrowing

**Borrowing Headroom (วงเงินยืมคงเหลือของคำขอ)**:
The request's approved amount (reserved budget, else the plan total) minus every **non-cancelled** สัญญายืม already drawn against it — what the remaining participants may still borrow. A *closed* loan still consumes it: the cash left the institute under this request.
_Avoid_: remaining budget, credit limit, per-person cap

**Actual Expense Allocation (ค่าใช้จ่ายจริง / จัดสรรรายคน)**:
The after-mission breakdown recorded on the request: rows of (**recipient**, expense product, **actual** amount, **payment type**, bank). Grouped by recipient it *is* the งบหน้าใบสำคัญคู่จ่าย view; recipients are drawn from the participants. A `direct`/`prepaid` row bills into a disbursement line; an `advance` row is excluded from the disbursement and instead **names the Funding Loan** it was paid out of (see Payment type). The allocation is the *itemisation* of what happened; it never clears a loan by itself.
_Avoid_: expense plan (that is the pre-spend estimate), payee sync, loan clearing

**Recipient (ผู้รับเงิน)**:
A participant who actually receives money — known only after the mission, named on an Actual Expense Allocation row with their bank. A single request may pay **several** recipients.
_Avoid_: participant, payee-per-plan-line

**Payment type (ประเภทการจ่ายเงิน)**:
How an actual-allocation row's money is settled, recorded **per row** in the `actual` stage: `direct` (จ่ายตรง — the institute pays the named recipient directly), `prepaid` (สำรองจ่าย — a participant fronts the cost, then claims it back), or `advance` (เงินยืม — paid out of a Funding Loan). `direct`/`prepaid` bill into a disbursement (one DR per request, header `direct` in the interim until the DR module supports per-line type); `advance` is excluded from the disbursement. One recipient may mix types across their rows.
_Avoid_: the removed plan-level `payment_type` (ADR-0001 D6) — this is its post-mission, per-row successor ([ADR-0002](docs/adr/0002-payment-type-per-actual-row.md))

**Funding Loan (แหล่งเงินของแถวเงินยืม)**:
The สัญญายืม an `advance` allocation row was paid out of — **chosen per row** from the loans drawn against this request, and **not necessarily the recipient's own**: one participant may borrow on the group's behalf and pay the others from it. Answers "which loan did this money come from", which is a different question from "who received it".
_Avoid_: the recipient's loan, borrower's loan (it may be someone else's), auto-matched loan

**Pull back (ดึงกลับ — pre-routing)**:
The clerk returning a *not-yet-sent* request to `draft` (via a confirm wizard, releasing the budget reservation), available only before the หนังสือ is sent to e-Saraban. **Distinct** from e-Saraban's own ดึงกลับ/ตีกลับ, which act on a *circulating* หนังสือ and land the request in `returned`.
_Avoid_: recall (that is e-Saraban's, on a circulating document), reset

**Budget Selection Mode (วิธีเลือกงบประมาณ)**:
The up-front choice of how a request gets its budget (`budget_selection_mode`). Base ships **`normal`** (ใช้เงินจากแผน — reserve a new commitment from the budget chart, scoped by the category's non-procurement baseline and any pinned code, [ADR-0004](docs/adr/0004-budget-code-selection-scoped-by-category-non-procurement.md)). A bridge (`kmitl_project_agx_approval`) adds **`project`** (โครงการ/กิจกรรม — draw down a commitment a `kmitl.project` already reserved for itself; the category pin does not apply). A UI affordance only — the server always keys draw-down off `reservation_commitment_id`, never off this field.
_Avoid_: the removed generic "draw any existing reservation" mode — each mode now scopes its own draw-eligible slips

**Project-Funded Request (คำขอใช้งบโครงการ)**:
An approval request in `project` mode. Its money was already authorized when the `kmitl.project` itself was approved (kmitl_project [ADR-0005](../kmitl_project/docs/adr/0005-approval-gated-lifecycle-esaraban.md)), so spending it is bookkeeping, not a fresh authorization — the request **skips e-Saraban entirely**, jumping `to_verify → approved` on draw ([ADR-0005](docs/adr/0005-project-mode-auto-approve-skips-esaraban.md)). No expense-side manager approval, no หนังสือ, no expense-side PDF (the project's own letter is the authority). Drawable only from a project in `in_progress` — a project reserves its slip *before* its own approval, so the slip alone is not the authorization the skip relies on.
_Avoid_: assuming every request routes through e-Saraban when the Sarabun bridge is installed — project mode is the one path that deliberately does not; and assuming any reserved project slip is drawable — the project must be approved first

**Disbursement Voucher Cover Sheet (งบหน้าใบสำคัญคู่จ่าย)**:
The **PDF report** (`report_disbursement_voucher`) over the Actual Expense Allocation — grouped per recipient × expense type, with withholding-tax columns (from the recipient's partner-type WHT) and the dean's signature. Each recipient may have made their own loan or fronted their own money, so there is no single ผู้ทดรองจ่าย designation.
_Avoid_: disbursement request (that is the payment document itself)
