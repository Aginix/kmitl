# Advance Payment (สัญญายืมเงิน)

Employee cash-advance loans: the institute disburses money to a borrower ahead of spending, then tracks the debt until it is cleared and the agreement closed.

## Language

**Advance Payment Agreement (สัญญายืมเงิน)**:
One loan contract for one borrower, funded by a **single** disbursement for the exact amount requested (no partial/multiple draws on one agreement). Tracked from request → disbursement → clearing → closure.
_Avoid_: loan, borrowing, cash advance request, contract (bare)

**Borrower (ผู้ยืม)**:
The person who takes the loan and personally owes the debt; stored in `requested_by`. Must always **submit** the request personally — no submitting on behalf of someone else — but need not be the record's *creator*: a `user`-tier staffer may draft the request on the borrower's behalf, ready for the borrower to submit (ADR-0010).
_Avoid_: requester, requestor, applicant

**Role tiers (own-only / user / manager / loan officer)**:
The implied permission chain `own_only → user → manager`, plus the standalone `loan_officer` group (ADR-0010):
- **Own-only (`group_advance_payment_own_only`)**: sees and creates only their own agreements; the default borrower tier.
- **User (`group_advance_payment_user`)**: sees every agreement and may draft one on behalf of another borrower (data entry only) — cannot submit someone else's draft or perform any workflow action.
- **เจ้าหน้าที่งานเงินยืม / Loan Officer (`group_advance_payment_loan_officer`)**: the standalone oversight tier that performs the workflow actions — verify, reset-to-draft, accept-report, bank correction, due-date, and return-line approve/reject. Implies `user` (sees all). Normally a single named officer, referenced per-record by `loan_verifier_id`.
- **Manager (`group_advance_payment_manager`)**: approves (the manual fallback) and cancels; implies `user` but not `loan_officer` — a manager does not get the loan officer's workflow buttons.
The escape hatch for exceptional data fixes stays `base.group_system`, never `manager`.
_Avoid_: officer (renamed to `loan_officer`; the plain `user` group is now the sees-all data-entry tier, not the borrower's own-only tier)

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
The management sign-off at `to_approve` that releases the request to disbursement — a **single step**, a manual click by `group_advance_payment_manager` (`action_approve`), which creates the disbursement `account.payment` and moves the loan to `waiting_transfer`. The multi-tier Endorse → Approve chain routed by org unit (Faculty: Dean endorses → Deputy Rector approves; สนอ.: ผอ.กองคลัง endorses → Deputy Rector approves) is **not implemented**. There is no `rejected` state on the loan itself — a request that does not pass goes back to `draft`/`to_verify` (ส่งกลับแก้ไข) or to `cancel`. (An e-Saraban approval bridge, `advance_payment_sarabun`, was prototyped and removed for now — see ADR-0011.)
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
The upstream document a loan is created from — an Approval Request (ใบขออนุมัติ / expense plan, `approval.request`) or a Purchase Request (คำขอให้จัดหา, `purchase.request`). A Purchase Request backs **one** loan; an Approval Request may back **several**, one per participant who chose to borrow, each capped by the request's remaining headroom (`agx_approval` ADR-0003). Held in the `reference` Reference field, with `reference_model` derived from it; each bridge additionally mirrors it into a typed Many2one (`purchase_request_id`, `approval_request_id`) for searching, grouping and FK integrity. advance_payment never depends on these models directly; the mirrors and the auto-fill live only in bridge modules. A Disbursement Request (ใบเบิก/DR) is *not* a source and is unrelated to loans. See ADR-0007.
_Avoid_: origin, parent, DR

**Budget Commitment (ใบจองงบประมาณ)**:
The `budget.commitment` the borrowed cash is drawn against, copied onto the loan from its Source Reference when the reference is picked and held as a snapshot (`budget_commitment_id`). The loan **never reserves its own** — the source document already reserved this money, and reserving again would draw the appropriation down twice. Empty on a standalone loan, whose budget source is an open policy question. Recording it is *not* ตัดงบ: consuming the budget for borrowed money is still parked, and nothing on the loan path obligates or consumes today. Lives in the `advance_payment_budget` bridge, not in this module. See ADR-0008, ADR-0009 and `agx_approval` ADR-0003.
_Avoid_: budget, reservation, earmark (for the document itself), ตัดงบ (that is the consume step)

**มิติทางบัญชี (financial dimensions)**:
The four dimensions a loan is charged to — ส่วนงาน, แหล่งเงิน, กองทุน, ด้าน/แผนงาน/กิจกรรม — held in `analytic_distribution` with `*_analytic_id` pickers computed from it, per the repo-wide idiom. They live in the `advance_payment_budget` bridge together with the ใบจองงบประมาณ, so the loan lifecycle in this module needs no budget stack (ADR-0009). Completeness is enforced by a blocking exception at submit, and the pickers lock once a Source Reference supplies them.
_Avoid_: analytic accounts (that is the underlying model), cost centre

**Required reference model (`loan_type_id.reference_model`)**:
The *declaration*, on the loan-type master data, that loans of that type must be backed by a source document of a given model. Distinct from `advance.payment.reference_model`, which is the *actual* model of the attached document. A mismatch between the two is a hard `ValidationError`; a missing document is a blocking exception at submit.
_Avoid_: reference type, document type

**Expense Report / บันทึกค่าใช้จ่ายจริง**:
The borrower's end-of-activity summary recorded directly on the agreement — description, actual expense amount, auto-computed return amount, and evidence (**no itemized lines**). Submitted to leave `in_progress`; the loan-responsible finance officer must accept it before the debt can close. It covers every baht drawn on the loan, which may include money the borrower paid to *other* people — the debt is the borrower's alone even when the spending was the group's.
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
