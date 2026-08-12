# 0005 — The finance office and the accounting office each run their own lifecycle on the payment voucher

- Status: accepted (designed; **not yet built**)
- Date: 2026-08-12
- Supersedes: ADR-0004
- Builds on: ADR-0001 (the accounting office posts the payment, and posting is clearing)

## Context

ADR-0004 left the e-payment export gated on `state = 'submitted'` and had the
**finance** office submit the voucher. The accounting office therefore received a
voucher that was already submitted: only the approver had anything left to do, the
maker step was skipped, and nobody in the office that owns the books could correct
what was wrong in them — the analytic dimensions above all, which is exactly what
gets mistyped. `submitted` also claimed a maker had acted when none had.

The two offices need two lifecycles, and there is only one document to hang them
on: `account.payment` is `_inherits`-bound to `account.move`, so a payment *is* a
move — one row, one `state`, created together. Splitting the record was costed and
rejected in ADR-0004 and that costing still holds.

The bank's own result file is never imported into Odoo (ADR-0004); a rejected
transfer is settled outside the system.

## Decision

**1. `state` belongs to the accounting office alone.** A payment voucher stays
`draft` through the finance office's entire stretch and then runs the standard KMITL
maker-checker (`draft → submitted → posted`) exactly like every other voucher.
`finance_kmitl`'s bespoke `account.payment.action_submit` is dropped — a payment
stops being special.

**2. The finance office gets its own lifecycle, `finance_state`:
`draft → confirmed → paid`.**

- **`confirmed`** (ยืนยันพร้อมส่งธนาคาร) freezes the money side, assigns the voucher
  number, and is what the e-payment export selects on — replacing `state =
  'submitted'` in the three places that test it. The number is assigned here and not
  at the accounting maker's Submit because core displays an unnumbered payment as
  "Draft Payment", and a file of twelve rows all reading "Draft Payment" is unusable.
- **`paid`** (ยืนยันจ่ายสำเร็จ) is the finance office's single assertion that the money
  reached every payee, and it is the **Hand-over**.

**3. The lock is per side, not per document.**

| Money side — frozen from `confirmed` | Booking side — the accounting maker's to fix |
| ------------------------------------ | -------------------------------------------- |
| amount, payee, payee's bank account, paying account (หัวจ่าย), currency, payment/partner type, journal, **date** | analytic distribution (the 6 dimensions), reference / description, attachments, operation type (ประเภทธุรกรรม) and therefore the counterpart account |

**4. `date` is money-side.** There is one date field and it is both the day the money
left and the accounting period. Freezing it keeps the withholding-tax certificate and
the ภ.ง.ด. filing in the month the payment was actually made; an entry is always
booked in the period the money left.

**5. `_synchronize_to_moves` is fixed to preserve the withholding tax.** Changing the
operation type rebuilds the entry, and core keeps only the *amount* of the write-off
lines — merging them into one line built from the first one's name/account/currency
and dropping `wht_tax_id` and `tax_base_amount`, the fields the WHT certificate and
the ภ.ง.ด. report are made of. Since core passes write-off values straight into
`account.move.line` create values, the fix is to hand it richer per-line values
rather than to reimplement its rebuild.

**6. `bank_result_status` stops being a gate.** `finance_state = paid` says what it
said. The per-row detail stays on the e-payment file (`epayment_status`,
`epayment_note`), which is the finance office's own record.

**7. The maker of a handed-over voucher is whichever accounting person picks it up.**
The creator rule ("you do not submit a colleague's work") has nothing to protect on a
voucher no accounting person authored.

**8. Work reaches the accounting office through the disbursement request**, which is
KMITL's navigation document: one Todo per request at the Hand-over, plus a queue at DR
state `paid`. A payment made by hand has no request, so it carries its own Todo. One
list shows every handed-over voucher of either kind, so nothing falls between them.

**9. Forward-only after the Hand-over.** Before it, a `confirmed` payment may be
unconfirmed back to `draft` while it is not yet in a file — there is nothing to
protect until the bank has the instruction.

## Alternatives rejected

- **What ADR-0004 built** (finance submits; the voucher arrives submitted). The
  accounting office cannot correct the booking, which is the whole reason it has a
  maker step.
- **Freezing the whole document with `state = 'submitted'`** as the lock. It freezes
  the booking side too — the one side the accounting maker exists to fix.
- **Two dates** (the real payment date beside a separate accounting date). In practice
  the office books in the period the money left, so the second date would only restate
  the first, and every extra date is another thing that can disagree.
- **Forbidding the operation type to change after the Hand-over**, so the WHT rebuild
  trap stays shut. Rejected in favour of fixing the trap: the loss is a real defect
  that also bites anyone changing the date or the amount of a WHT payment while it is
  still the finance office's.
- **A Todo per voucher to every accounting maker.** A twelve-payee request would put
  sixty rows into five inboxes for one press, and the request already is the document
  KMITL navigates by.
- **A role-addressed Todo** (`mail_activity_todo_role_unit`). It would need a
  `res.users.role` for accounting created from scratch and then kept in step with the
  group that already identifies the same people — two membership registers that drift.
- **A Recall of the Hand-over.** The phase is forward-only; a confirmation given by
  mistake is corrected in the books, not by walking the workflow backwards.

## Consequences

- **Reject after the money left becomes safe**, which closes the risk ADR-0004 left
  open. `draft` no longer means "everything is editable": a rejected voucher goes back
  to the accounting maker with the money side still frozen, so Reject can only ever
  mean "the booking is wrong", never "the payment was wrong".
- `submitted_by` on a payment voucher is the **accounting maker** — the opposite of
  ADR-0004, where it was the finance officer.
- Every field on the payment form has to be classified as money side or booking side.
  The blanket `readonly` when `state != 'draft'` is gone, and a field nobody classifies
  is a field left editable after the bank has paid.
- The finance office's whole stretch happens on a `draft` move, so a numbered but
  unposted voucher exists while the money is at the bank. Cancelling one leaves a gap
  in the ใบสำคัญจ่าย sequence, as it already did.
- Two Todos and one list have to exist for the accounting office; without them a
  handed-over voucher is a draft entry among all the other draft entries.
- **A migration is needed**, not just a schema change: payments already `submitted`
  and waiting in the approval queue have to be moved onto the new shape
  (`bank_result_status = success → finance_state = paid`, and a submitted-but-unposted
  voucher returned to `draft` for the accounting maker) — with a decision for any
  voucher an approver has already touched.
