# CONTEXT — Disbursement ↔ KMITL Finance Bridge

Glossary for the **post-bill payment-execution workflow** on `disbursement.request`
(DR). This module owns the phase that runs **after** the accounting office posts the
vendor bills.

## The two approval rounds (do not conflate)

The word "ตรวจสอบ / verify" and "อนุมัติ / approve" appear in **two different rounds**.
They use different vocabulary and different security groups.

| Concept | Round 1 — request approval (module `disbursement`, before bill)                                                    | Round 2 — payment execution (this module, after bill)                                                                                |
| ------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Verify  | **Request Verification** — state `verified`, "ตรวจสอบคำขอ", `group_disbursement_officer`                           | **Payment Audit** — state `payment_audited`, "ตรวจสอบการเบิกจ่าย", `group_disbursement_payment_auditor`                              |
| Approve | **Request Approval** — state `approved` (obligates + consumes budget), "อนุมัติคำขอ", `group_disbursement_manager` | **Payment Authorization** — state `payment_authorized`, "อนุมัติเบิกจ่าย" (rector delegate), `group_disbursement_payment_authorizer` |

Round 2 deliberately uses the verbs **audit** and **authorize** so it never collides
with round 1's verify/approve.

The two rounds also live in **different apps**: round 1 in **การขอเบิก**, which is the
requesting unit's, and round 2 in **การเงิน**, which is the treasury office's. An app
here answers _whose desk is this_, not _which document is this_ — see
[`finance_kmitl` ADR-0005](../finance_kmitl/docs/adr/0005-the-finance-app-is-the-treasury-offices-house.md).
Within การเงิน the two round-2 steps are separated the same way: the audit is a clerk's
step in the paying run and sits with it under **การเงินจ่าย**, while the authorisation
gets its own **ผู้อนุมัติ** heading.

## Words that describe a payment, and which one means what

Five records sit near a payment and three of them have "type" or "subject" in their
name. They answer different questions and must not be conflated.

| Term                                | Model                               | What it says                                                                                                                                                                                                                                            |
| ----------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **เรื่องที่จ่าย** (Payment Subject) | `kmitl.payment.subject`             | _What the disbursement is for_, which is what decides the **paying account** each payee is served from. One per request, chosen by the auditor, and copied read-only onto every voucher it raises so a payment records why it left the account it left. |
| **ประเภทธุรกรรม** (Operation Type)  | `kmitl.payment.type`                | The **counterpart** side: what the money _is_ — which receivable, payable or deposit liability it settles or creates (เงินรับฝากค้ำประกัน, เงินยืม), through its override account. Says nothing about how money moves.                                  |
| **ลักษณะการจ่าย**                   | `disbursement.request.payment_type` | `direct` / `advance` / `prepaid`, inherited from the approval request. Nothing to do with either of the above.                                                                                                                                          |
| **หัวจ่าย** (Paying Account)        | `account.payment.method.line`       | The **money** side: out of which bank account the money leaves, by which means, under which voucher, booked against which GL account. One choice, one of Odoo's own records.                                                                            |
| **วิธีจ่าย** (Payment Method)       | `account.payment.method`            | เงินโอน / เช็ค / เงินสด. **Not a field anyone sets**: a paying account already names its method, so choosing the account chooses the method and the two cannot contradict each other.                                                                   |
| **ใบสำคัญ** (Voucher)               | `account.journal`                   | The document type (PV/RV/PVR/PAR) that numbers the payment — its sequence _is_ the voucher number, which is why it stays a document type and never becomes a bank account. Choosing the paying account settles the voucher, not the other way round.    |

A record describing the money side has no business on `kmitl.payment.type`, and vice
versa. See `finance_kmitl/docs/adr/0001-paying-account-is-a-payment-method-line.md`.

**Auto-match / จับคู่ตามธนาคารผู้รับ** is a flag on the subject: when on, each payee is
served from the **allowed** account held at the bank of their own bank account
(เงินยืม/สำรองจ่าย); a payee whose bank matches none falls to the subject's account,
which then reads as the **fallback / หัวจ่ายสำรอง**. When off, every payee pays from
that same account, which reads as the **main / หัวจ่ายหลัก** (เงินเดือน → KTB,
จ่ายตรงคู่ค้า → SCB) — one field, two roles, the label following the flag.

**Match Result / ผลลัพธ์การจับคู่** (`paying_account_match`) is the **provenance** of a
row's paying account — ตรงธนาคารผู้รับ (`bank`), ไม่ตรงกับหัวจ่ายหลัก (`fallback`,
highlighted so the auditor re-checks exactly those), หัวจ่ายหลัก (`main`), or เลือกเอง
(`manual`). The derivation has **two** inputs — the subject and the payee's own bank —
so changing _either_ re-derives every row except the `manual` ones, which stay frozen
because a person already decided them.

Both inputs re-derive **in the open form**, not only on save: picking the เรื่องที่จ่าย
fills in every row's หัวจ่าย on the spot, so the rows that fell to the fallback are
re-checked in the same pass over the payees rather than in a second one after saving.
The provenance column is `force_save` for exactly that reason — it is readonly, the web
client drops readonly fields from a save, and without it the เลือกเอง a row has just
reported would never reach the database, letting the re-derivation in that same save
overwrite the account the person just picked.

## Terms

- **Payment Line / รายการจ่ายเงิน** (`disbursement.payment.line`): **one payee, one
  payment.** The request line (`disbursement.request.line`) is one _item_ being
  reimbursed, so a payee with three receipts has three of them; the payment line is the
  payee-level row that becomes exactly one `account.payment` against exactly one posted
  bill. It is where the paying account and the payee's bank account live, and it reads
  its amount from the **posted bill** — the money that will actually leave, net of WHT —
  not from the sum of the request lines, which is only what was asked for. Made when the
  request reaches `bills_posted`, i.e. when the payee set is final. Thai keeps the two
  apart by document weight: a payment line is a **รายการ**จ่ายเงิน (a row), the
  `account.payment` it becomes is an **ใบ**จ่ายเงิน (a document). Never call a payment
  "รายการจ่ายเงิน".
- **Payment Audit** (`action_audit`, `bills_posted → payment_audited`): the auditor
  checks the disbursement documents after the bills are posted, and sets the
  เรื่องที่จ่าย that gives every payee its paying account. It is the **only** checkpoint
  on the banking coordinates — the finance office has none of its own, so a coordinate
  that is wrong after this is corrected on the voucher itself.
- **ตราผู้กระทำรอบ 2 / Round-2 stamps** (`payment_auditor_id`, `payment_audit_date`,
  `payment_authorizer_id`, `payment_authorize_date`): who took each round-2 step and
  when, recorded the way round 1 records its two approvals. Round 2 left the answer in
  the chatter alone, which is not something a list can be built on — and the
  authorizer's own history (**รายการที่อนุมัติแล้ว**) has to stand on the stamp rather
  than the state, or a request would drop out of it the moment it is paid.
- **Payment Authorization** (`action_authorize`,
  `payment_audited → payment_authorized`): the rector's delegate authorises the money to
  be paid, and that press is also what **raises the vouchers** — one `account.payment`
  per payment line (net of WHT), each numbered and confirmed for the bank, so the
  finance office's first act on the request is the e-payment file rather than turning
  the request into payments one press per payee. Raising them is not part of the
  authorisation's transaction: a coordinate that fails leaves the request authorized
  with the reason in the chatter. See ADR-0006. _Avoid_: reading "authorize" as touching
  only the request's state.
- **Payment** (`account.payment`, made by `_create_payments`): one payee's voucher
  against one posted bill. It carries the line's paying account and takes its voucher
  journal from it, and it is **dated the day the request was authorised** — that date is
  its accounting period and what numbers it, and neither may move afterwards. The
  request stays at `payment_authorized` while the payments are in transit.
  `action_create_payment` is the same work behind a button, kept only for the requests
  the authorisation could not raise vouchers for.
- **Bank Result / ผลการจ่าย** (`account.payment.bank_result_status`): the finance
  office's **assertion** that the money reached the payee (`success` / `failed`) — not
  something a bank ever told Odoo. The bank's own result file is never imported (see
  Rules), so this field carries a person's word, given once per request at **Paid**, and
  it is the only thing downstream reads. _Avoid_ reading it as "what the bank reported":
  nothing in the system knows that.
- **Paid / จ่ายครบ** (`payment_authorized → paid`): every payee of the request has their
  money, as the finance office says so. **Nobody presses this for the request as a
  whole.** A request's payees span several หัวจ่าย and are settled in as many different
  ways, and no two of those need be the same officer's — so each officer confirms only
  what they handled, in the place that knows it: closing an **ไฟล์ e-Payment** pays the
  transfer payees it carried, **มอบเช็ค** pays the payee that cheque was written for, and
  cash is confirmed on the voucher. The request arrives here when the last of them lands. See
  [ADR-0007](./docs/adr/0007-the-request-crosses-when-its-last-voucher-is-paid.md). The
  money has left; the accounting entry is **not** posted yet. This is the **Hand-over**
  (below) — the moment the request stops being the finance office's and becomes the
  accounting office's. Never call this "เคลียร์": เคลียร์/ล้างหนี้ is the accounting act
  that comes after it.
- **Hand-over / ส่งมอบให้บัญชี** (`paid`): the single moment a request's payments stop
  being the finance office's work and become the accounting office's. Before it, a
  voucher is numbered and its **money side** is frozen, but it belongs to finance — it
  is theirs to put in an e-payment file, chase at the bank, and vouch for. After it, the
  voucher waits in `draft` as **the accounting office's entry to book**: their maker
  corrects the booking side, submits it, and their approver approves = posts = ล้างหนี้.
  It is _not_ a hand into the approval queue — the accounting office's own maker step
  runs from the beginning, which is what lets them fix what is wrong in the books .
  There is exactly **one** such moment per request, and it is per **request**, not per
  payment: a payee whose transfer succeeded waits for the payees whose did not, because
  a request is handed over whole or not at all. It is also what makes the work visible —
  one Todo per request to the accounting makers, and a queue at `paid` — because the
  request, not the voucher, is what KMITL navigates by. _Avoid_: "ส่งให้บัญชี / submit
  ให้บัญชี" (Submit is the accounting maker's action on the voucher, not the hand-over),
  "เคลียร์".
- **Cleared / ล้างหนี้** (`paid → cleared`): the accounting office posts the payment
  move through the **same account.move maker-checker as the vendor bill** (Approve =
  post). Posting reconciles the payment against the bill, clearing the payable. Set in
  `account_move._post`. This is the KMITL sense of "ล้างหนี้" — recording the cash-out
  and matching it to the liability.

## Rules

- The workflow is **forward-only** in round 2: there is no reject/return. A request that
  must be corrected is cancelled (before payment) or the bill is reversed by accounting.
  The one exception is a **cheque that dies after it was handed over** — bounced, lost,
  out of date, drawn wrong. It is the only instrument that can fail once the payee is
  holding it, so cancelling it withdraws that payee's voucher back to `confirmed` and a
  replacement cheque is written on the same voucher. The **request does not follow it
  back**: it stays at `paid` and reports จ่ายแล้ว n-1/m, because the other payees still
  need booking and their queue should not be emptied over one of them. See
  `finance_kmitl` ADR-0007.
- **The bank's result file is never imported into Odoo.** A transfer the bank rejects is
  chased and settled **outside the system** — a corrected transfer made at the bank's
  own portal, a cheque handed over — and Odoo learns of it only through the finance
  office's one assertion at **Paid**. Nothing in the payment phase waits for a
  machine-readable answer from a bank, and no per-payee outcome is imported, matched or
  reconciled against a file. A payee is therefore never re-paid inside a request: the
  request has one set of payments, and the exceptions among them are resolved elsewhere.
  What the finance office writes down about an exception **stays with the finance
  office** — the note lives on the row of the e-payment file
  (`bank.payment.export.line.epayment_note`), which the accounting office never opens.
  The entry they post asserts only that the money left, and that assertion is the
  finance office's word at **Paid**, nothing finer-grained.
- **The accounting office sees a payment only at the Hand-over**. What lets the finance
  office put a voucher in an e-payment file is a finance-side fact
  (`finance_state = confirmed`), never `state` — `state` belongs to the accounting
  office, and a voucher sits in `draft` for the whole of the finance office's stretch.
  So no list of theirs shows an entry they could not act on, and neither office's field
  is read by the other. See [`finance_kmitl/CONTEXT.md`](../finance_kmitl/CONTEXT.md)
  for the money-side / booking-side split that makes a `draft` voucher safe to leave
  with them.
- **Budget is untouched** in round 2. It is obligated and consumed exactly once at
  round-1 `approved` and never re-cut here.
- A DR payment move can be **posted only after the request is `paid`** and the payment's
  bank result is `success` (guard in `account_move._post`). A failed bank transfer
  therefore never produces an accounting entry.
- **Full payment only** — each bill is paid in full (no partial). One payment line → one
  bill → one payment; the DR reaches `paid` only when every payment is confirmed
  success, and `cleared` only when every payment is posted.
- **One payee cannot be paid two ways.** This is not a rule that is checked — it is a
  rule that cannot be broken, because the payee-level payment line is the only place a
  paying account can be recorded, and it holds one.
- **A payment line's banking coordinates are editable exactly while no payment
  contradicts them** — the auditor's during Payment Audit, nobody's once the
  `account.payment` exists, which since ADR-0006 is from the authorisation onwards. The
  rule is phrased against the payment rather than against a list of states, so it stays
  true if the workflow ever grows another step.
- **The voucher's date and the day the money left are two different facts.** The voucher
  is dated when it was authorised, because that is what numbers it and what period it
  books in, and a number that has been issued must not change. The day the money
  actually left is the e-payment file's **effective date**, and that is what the
  withholding-tax certificate is dated from — the law dates the withholding by the day
  the income was paid. They agree except when a file leaves in a later month than the
  authorisation, and then they are deliberately allowed to differ. See ADR-0006.
- **One e-payment file debits one account.** The paying account is chosen on the bank
  payment export first, and the payments that can be picked into it are narrowed to the
  ones paid from it — a DR whose payees span four paying accounts produces four files.
- **Everything in the payment phase leads back to the ใบขอเบิก.** The request is the
  document KMITL navigates by, so the voucher, its journal entry and the e-payment file
  each carry a trail back to it. The file's trail is computed rather than stored
  (`bank.payment.export.disbursement_request_ids`, from
  `export_line_ids.payment_id.disbursement_request_id`): the relation is many-to-many in
  both directions — a file spans several requests, a request spans several files — and
  nothing would keep a stored copy honest. It names the request only when there is
  exactly one, and the per-row column is what answers it for a file carrying several.

## System note

Payments linked to a DR (`account.payment.disbursement_request_id`) are posted by
accounting through the account.move approval queue, exactly like the bill. The deferred
reconcile that normally lives in `account.payment.action_post` runs on the move-posting
path here, so **posting a DR payment == clearing it**.

See `docs/adr/0001-payment-execution-via-account-move-workflow.md`.
