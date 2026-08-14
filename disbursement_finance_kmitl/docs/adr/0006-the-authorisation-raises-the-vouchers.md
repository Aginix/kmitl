# 0006 — Authorising a disbursement is what raises its payment vouchers

- Status: accepted
- Date: 2026-08-14
- Amends: ADR-0005 (points 2 and 4, and its rejection of two dates)
- Builds on: ADR-0002 (one payee, one payment line, one voucher)

## Context

ADR-0005 gave the finance office its own lifecycle on the voucher and made
`finance_state = 'confirmed'` the gate an e-payment file selects on. It left the
raising of the vouchers where it had always been: with the finance office, as
two presses after the authorisation.

In practice that is not two presses. A request with twelve payees is

1. *Review Before Creating Payments* (optional),
2. *Create Payment* — twelve vouchers, all `finance_state = 'draft'`,
3. **open each voucher and press ยืนยันพร้อมส่งธนาคาร** — twelve forms, twelve
   presses of the same button, because there is no batch confirm anywhere,

before the officer can begin the thing they actually came to do, which is put the
twelve rows into a file and upload it. None of the three steps is a decision. The
banking coordinates were decided by the auditor at **Payment Audit** and validated
there (`_check_payment_classification`); the authorisation settled that the money
may leave; the amounts came from the posted bills. The finance office is retyping
a conclusion someone else reached.

## Decision

**1. `action_authorize` raises the vouchers.** One press by the rector's delegate
creates one `account.payment` per payment line and confirms each for the bank, so
the finance office receives vouchers that are numbered, money-side frozen, and
selectable into an e-payment file. Their first act on a request is now the file.

**2. Raising them is *not* part of the authorisation's transaction.** What can
fail is a banking coordinate — a payee whose bank account was removed after the
audit, a หัวจ่าย naming no bank — and none of that is the authorizer's to fix or
to be stopped by. The state write happens first; the creation runs inside a
savepoint; a failure is posted to the request's chatter and leaves the finance
office's Todo where it was. `action_create_payment` survives as the way back in.

**3. The finance office no longer has a correction window before the voucher
exists.** `action_open_payment_review` and its button are removed. **Payment
Audit** is the single checkpoint on the banking coordinates. A coordinate found
wrong afterwards is corrected on the voucher itself: *ยกเลิกการยืนยัน* →
correct → *ยืนยันพร้อมส่งธนาคาร*, which ADR-0005 already allows for as long as
the voucher is not yet in a file.

**4. The voucher's `date` is the day it was authorised, and it never moves.**
This amends ADR-0005 point 4, which required `date` to be the day the money left.
`date` is what numbers the voucher — KMITL numbers ใบสำคัญจ่าย `PV/2026/08/0001`,
month-reset, and Odoo's `sequence.mixin` refuses a date whose month disagrees with
the number it already carries. A voucher number that could change after it was
issued was judged worse than a period that can be a month early, so the date is
pinned where the number is.

**5. The withholding-tax certificate is dated from the e-payment file.**
`withholding.tax.cert.date` reads `payment_id.payment_export_id.effective_date`,
falling back to the voucher's date for cheques and cash, which never travel in a
file. The withholding is dated by law from the day the income was paid —
ภ.ง.ด.3/53 is filed by the 7th of the month *following the month of payment* — and
the effective date is the only record of that day, because it is what the bank was
told to act on.

**6. A voucher carries its request, and so does the entry.** The payment already
had `disbursement_request_id`; the journal entry gets
`payment_disbursement_request_id`, a *related* field on the payment's own link. It
is deliberately not `account.move.disbursement_request_id` — that column is what
`disbursement.request.bill_ids` reads, and the One2many does not filter by move
type, so storing a request on a payment move would file the voucher among the
request's bills.

## Alternatives rejected

- **Let the e-payment file settle the date, and number the voucher then.** The
  cleanest accounting answer: one date, always the day the money left, so the
  period, the certificate and the ภ.ง.ด. all agree. Rejected because the voucher
  would carry no ใบสำคัญจ่าย number between authorisation and file — and, in the
  cross-month case, would be renumbered. A number that has been issued must not
  change.
- **Two dates on the voucher** (an issue date that numbers it, beside the real
  payment date), which is what ADR-0005 rejected for a different reason. Odoo
  binds the number to `date` through `sequence.mixin._sequence_date_field` and
  through `account.move._get_last_sequence_domain`, which writes `date` into its
  SQL; driving the number from a second field means reimplementing core's
  numbering for payment moves only. And Thai practice does not put two dates on
  one voucher — it uses two documents, which this system already has: the ใบขอเบิก
  and the e-payment file are the "before" documents, and the ใบสำคัญจ่าย is the
  one that says the money went.
- **Refusing an effective date in a different month from the voucher.** Zero code
  and no mismatch, but it fails at exactly the moment it would be needed — the
  1 October fiscal-year turn, when there is a queue.
- **Making the authorisation atomic** (a coordinate error un-does the
  authorisation). It puts a finance-office error message in front of the rector's
  delegate and asks them to hold the whole request over it.
- **Keeping Payment Review by opening the banking coordinates during
  `payment_audited`.** It preserves a window the finance office was not using —
  the auditor sets and validates those coordinates one step earlier — at the cost
  of two offices editing the same rows while the request sits in the authorizer's
  queue.

## Consequences

- **In a cross-month case the GL period and the ภ.ง.ด. month disagree by design.**
  A request authorised 30 September whose file leaves 3 October books in
  September and is filed for October. The reconciliation of WHT per the books
  against WHT per the filing has to be done by hand for those. This is accepted:
  the alternative was a voucher number that moves.
- `create_uid` on an automatically raised voucher is OdooBot — the creation is a
  system derivation run sudo, because the authorizer holds no accounting rights
  (the same reasoning as ADR-0003). Who authorised is on the request's chatter and
  in `rector_approver_id`; who is responsible for the voucher is `assigned_to`,
  set by `finance_kmitl_assignment` at creation as before.
- The finance office's Todo (`mail_activity_dr_to_pay`) now means "put these in a
  file", not "create the payments".
- Cancelling an automatically raised voucher leaves a gap in the ใบสำคัญจ่าย
  sequence, as cancelling any confirmed voucher already did — but there is now a
  numbered voucher from the moment of authorisation, so the window in which one
  can be cancelled is longer.
- A payment line's banking coordinates are editable only during **Payment
  Audit**. The rule in `_banking_editable` is unchanged and still true as
  written — "editable exactly while no payment contradicts them" — it simply has
  one fewer state in which it can be true.
