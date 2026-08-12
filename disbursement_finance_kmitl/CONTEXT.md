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

## Words that describe a payment, and which one means what

Five records sit near a payment and three of them have "type" or "subject" in their
name. They answer different questions and must not be conflated.

| Term                                | Model                               | What it says                                                                                                                                                                                                                                         |
| ----------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **เรื่องที่จ่าย** (Payment Subject) | `kmitl.payment.subject`             | _What the disbursement is for_, which is what decides the **paying account** each payee is served from. One per request, chosen by the auditor.                                                                                                      |
| **ประเภทธุรกรรม** (Operation Type)  | `kmitl.payment.type`                | The **counterpart** side: what the money _is_ — which receivable, payable or deposit liability it settles or creates (เงินรับฝากค้ำประกัน, เงินยืม), through its override account. Says nothing about how money moves.                               |
| **ลักษณะการจ่าย**                   | `disbursement.request.payment_type` | `direct` / `advance` / `prepaid`, inherited from the approval request. Nothing to do with either of the above.                                                                                                                                       |
| **หัวจ่าย** (Paying Account)        | `account.payment.method.line`       | The **money** side: out of which bank account the money leaves, by which means, under which voucher, booked against which GL account. One choice, one of Odoo's own records.                                                                         |
| **วิธีจ่าย** (Payment Method)       | `account.payment.method`            | เงินโอน / เช็ค / เงินสด. **Not a field anyone sets**: a paying account already names its method, so choosing the account chooses the method and the two cannot contradict each other.                                                                |
| **ใบสำคัญ** (Voucher)               | `account.journal`                   | The document type (PV/RV/PVR/PAR) that numbers the payment — its sequence _is_ the voucher number, which is why it stays a document type and never becomes a bank account. Choosing the paying account settles the voucher, not the other way round. |

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
- **Payment Review / ตรวจทานก่อนสร้างใบจ่าย** (`action_open_payment_review`): the
  finance office's read-back of every payment line before the payments are created. It
  is a checkpoint, not an approval — nothing about the request changes state. Finance
  may correct only the two **banking coordinates** — the paying account (_from_ where,
  and thereby _by which means_) and the payee's bank account (_to_ where). Who is paid
  and how much are not theirs to touch: those were settled by round-1 approval and by
  the posted bill.
- **Payment Audit** (`action_audit`, `bills_posted → payment_audited`): the auditor
  checks the disbursement documents after the bills are posted, and sets the
  เรื่องที่จ่าย that gives every payee its paying account.
- **Payment Authorization** (`action_authorize`,
  `payment_audited → payment_authorized`): the rector's delegate authorises the money to
  be paid.
- **Payment** (`action_create_payment`, run while `payment_authorized`, after the
  Payment Review): the finance office creates one `account.payment` per payment line
  (net of WHT), submits it and sends it to the bank via a bank payment export. The
  payment carries the line's paying account, and takes its voucher journal from it. The
  request stays at `payment_authorized` while the payment is in transit.
- **Bank Result / ผลการจ่าย** (`account.payment.bank_result_status`): the finance
  office's **assertion** that the money reached the payee (`success` / `failed`) — not
  something a bank ever told Odoo. The bank's own result file is never imported (see
  Rules), so this field carries a person's word, given once per request at **Paid**, and
  it is the only thing downstream reads. _Avoid_ reading it as "what the bank reported":
  nothing in the system knows that.
- **Paid / จ่ายครบ** (`action_confirm_paid`, `payment_authorized → paid`): the finance
  office's assertion that every payee of the request has their money. It is the
  **single** human confirmation of the whole payment phase — one press, on the request,
  standing for every payment it covers — so nothing asks the officer to confirm the same
  fact twice in two places. What may be checked before it is not "has each payment been
  confirmed" (Odoo learns that from no one but this press) but whether the e-payment file
  was actually produced for the payments that travel in one. The money has left; the
  accounting entry is **not** posted yet. This is the **Hand-over** (below) — the one
  moment the request stops being the finance office's and becomes the accounting
  office's. Never call this "เคลียร์": เคลียร์/ล้างหนี้ is the accounting act that comes
  after it.
- **Hand-over / ส่งมอบให้บัญชี** (`paid`): the single moment a request's payments stop
  being the finance office's work and become the accounting office's. Before it, a
  voucher is numbered and its **money side** is frozen, but it belongs to finance — it is
  theirs to put in an e-payment file, chase at the bank, and vouch for. After it, the
  voucher waits in `draft` as **the accounting office's entry to book**: their maker
  corrects the booking side, submits it, and their approver approves = posts = ล้างหนี้.
  It is *not* a hand into the approval queue — the accounting office's own maker step
  runs from the beginning, which is what lets them fix what is wrong in the books
  _(designed — ADR-0005)_. There is exactly **one** such moment per request, and it is
  per **request**, not per payment: a payee whose transfer succeeded waits for the payees
  whose did not, because a request is handed over whole or not at all. It is also what
  makes the work visible — one Todo per request to the accounting makers, and a queue at
  `paid` — because the request, not the voucher, is what KMITL navigates by.
  _Avoid_: "ส่งให้บัญชี / submit ให้บัญชี" (Submit is the accounting maker's action on the
  voucher, not the hand-over), "เคลียร์".
- **Cleared / ล้างหนี้** (`paid → cleared`): the accounting office posts the payment
  move through the **same account.move maker-checker as the vendor bill** (Approve =
  post). Posting reconciles the payment against the bill, clearing the payable. Set in
  `account_move._post`. This is the KMITL sense of "ล้างหนี้" — recording the cash-out
  and matching it to the liability.

## Rules

- The workflow is **forward-only** in round 2: there is no reject/return. A request that
  must be corrected is cancelled (before payment) or the bill is reversed by accounting.
- **The bank's result file is never imported into Odoo.** A transfer the bank rejects is
  chased and settled **outside the system** — a corrected transfer made at the bank's own
  portal, a cheque handed over — and Odoo learns of it only through the finance office's
  one assertion at **Paid**. Nothing in the payment phase waits for a machine-readable
  answer from a bank, and no per-payee outcome is imported, matched or reconciled against
  a file. A payee is therefore never re-paid inside a request: the request has one set of
  payments, and the exceptions among them are resolved elsewhere. What the finance office
  writes down about an exception **stays with the finance office** — the note lives on the
  row of the e-payment file (`bank.payment.export.line.epayment_note`), which the
  accounting office never opens. The entry they post asserts only that the money left, and
  that assertion is the finance office's word at **Paid**, nothing finer-grained.
- **The accounting office sees a payment only at the Hand-over** _(designed — ADR-0005)_.
  What lets the finance office put a voucher in an e-payment file is a finance-side fact
  (`finance_state = confirmed`), never `state` — `state` belongs to the accounting office,
  and a voucher sits in `draft` for the whole of the finance office's stretch. So no list
  of theirs shows an entry they could not act on, and neither office's field is read by
  the other. See [`finance_kmitl/CONTEXT.md`](../finance_kmitl/CONTEXT.md) for the
  money-side / booking-side split that makes a `draft` voucher safe to leave with them.
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
  contradicts them** — the auditor's during Payment Audit, the finance office's during
  Payment Review, nobody's once the `account.payment` exists. The rule is phrased
  against the payment rather than against a list of states, so it stays true if the
  workflow ever grows another step.
- **One e-payment file debits one account.** The paying account is chosen on the bank
  payment export first, and the payments that can be picked into it are narrowed to the
  ones paid from it — a DR whose payees span four paying accounts produces four files.

## System note

Payments linked to a DR (`account.payment.disbursement_request_id`) are posted by
accounting through the account.move approval queue, exactly like the bill. The deferred
reconcile that normally lives in `account.payment.action_post` runs on the move-posting
path here, so **posting a DR payment == clearing it**.

See `docs/adr/0001-payment-execution-via-account-move-workflow.md`.
