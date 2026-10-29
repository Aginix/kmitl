# Advance Payment (สัญญายืมเงิน)

Employee cash-advance loans: the institute disburses money to a borrower ahead of spending, then tracks the debt until it is cleared and the agreement closed.

## Language

**Advance Payment Agreement (สัญญายืมเงิน)**:
One loan contract for one borrower, funded by a **single** disbursement for the exact amount requested (no partial/multiple draws on one agreement). Tracked from request → disbursement → clearing → closure.
_Avoid_: loan, borrowing, cash advance request, contract (bare)

**Borrower (ผู้ยืม)**:
The person who takes the loan and personally owes the debt — must be an organization staff member, stored in `employee_id` (`hr.employee`), not a bare `res.users`. The borrower's payable partner (`partner_id`, used for bank matching and payment) is a stored `related` on `employee_id.work_contact_id`. Submits the request personally, or a loan officer submits it on the borrower's behalf (any loan type); when someone other than the borrower submits, the borrower's signature block on the printed contract is left blank to sign by hand (ADR-0031). Need not be the record's *drafter* (see below): a `user`-tier staffer may draft the request on the borrower's behalf, ready for the borrower to submit (ADR-0010), unless Strict mode is on (ADR-0014). An employee with no linked user account can be picked as borrower but cannot submit for themselves — only an admin can submit on their behalf.
_Avoid_: requester, requestor, applicant, requested_by (old field name, retyped by ADR-0014)

**Drafter (ผู้จัดทำ)**:
Who actually filled the form in — `user_id` (`res.users`), the source of truth for this, distinct from `create_uid` (immutable) so a manager can correct a mis-attributed request. Grants visibility to the record via the own-only ir.rule (OR'd with the borrower's own visibility) even after the drafter loses the `user`-tier draft-on-behalf group. Editable only by a manager/admin (`can_edit_drafter`), everyone else sees it read-only (ADR-0014).
_Avoid_: creator, create_uid, ผู้ยืม (that is the borrower, `employee_id`)

**Role tiers (own-only / user / manager / loan officer / loan approver)**:
The implied permission chain `own_only → user → manager`, plus two standalone groups, `loan_officer` (ADR-0010) and `loan_approver` (ADR-0017):
- **Own-only (`group_advance_payment_own_only`)**: sees and creates only their own agreements; the default borrower tier.
- **User / การเงินหน่วยงาน (`group_advance_payment_user`)**: the unit finance staff. Sees every agreement and may draft one on behalf of another borrower (data entry only) — cannot submit someone else's draft or perform any workflow action. Strict mode (ADR-0014) switches this power off org-wide except for `base.group_system`.
- **เจ้าหน้าที่งานเงินยืม / Loan Officer (`group_advance_payment_loan_officer`)**: the standalone oversight tier that performs the workflow actions — submitting on a borrower's behalf, verify, reset-to-draft, accept-report, bank correction (including materialising an Unlisted bank account, ADR-0022), due-date, and return-line approve/reject. Implies `user` (sees all). Each record is assigned to a single named officer via the required `loan_verifier_id`; verifying (`action_verify`) is restricted to that specific officer (or an admin), not any member of the group (ADR-0013). `base.group_system` admins are standing members of this group so they can always be picked.
- **ผู้มีสิทธิ์อนุมัติเงินยืม / Loan Approver (`group_advance_payment_loan_approver`)**: standalone, same shape as Loan Officer — implies `user`, root/admin are standing members. Each record is assigned a single expected approver via the required `approver_id`; approving (`action_approve`) is restricted to that specific approver (or an admin), not any member of the group (ADR-0017). Independent of Manager: being a manager does not make someone an eligible approver, and vice versa.
- **Manager (`group_advance_payment_manager`)**: cancels agreements; implies `user` but not `loan_officer`/`loan_approver` — a manager does not get their workflow buttons. Managers (and admins) alone may edit the Drafter, Loan Officer and Loan Approver fields (`can_edit_drafter`, `is_manager`; ADR-0014).
The escape hatch for exceptional data fixes stays `base.group_system`, never `manager`.
_Avoid_: officer (renamed to `loan_officer`; the plain `user` group is now the sees-all data-entry tier, not the borrower's own-only tier)

**ทยอยยืม (serial borrowing)**:
Covering a multi-activity need with a *sequence* of single-draw agreements (borrow → clear → borrow again), **not** multiple draws on one agreement. Enforced by the one-active-agreement-per-borrower rule.
_Avoid_: partial borrowing, installment, drawdown

**ADV Running Number (เลขที่คำขอ)**:
The record's running identifier (`ADV/<BE year>/####`), assigned when the request is first submitted (draft → to_endorse). Identifies the data row throughout its life.
_Avoid_: contract number, agreement number

**Contract Number (เลขที่สัญญายืมเงิน)**:
The formal loan-contract number, assigned only when the disbursement transfer completes on the Effective Date — distinct from the ADV Running Number. Uses a simple running sequence for now; a dedicated override module may customize the format later.
_Avoid_: ADV number, running number

**Loan Contract Form (แบบ สค.001 / ใบสัญญาการยืมเงิน)**:
The printed paper contract (`advance_payment_contract_pdf`, header button พิมพ์สัญญา, printable in any state). Each signature block — borrower, supervisor (เสนอ; the Finance Director on the Office route), approver (คำอนุมัติ) — carries the signer's digitized `hr.employee` signature once the record is past that signer's step; before that (or after ดึงกลับ / ส่งกลับแก้ไข / cancel) it is left blank to sign by hand. The approver's position always reads รองอธิการบดีฝ่ายการเงินและนิติการ ปฏิบัติการแทนอธิการบดี. The borrower's ใบรับเงิน block is never pre-filled — signed and dated by hand; โอนเงินวันที่ is the Effective Date. Page 1 is filled from the agreement; page 2 is the blank รายการส่งใช้เงินยืม ledger for handwriting. Its เลขที่ is the Contract Number, not the ADV Running Number.
_Avoid_: loan report, contract PDF (bare)

**Effective Date (วันที่เป็นลูกหนี้)**:
The date the disbursement transfer to the borrower completes. At this moment the agreement enters `in_progress` (from `approved`), becomes a formal debt ("ลูกหนี้โดยสมบูรณ์"), and receives its Contract Number.
_Avoid_: approval date, disbursement request date

**Endorse (เห็นชอบ)**:
The borrower's own first-line supervisor's sign-off at `to_endorse`, the step right after submit and before Verify. Distinct from Approve — Endorse is the supervisor confirming the request is legitimate before it reaches the finance officer; Approve is the Deputy Rector's final release to disbursement. The endorser is held in `endorser_id` (`res.users`), suggested from the borrower's line manager `employee_id.parent_id` but **overridable** — a request sometimes has to go to somebody above the direct manager. It re-suggests when the borrower changes and otherwise stands, so neither an HR reorg nor a ส่งกลับแก้ไข overwrites a deliberate choice; a manager can still reassign a pending request, which moves the To-Do with it. The one person it may never be is the borrower. Only `endorser_id` (or an admin) may `action_endorse`/`action_endorse_reject`, and submitting without a manager (or a manager with no linked user) is a blocking exception. The endorser reaches their queue through the **รอฉันเห็นชอบ** menu (own-only users see neither สัญญาของฉัน's own-records filter nor สัญญาเงินยืมทั้งหมด); they cannot see a subordinate's *draft*. Being named `endorser_id` is by itself enough to open and endorse the request (`advance_payment_endorser_rule`) — the endorser needs no advance-payment group at all, though without one the app menu stays hidden and they reach it through the To-Do. This is the *supervisor* tier only of the org-routed Endorse → Approve chain ADR-0006 deferred; the Dean/ผอ.กองคลัง tier above `to_approve` is still deferred (ADR-0020).
_Avoid_: approve, verify, validate

**Verify (ตรวจสอบ)**:
The finance officer's check of the submitted request against the real paper documents, at `to_verify` — reached after the supervisor's Endorse, not directly from submit. Distinct from Approve. On failure the officer returns the request to the borrower to edit (back to `draft`). Only the officer named in the record's `loan_verifier_id` (or an admin) may verify (ADR-0013); endorsing raises a To Do activity for that officer, which verifying marks **done** and which cancel / ส่งกลับแก้ไข / ดึงกลับ **drop** unfinished, so the officer's inbox only ever holds requests they can actually act on (ADR-0015). `loan_verifier_id` defaults from the standing assignee configured in Settings, else from the sole officer when there is only one (ADR-0015). Verify is refused while `bank_id` is empty, so an Unlisted bank account must be materialised first (ADR-0022).
_Avoid_: approve, review, validate

**Approval route (เส้นทางการอนุมัติ)**:
The ordered sign-off steps a request passes through between submit and disbursement. Two routes exist:
- **Standard route (flow พื้นฐาน — คณะ/วิทยาลัย)**: Endorse → Verify → Director Review → Approve.
- **Office route (flow สำนักงาน — สำนักงานภายใต้สำนักงานอธิการบดี)**: Verify → Director Review → Approve — **no supervisor Endorse**. On the printed contract the director's signature fills the supervisor's เสนอ block in its place.
A request's route is fixed when it is submitted and does not change mid-flight if the configuration later changes. The Standard route is the base behaviour; the Office route is an opt-in extension that owns its own configuration (ADR-0027).
_Avoid_: flow 1 / flow 2 (in docs), workflow, tier chain

**Director Review (ผอ.พิจารณา)**:
The Finance Director's (ผู้อำนวยการสำนักงานคลัง) consideration of a verified request, a step of its own **after Verify and before Approve** — the loan waits here as **รอผู้อำนวยการพิจารณา**. Distinct from Approve: the director considers and forwards; the authorised approver (ผู้มีอำนาจ) still gives the final release. Its date (วันที่ผอ.พิจารณา) is recorded separately from the approval date. The director is **one institution-wide person** (not per faculty/unit), named on each record in the same way as the approver — defaulted from the standing director configured in Settings, and only that named person (or an admin) may act.
_Avoid_: approve, verify, endorse

**Approve (อนุมัติ)**:
The sign-off at `to_approve` — now the **second** tier, the Deputy Rector's — that releases the request to disbursement — a **single step**, a manual click by `action_approve`, which creates the disbursement `account.payment` and moves the loan to `approved`. The org-routed chain above this step (Faculty: Dean → Deputy Rector; สนอ.: ผอ.กองคลัง → Deputy Rector) is **still deferred** — only the supervisor's Endorse below `to_verify` was reintroduced (ADR-0020). There is no `rejected` state on the loan itself — a request that does not pass goes back to `draft`/`to_endorse`/`to_verify` (ส่งกลับแก้ไข) or to `cancel`. (An e-Saraban approval bridge, `advance_payment_sarabun`, was prototyped and removed for now — see ADR-0011.)
Each record names its expected approver in `approver_id`, labelled **ผู้มีอำนาจอนุมัติเงินยืม** on the form (defaulted from the standing approver configured in Settings, else the admin), and finishing verification raises a To Do for that person; approving marks it done, cancel/ดึงกลับ drop it (ADR-0016). `action_approve` is restricted to that specific approver (or an admin) — not any `group_advance_payment_loan_approver` member — mirroring how ADR-0013 narrowed verify to the named officer (ADR-0017; supersedes ADR-0016's original "routing target, not an authority check").
_Avoid_: verify, confirm, endorse

**Debt (หนี้เงินยืม / ลูกหนี้)**:
What the borrower owes the institute. Created when the disbursement transfers on the Effective Date (equal to the loan amount) and reduced by clearing; when it reaches zero the agreement can close. From the moment the transfer succeeds the borrower is a debtor (ลูกหนี้) and the agreement reads **ค้างชำระ** (outstanding) — it no longer reads "in the contract period".
_Avoid_: balance, loan (the loan is the agreement, the debt is the owed amount)

**Clearing (ล้างหนี้)**:
Reducing the debt while the agreement is **ค้างชำระ**, by (a) spending evidenced through Disbursement Requests (ใบเบิก) and (b) leftover cash returned against a receipt (ใบเสร็จรับเงิน). Neither link exists yet (ADR-0028): for now the debt is cleared outside the app and the loan officer closes the agreement by hand. There is no borrower expense report and no in-app return step any more.
_Avoid_: settlement, reconciliation, reimbursement, ส่งเบิก / expense report (removed)

**Reset to draft (ตั้งกลับเป็นแบบร่าง)**:
Any transition that puts a request back in `draft`, keeping the ADV number. Four distinct paths, deliberately sharing one UI verb because they are the same thing from the borrower's point of view — the request is editable again:
- the **borrower's own** pull-back (`action_recall`, from `to_endorse`/`to_verify`/`to_approve`) — withdrawing a not-yet-approved request to edit or drop it;
- the **supervisor's ส่งกลับแก้ไข** (`action_endorse_reject`, from `to_endorse`) — sending it back before it even reaches the finance officer (ADR-0020);
- the **loan officer's ส่งกลับแก้ไข** (`action_reset_to_draft` / `_action_do_reject`, from `to_verify`) — sending it back for the borrower to fix;
- the **manager's un-cancel** (`action_reset_cancel_to_draft`, from `cancel`) — ad-hoc recovery of a request cancelled before the money moved.
_Avoid_: recall / ดึงกลับ (reserved for e-Saraban's own ดึงกลับ — see ADR-0011), withdraw, reopen (that is `action_reopen`: `done` → `in_progress`)

**Source Reference (AR / PR)**:
The upstream document a loan is created from — an Approval Request (ใบขออนุมัติ / expense plan, `approval.request`) or a Purchase Request (คำขอให้จัดหา, `purchase.request`). Policy: a loan a borrower files **must** have one — the borrower states up front which matter they borrow for and how much. The source's requester need not be the borrower, and **several borrowers may draw on one source**: since a person holds only one agreement at a time, a project's money is split across its team. The borrower identifies the source by **typing its document number exactly** (เลขที่เอกสาร) — they are never offered a list to browse, because the source is usually filed by someone whose documents the borrower may not read; the match shows only enough (subject, unit, remaining headroom) to confirm it is the right one. A drafter who can see the source may still pick it for the borrower. Borrowing happens **only in the loan app**: the source's own workflow never waits on, creates or copies a loan — it may at most show which loans cite it. Nor is the source held hostage: it and its Budget Commitment may be cancelled while loans against it are live — the loan stands, because the money is out and the debt is the borrower's either way (ADR-0029). Held in the `reference` Reference field, with `reference_model` derived from it; each bridge additionally mirrors it into a typed Many2one (`purchase_request_id`, `approval_request_id`) for searching, grouping and FK integrity. advance_payment never depends on these models directly (true since ADR-0023 moved the `purchase.request` selection value into `purchase_request_advance_payment`); the selection values, typed pickers, mirrors and auto-fill live only in bridge modules. A Disbursement Request (ใบเบิก/DR) is *not* a source and is unrelated to loans. See ADR-0007.
_Avoid_: origin, parent, DR

**Related document (เอกสารอ้างอิงเพิ่มเติม)**:
Any number of further documents cited on a loan beside its Source Reference — e.g. a หนังสือสารบรรณ backing a loan for a purchase request. Each one is either an in-system document of a supported kind (found by typing its number exactly, like the source — plus its date where numbers restart each fiscal year, as Sarabun's do) or an out-of-system document given by number/subject, optionally with a file. Purely supporting evidence: it never drives the headroom, the dimensions or the route. The borrower, unit finance (User tier) and the loan officer may add one at any point until the agreement is closed or cancelled; the borrower may remove only one they added themselves, and only while the request is a draft — unit finance and the loan officer may remove any. Every addition and removal is logged on the agreement (ADR-0029). An opt-in extension; each in-system kind comes from its own small bridge.
_Avoid_: reference (bare — that is the Source Reference), attachment, อ้างถึง (Sarabun's own term for its letters)

**Budget Commitment (ใบจองงบประมาณ)**:
The `budget.commitment` the borrowed cash is drawn against, copied onto the loan from its Source Reference when the reference is picked and held as a snapshot (`budget_commitment_id`). The loan **never reserves its own** — the source document already reserved this money, and reserving again would draw the appropriation down twice. Empty on a standalone loan, whose budget source is an open policy question. Recording it is *not* ตัดงบ: consuming the budget for borrowed money is still parked, and nothing on the loan path obligates or consumes today. The loan holds no commitment of its own (ADR-0025): it reaches its Source Reference's commitment, read-only, for the Borrowing headroom and the disbursement's financial dimensions. See ADR-0008, ADR-0009 and `agx_approval` ADR-0003.
_Avoid_: budget, reservation, earmark (for the document itself), ตัดงบ (that is the consume step)

**Borrowing rule (เงื่อนไขการยืม)**:
A policy condition a loan must meet before it may go forward — e.g. one active agreement per borrower, a source must be approved, the loan must fit the Borrowing headroom, a purchase request backs a single loan. Kept as administrator-maintained exception rules so policy can be switched on, changed or dropped without a release; checked at submit and again at Verify (ADR-0030). Distinct from an **integrity guard** (the loan type matching its source's document kind, a bank account before Verify), which protects data shape and is never switchable.
_Avoid_: constraint, validation (for policy)

**Borrowing headroom (วงเงินยืมคงเหลือ)**:
How much more may still be borrowed against a Source Reference: the full reserved amount of its Budget Commitment minus every loan drawn on it that is not cancelled (closed loans still count — that money went out). It does **not** net off what the commitment has spent through other channels (purchase orders, direct payments); which part of the reservation each borrower takes is the loan officer's call at Verify (ADR-0029). A loan may not exceed it. A source may back a loan only while its commitment is live (reserved or partly used) — no commitment yet, cancelled or used up means no borrowing, re-checked at submit and at Verify. An opt-in extension, not the base behaviour.
_Avoid_: borrowing cap (that is the full reserved amount), available budget, คงเหลือผูกพันได้ (that is the commitment's own balance)

**มิติทางบัญชี (financial dimensions)**:
The four dimensions a loan is charged to — ส่วนงาน, แหล่งเงิน, กองทุน, ด้าน/แผนงาน/กิจกรรม — The loan itself carries none (ADR-0025). The disbursement voucher (ใบสำคัญจ่ายเงินยืม) takes them from the header of the Source Reference's Budget Commitment when it is created — the commitment as a whole, not per commitment line; accounting may still correct them on the voucher.
_Avoid_: analytic accounts (that is the underlying model), cost centre

**Required reference model (`loan_type_id.reference_model`)**:
The *declaration*, on the loan-type master data, that loans of that type must be backed by a source document of a given model. Distinct from `advance.payment.reference_model`, which is the *actual* model of the attached document. A mismatch between the two is a hard `ValidationError`; a missing document is a blocking exception at submit. The type alone decides: a type with no model means the loan has no reference, and there is no manual-reference setting (ADR-0023, removing `allow_manual_reference`).
_Avoid_: reference type, document type

**Restricted loan type (ประเภทเงินยืมเฉพาะกลุ่ม)**:
A loan type only members of named groups may choose when drafting — by default the loan type with no Source Reference (ค่าใช้จ่ายอื่นใด), kept for the loan officer's back-office use since borrowers must otherwise borrow against a source. It limits who may *start* such a loan, not who may see one: the borrower and every approver still open it as usual. A type naming no group is open to all. An opt-in extension (ADR-0031).
_Avoid_: hidden loan type, private loan type

**Reference filter (ตัวกรองเอกสารอ้างอิง, `loan_type_id.reference_domain`)**:
A domain over the loan type's required model that narrows which source documents the borrower is offered. It may use `employee_id`, `partner_id`, `user_id` (all the borrower's), `uid` and `company_id`. It is evaluated server-side and ANDed with each bridge's mandatory baseline (AR and PR: approved). The result drives the typed picker (`reference_picker_domain`) and is re-checked while the loan is in draft (ADR-0023).
_Avoid_: reference domain (bare), picker domain (that is the computed result)

**Cleared amount (ส่งใช้คืน)**:
The part of the debt already cleared. Read-only on the agreement; it will be fed by the Disbursement Requests (ใบเบิก) linked to the loan (ADR-0028).
_Avoid_: actual expense report, ยอดค่าใช้จ่ายจริง

**Outstanding amount (คงเหลือ)**:
What the borrower still owes right now: loan amount minus ส่งใช้คืน. Zero means the debt is settled.
_Avoid_: leftover, return amount, ยอดคงเหลือ

**Unlisted bank account (บัญชีธนาคารนอกรายการ)**:
A payee account the borrower declares on the loan because it is not yet among their work contact's `res.partner.bank`: tick `use_unlisted_bank`, then give the bank, account number and a Book Bank image. Ticking clears `bank_id`. At `to_verify` the loan officer checks it against the Book Bank and materialises it with **สร้างบัญชีธนาคาร** (`advance_payment_partner_bank`), which reuses or creates the account, sets `bank_id` and clears the tick. Verify is refused until `bank_id` is set (ADR-0022).
_Avoid_: new bank account, manual bank account

**Return due date (วันที่ครบกำหนด)**:
The date by which the borrower must clear the loan, set **manually by the loan officer after approval** — not derived from the activity end date or the effective date. Drives the weekly overdue reminders.
_Avoid_: deadline, activity end date

**Return due status (สถานะวันครบกำหนด)**:
Where an outstanding loan stands against its Return due date, read literally by the calendar day: **ยังไม่ถึงกำหนด** (before the date), **ครบกำหนด** (today *is* the date), **เกินกำหนด** (past it). Shown only while the borrower is a debtor — from the Effective Date until the agreement closes; blank otherwise. Distinct from the reminder window ("notify N days before"), which is a separate notion.
_Avoid_: overdue flag (that is only one of the three values), due range / ช่วงวันครบกำหนดคืน (the 0-7/8-15/… buckets)
