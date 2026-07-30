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

Set by the **auditor** during Payment Audit. Three orthogonal concepts:

- **Payment Subject / เรื่องที่จ่าย** (`kmitl.payment.subject`, master data in
  `finance_kmitl`, one per DR, chosen by the auditor): *what* the payment is
  for (e.g. เงินเดือน, เงินยืม/สำรองจ่าย, จ่ายตรงคู่ค้า, ค่าน้ำค่าไฟ). Admins
  maintain the list. Not to be confused with `DR.payment_type`
  (direct/advance/prepaid, inherited from the approval) nor with
  `kmitl.payment.type` (the mechanical operation type that carries
  `is_cheque` / journal / override account).
- **Paying Account / หัวจ่าย** (`account.account` flagged
  `is_paying_account`): *which* account the money leaves from. In the KMITL
  chart one GL account is one real bank account, so the account itself carries
  `paying_bank_id` and `paying_acc_number` — the bank export and the cheque
  register read them there instead of from a journal. Cash accounts qualify
  too (KMITL types cash-in-hand `asset_current` and banks `asset_cash`, so the
  flag, not the type, decides).
- **Allowed / default paying accounts** (on the subject): the accounts a
  subject may pay from, plus the fallback. One mechanism covers every real
  case — allow a single account and it is always used (salary → KTB, direct
  vendor → SCB); allow several and **each payee is served from the account at
  their own bank** (เงินยืม/สำรองจ่าย), falling back to the default when no
  account matches. Set per DR **line**, defaulted at audit time.
- **Voucher journal / ใบสำคัญ** (`account.payment.journal_id`): the document
  type (PV/RV/PVR/PAR) that numbers the payment. It is *not* a bank account —
  KMITL settles a payable in one step (no bank statement, no outstanding
  account), so the money side of the entry is booked straight against the
  paying account (`_compute_outstanding_account_id` is overridden to return
  it).
- **Payment Method / วิธีจ่าย** (per DR **line**, defaulted from the subject):
  *how* a payee is paid — เงินโอน / เช็ค / เงินสด. Any subject can be paid any
  way. Lines of the same payee must share one method, one payee bank account
  and one paying account (one bill per payee → one full payment per bill). The
  method resolves to a `kmitl.payment.type` (transfer → จ่ายเงินออก, cheque →
  จ่ายเช็ค with `is_cheque`) when finance creates the payment.

## Terms

- **Payment Audit** (`action_audit`, `bills_posted → payment_audited`): the
  auditor checks the disbursement documents after the bills are posted.
- **Payment Authorization** (`action_authorize`, `payment_audited →
  payment_authorized`): the rector's delegate authorises the money to be paid.
- **Payment** (`action_create_payment`, run while `payment_authorized`): the
  finance office creates one `account.payment` per posted bill (net of WHT),
  submits it and sends it to the bank via a bank payment export. The request
  stays at `payment_authorized` while the payment is in transit.
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
- **Full payment only** — each bill is paid in full (no partial). For a
  multi-partner DR there is one payment per bill; the DR reaches `paid` only
  when every payment is confirmed success, and `cleared` only when every
  payment is posted.

## System note

Payments linked to a DR (`account.payment.disbursement_request_id`) are posted
by accounting through the account.move approval queue, exactly like the bill.
The deferred reconcile that normally lives in `account.payment.action_post`
runs on the move-posting path here, so **posting a DR payment == clearing it**.

See `docs/adr/0001-payment-execution-via-account-move-workflow.md`.
