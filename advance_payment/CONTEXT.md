# Advance Payment (สัญญายืมเงิน)

Employee cash-advance loans: the institute disburses money to a borrower ahead of spending, then tracks the debt until it is cleared and the agreement closed.

## Language

**Advance Payment Agreement (สัญญายืมเงิน)**:
One loan contract for one borrower, funded by a **single** disbursement for the exact amount requested (no partial/multiple draws on one agreement). Tracked from request → disbursement → clearing → closure.
_Avoid_: loan, borrowing, cash advance request, contract (bare)

**Borrower (ผู้ยืม)**:
The person who takes the loan and personally owes the debt; always the creator of the agreement — no borrowing on behalf of someone else. Stored in `requested_by`.
_Avoid_: requester, requestor, applicant

**ทยอยยืม (serial borrowing)**:
Covering a multi-activity need with a *sequence* of single-draw agreements (borrow → clear → borrow again), **not** multiple draws on one agreement. Enforced by the one-active-agreement-per-borrower rule.
_Avoid_: partial borrowing, installment, drawdown

**ADV Running Number**:
The record's running identifier (`ADV/<BE year>/####`), assigned when the request is first submitted (draft → to_verify). Identifies the data row throughout its life.
_Avoid_: contract number, agreement number

**Contract Number (เลขที่สัญญา)**:
The formal loan-contract number, assigned only when the disbursement transfer completes on the Effective Date — distinct from the ADV Running Number. Uses a simple running sequence for now; a dedicated override module may customize the format later.
_Avoid_: ADV number, running number

**Effective Date (วันที่มีผลของสัญญา)**:
The date the disbursement transfer to the borrower completes. At this moment the agreement enters `in_progress`, becomes a formal debt ("ลูกหนี้โดยสมบูรณ์"), and receives its Contract Number.
_Avoid_: approval date, disbursement request date

**Verify (ตรวจสอบ)**:
The finance officer's check of the submitted request against the real paper documents, at `to_verify`. Distinct from Approve. On failure the officer returns the request to the borrower to edit (back to `draft`).
_Avoid_: approve, review, validate

**Approve (อนุมัติ)**:
The management sign-off at `to_approve` that releases the request to disbursement — today a **single step** by `group_advance_payment_manager`. The multi-tier Endorse → Approve chain routed by org unit (Faculty: Dean endorses → Deputy Rector approves; สนอ.: ผอ.กองคลัง endorses → Deputy Rector approves) is **not implemented**; there is no `rejected` state — a request that does not pass goes back to `draft` (ส่งกลับแก้ไข) or to `cancel`.
_Avoid_: verify, confirm, endorse

**Debt (หนี้เงินยืม / ลูกหนี้)**:
What the borrower owes the institute. Created when the disbursement transfers on the Effective Date (equal to the loan amount) and reduced by clearing; when it reaches zero the agreement can close.
_Avoid_: balance, loan (the loan is the agreement, the debt is the owed amount)

**Clearing (ล้างหนี้)**:
Reducing the debt during the report/return stage, by (a) verified actual expenses and (b) returned leftover cash. Internal to the agreement — it does **not** involve a Disbursement Request (ใบเบิก/DR).
_Avoid_: settlement, reconciliation, reimbursement

**Recall (ดึงกลับ)**:
The borrower withdrawing their own not-yet-approved request back to `draft` (to edit or drop it). Distinct from the officer's reset-to-draft and from a Verify-stage return.
_Avoid_: cancel, withdraw, reset

**Source Reference (AR / PR)**:
The upstream document a loan is created from — an Approval Request (คำขออนุมัติค่าใช้จ่าย, `approval.request`) or a Purchase Request (คำขอให้จัดหา, `purchase.request`). Held in the `reference` Reference field, with `reference_model` derived from it; each bridge additionally mirrors it into a typed Many2one (`purchase_request_id`, `approval_request_id`) for searching, grouping and FK integrity. advance_payment never depends on these models directly; the mirrors and the auto-fill live only in bridge modules. A Disbursement Request (ใบเบิก/DR) is *not* a source and is unrelated to loans. See ADR-0007.
_Avoid_: origin, parent, DR

**Required reference model (`loan_type_id.reference_model`)**:
The *declaration*, on the loan-type master data, that loans of that type must be backed by a source document of a given model. Distinct from `advance.payment.reference_model`, which is the *actual* model of the attached document. A mismatch between the two is a hard `ValidationError`; a missing document is a blocking exception at submit.
_Avoid_: reference type, document type

**Expense Report / บันทึกค่าใช้จ่ายจริง**:
The borrower's end-of-activity summary recorded directly on the agreement — description, actual expense amount, auto-computed return amount, and evidence (**no itemized lines**). Submitted to leave `in_progress`; the loan-responsible finance officer must accept it before the debt can close.
_Avoid_: usage record, usage line, itemized expenses

**Return installment (คืนหลายงวด)**:
A per-agreement flag that lets the borrower return the money in several transfers instead of one; set by the borrower at report time and adjustable by the officer. Off by default (single return).
_Avoid_: partial return (that is any one transfer)

**Leftover / Return amount (ยอดคงเหลือ / เงินเหลือจ่าย)**:
Loan amount minus the actual expense — the cash to transfer back (`return_amount`, auto-computed). Returned in a single transfer, or — when the Return installment flag is on — several that accumulate to it. Each recorded return must equal the real transfer.
_Avoid_: change, remaining balance

**Reconcile (ตรวจสอบยอดคืนในบัญชี)**:
Finance confirming that returned cash actually arrived in the bank and matches the declared return. An exact match triggers automatic close; a mismatch is left unconfirmed (pending).
_Avoid_: verify (that is the request-stage document check by the officer)

**Over-return (คืนเกิน)**:
When the borrower transfers back more than the Leftover. The excess is never refunded — the borrower must confirm donating it to the institute before the agreement can close.
_Avoid_: overpayment, refund

**Donation of excess (บริจาคเงินส่วนเกิน)**:
The borrower's mandatory, consented donation of an over-returned excess to the institute, recorded with an audit trail (who confirmed + timestamp). Closing is blocked until consent is given.
_Avoid_: refund, write-off

**Return due date (วันครบกำหนดคืน)**:
The date by which the borrower must clear the loan, set **manually by the loan officer after approval** — not derived from the activity end date or the effective date. Drives the weekly overdue reminders.
_Avoid_: deadline, activity end date
