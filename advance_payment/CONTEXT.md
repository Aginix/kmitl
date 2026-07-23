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

**Endorse (เห็นชอบ) / Approve (อนุมัติ)**:
The management approval chain at `to_approve`, run via tier validation and routed by org unit — Faculty: Dean endorses → Deputy Rector approves; สนอ.: Finance Director (ผอ.กองคลัง) endorses → Deputy Rector approves. Endorse is the intermediate sign-off; Approve is the final one that releases the request to disbursement. A rejection here sends the request to `rejected`.
_Avoid_: verify, confirm

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
The upstream document a loan is created from — an Approval Request (คำขออนุมัติค่าใช้จ่าย, `approval.request`) or a Purchase Request (คำขอให้จัดหา, `purchase.request`). advance_payment never depends on these directly; the link lives only in bridge modules. A Disbursement Request (ใบเบิก/DR) is *not* a source and is unrelated to loans.
_Avoid_: origin, parent, DR

**Expense Report (รายงานค่าใช้จ่าย)**:
The borrower's end-of-activity declaration of what was actually spent from the loan, with evidence, submitted to leave `in_progress`. It states the expense total and the resulting Leftover; the loan-responsible finance officer must accept it before the debt can close.
_Avoid_: usage record, บันทึกการใช้เงิน (the old free-form field)

**Leftover (ยอดคงเหลือ / เงินเหลือจ่าย)**:
Loan amount minus the accepted actual expenses — the cash the borrower must transfer back, in one or more partial transfers. Each recorded return amount must equal the real transfer.
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
