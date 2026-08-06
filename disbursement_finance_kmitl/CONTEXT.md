# CONTEXT — Disbursement ↔ KMITL Finance Bridge

Glossary for the **post-bill payment-execution workflow** on
`disbursement.request` (DR). This module owns the phase that runs **after** the
accounting office posts the vendor bills.

## The two approval rounds (do not conflate)

The word "ตรวจสอบ / verify" and "อนุมัติ / approve" appear in **two different
rounds**. They use different vocabulary and different security groups.

| Concept | Round 1 — request approval (module `disbursement`, before bill) | Round 2 — payment execution (this module, after bill) |
|---|---|---|
| Verify | **Request Verification** — state `verified`, "ตรวจสอบคำขอ", `group_disbursement_officer` | **Payment Audit** — state `payment_audited`, "ตรวจสอบการเบิกจ่าย", `group_disbursement_payment_auditor` |
| Approve | **Request Approval** — state `approved` (obligates + consumes budget), "อนุมัติคำขอ", `group_disbursement_manager` | **Payment Authorization** — state `payment_authorized`, "อนุมัติเบิกจ่าย" (rector delegate), `group_disbursement_payment_authorizer` |

Round 2 deliberately uses the verbs **audit** and **authorize** so it never
collides with round 1's verify/approve.

## The three payment axes (do not conflate with `DR.payment_type`)

Set by the **auditor** during Payment Audit, on the **payment line** (see
Terms). Three orthogonal concepts:

- **Payment Subject / เรื่องที่จ่าย** (`kmitl.payment.subject`, master data in
  `finance_kmitl`, one per DR, chosen by the auditor): *what* the payment is
  for (e.g. เงินเดือน, เงินยืม/สำรองจ่าย, จ่ายตรงคู่ค้า, ค่าน้ำค่าไฟ). Admins
  maintain the list. Not to be confused with `DR.payment_type`
  (direct/advance/prepaid, inherited from the approval) nor with
  `kmitl.payment.type` (see the two sides of an entry, below).
- **Paying Account / หัวจ่าย** (`account.payment.method.line`): out of which
  account the money leaves, by which means, under which voucher — one choice, and
  one of Odoo's own records. A method line names a journal (the ใบสำคัญ), a
  payment method (เงินโอน / เช็ค / เงินสด) and the GL account the money is booked
  against; this module adds the institute's own bank account, which the e-payment
  file needs as its sending account and the cheque register as the cheque book.
  **What makes a line a paying account is that it names its GL account** — the
  lines Odoo seeds on every bank journal by default do not, and are not offered.
  That is also how cash qualifies, with no bank account at all. A bank account may
  hold several: a current account can be transferred from and drawn cheques on,
  and all of its paying accounts book to the same GL, because money leaving one
  bank account leaves one ledger account however it is paid. See
  `finance_kmitl/docs/adr/0001-paying-account-is-a-payment-method-line.md`.
- **Auto-match / จับคู่ตามธนาคารผู้รับ** (flag on the subject): when on, each
  payee is served from the **allowed** account held at the bank of their own
  bank account (เงินยืม/สำรองจ่าย); a payee whose bank matches none falls to
  the subject's account, which then reads as the **fallback / หัวจ่ายสำรอง**.
  When off, every payee pays from that same account, which reads as the
  **main / หัวจ่ายหลัก** (salary → KTB, direct vendor → SCB) — one field, two
  roles, the label follows the flag. Left empty it inherits the
  institute-wide default on the company. Set per **payment line** at audit
  time.
- **Match Result / ผลลัพธ์การจับคู่** (`paying_account_match` on the payment
  line): the **provenance** of that line's paying account — ตรงธนาคารผู้รับ
  (`bank`), ไม่ตรงกับหัวจ่ายหลัก (`fallback`, highlighted for the auditor to
  re-check), หัวจ่ายหลัก (`main`), or เลือกเอง (`manual`, set when a person
  picks the account by hand). The derivation has **two** inputs — the subject
  and the payee's own bank — so changing *either* re-derives every line except
  the `manual` ones, which stay frozen because a person already decided them.
- **Voucher journal / ใบสำคัญ** (`account.payment.journal_id`): the document
  type (PV/RV/PVR/PAR) that numbers the payment — its sequence *is* the voucher
  number, which is why it stays a document type and never becomes a bank account.
  A paying account is therefore one of the journal's payment method lines, and
  several banks appear as several lines on one journal. Choosing the paying
  account settles the voucher, not the other way round. KMITL settles a payable in
  one step (no bank statement), so nothing later clears the money account: what
  Odoo calls the outstanding account is simply the final one here.
- **Payment Method / วิธีจ่าย** (`account.payment.method`, outbound): *how* a
  payee is paid — เงินโอน / เช็ค / เงินสด. It is **not a field anyone sets on a
  payment line**: a paying account already names its method, so choosing the
  account chooses the method and the two cannot contradict each other. The
  subject carries one (`default_payment_method_id`) for a single purpose — to say
  which of a bank's paying accounts auto-matching means.

## The two sides of a payment entry have two owners

Every payment writes one entry with two sides, and each side has its own master
data. Conflating them is what produced two competing notions of "payment method".

- **Money side** — out of (or into) which account, by which means, under which
  voucher: the **paying account** above, i.e. one of Odoo's payment method lines.
- **Counterpart side** — what the money *is*, i.e. which receivable, payable or
  deposit liability it settles or creates: `kmitl.payment.type`
  (เงินรับฝากค้ำประกัน, เงินยืม, …) through its override account. This is why
  `advance_payment` and `purchase_guarantee` add records of their own. It says
  nothing about how money moves; a record that did (จ่ายเช็ค, จ่ายเงินสด) was on
  the wrong side of the entry and is gone.

A record describing the money side has no business in `kmitl.payment.type`, and
vice versa.

## Terms

- **Payment Line / รายการจ่ายเงิน** (`disbursement.payment.line`): **one payee,
  one payment.** The request line (`disbursement.request.line`) is one *item*
  being reimbursed, so a payee with three receipts has three of them; the
  payment line is the payee-level row that becomes exactly one
  `account.payment` against exactly one posted bill. It is where the three
  payment axes and the payee's bank account live, and it reads its amount from
  the **posted bill** — the money that will actually leave, net of WHT — not
  from the sum of the request lines, which is only what was asked for. Made
  when the request reaches `bills_posted`, i.e. when the payee set is final.
  Thai keeps the two apart by document weight: a payment line is a
  **รายการ**จ่ายเงิน (a row), the `account.payment` it becomes is an
  **ใบ**จ่ายเงิน (a document). Never call a payment "รายการจ่ายเงิน".
- **Payment Review / ตรวจทานก่อนสร้างใบจ่าย**: the finance office's read-back
  of every payment line before the payments are created. It is a checkpoint,
  not an approval — nothing about the request changes state. Finance may
  correct only the two **banking coordinates** — the paying account (*from*
  where, and thereby *by which means*) and the payee's bank account (*to*
  where). Who is paid and how much are not theirs to touch: those were settled
  by round-1 approval and by the posted bill.
- **Payment Audit** (`action_audit`, `bills_posted → payment_audited`): the
  auditor checks the disbursement documents after the bills are posted.
- **Payment Authorization** (`action_authorize`, `payment_audited →
  payment_authorized`): the rector's delegate authorises the money to be paid.
- **Payment** (`action_create_payment`, run while `payment_authorized`, after
  the Payment Review): the finance office creates one **draft**
  `account.payment` per payment line (net of WHT). Submitting them is a
  deliberate **separate** step, because submitting is what makes a payment
  exportable to the bank (`state = submitted` is the export's entry condition)
  and what registers a cheque — the officer decides when that happens, not the
  creation. The request stays at `payment_authorized` while the payment is in
  transit.
- **Bank Result** (`account.payment.bank_result_status`): the actual outcome
  of an outbound payment (`success` / `failed`). For transfers it is recorded
  from the bank payment export line; for cheques the finance office confirms
  it **manually** on the payment (deliberately NOT hooked to the cheque
  register lifecycle — the register remains a control log for numbering,
  printing and clearing status only).
- **Cheque timing note**: a DR cheque payment gets its cheque-register row at
  **submit** (not at post, as non-DR cheque payments do), because in this
  workflow posting happens last (clearing) while the physical cheque must be
  numbered, printed and handed over long before that.
- **A cheque is booked against the bank account it is drawn on**, the same GL a
  transfer out of that account would use — there is no "เช็คจ่าย" holding
  account and therefore no second entry when the cheque is presented. That a
  cheque is issued but not yet presented is tracked by the cheque register
  (`clearing_date`), not by the ledger.
- **Paid** (`action_confirm_paid`, `payment_authorized → paid`): the finance
  office confirms every payment of the request succeeded at the bank. The money
  has left; the accounting entry is **not** posted yet.
- **Cleared / ล้างหนี้** (`paid → cleared`): the accounting office posts the
  payment move through the **same account.move maker-checker as the vendor
  bill** (Approve = post). Posting reconciles the payment against the bill,
  clearing the payable. Set in `account_move._post`. This is the KMITL sense of
  "ล้างหนี้" — recording the cash-out and matching it to the liability.

## Rules

- The workflow is **forward-only** in round 2: there is no reject/return. A
  request that must be corrected is cancelled (before payment) or the bill is
  reversed by accounting.
- **Budget is untouched** in round 2. It is obligated and consumed exactly once
  at round-1 `approved` and never re-cut here.
- A DR payment move can be **posted only after the request is `paid`** and the
  payment's bank result is `success` (guard in `account_move._post`). A failed
  bank transfer therefore never produces an accounting entry.
- **Full payment only** — each bill is paid in full (no partial). One payment
  line → one bill → one payment; the DR reaches `paid` only when every payment
  is confirmed success, and `cleared` only when every payment is posted.
- **One payee cannot be paid two ways.** This is not a rule that is checked —
  it is a rule that cannot be broken, because the payee-level payment line is
  the only place a method or a paying account can be recorded.
- **A payment line's banking coordinates are editable exactly while no payment
  contradicts them** — the auditor's during Payment Audit, the finance
  office's during Payment Review, nobody's once the `account.payment` exists.
  The rule is phrased against the payment rather than against a list of states,
  so it stays true if the workflow ever grows another step.

## System note

Payments linked to a DR (`account.payment.disbursement_request_id`) are posted
by accounting through the account.move approval queue, exactly like the bill.
The deferred reconcile that normally lives in `account.payment.action_post`
runs on the move-posting path here, so **posting a DR payment == clearing it**.

See `docs/adr/0001-payment-execution-via-account-move-workflow.md`.
