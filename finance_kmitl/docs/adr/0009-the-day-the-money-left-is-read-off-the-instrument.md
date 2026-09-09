# The day the money left is read off the instrument

**วันที่จ่ายจริง** (`account.payment.paid_date`) is a computed, unstored field that
reads the day the money left off whatever carried it: an e-payment file's
**วันที่มีผลที่ธนาคาร**, a cheque's **วันที่บนเช็ค**, and — for cash, which has no
instrument — the voucher's own date, the day it was paid across the counter.

The concept is older than the field. `withholding_tax_cert` has dated the ภ.ง.ด.
certificate this way since the certificate had to survive a voucher raised in one month
and paid in the next (`disbursement_finance_kmitl` ADR-0006), and it did it by writing
the `or` chain out inline. The reports the finance office asked for are dated the same
way — a payment report whose axis is วันที่บนใบสำคัญจ่าย answers a question about when
things were authorised, not about what the treasury paid out — so the chain was about to
have a second, and then a third, home. Two copies of a definition are two places to
change it and one place to forget.

## Why the voucher's own date is not the answer

`account.payment.date` is money side and it never moves: it is the accounting period the
entry is booked in, and Odoo binds the ใบสำคัญจ่าย number to it, so a voucher numbered
`PV/2026/00001` cannot be re-dated into another year. It is the day the payment was
**authorised**. A file authorised on 28 September and given an effective date of 2
October moved its money in October, and both statements are true at once — which is
exactly why there have to be two fields and not one.

## Why it is not stored

The value is assembled from three models — `bank.payment.export`, `cheque.register` and
the payment itself — and any of the three can change under it: a draft file's effective
date is edited before it is confirmed, and a cheque that dies takes its voucher back to
`confirmed` for a replacement written on a new date (ADR-0007). Nothing in this module
makes a stored copy honest that the compute does not already make correct for free, and
a stored column would need a migration to fill on every existing voucher. This is the
same call `accounting_kmitl_reports` ADR-0001 made in refusing convenience columns on
`account.move.line`.

## Consequences

- **It carries a `search=`, and that is not optional.** A `store=False` field with no
  search implementation is not refused by `expression` — it logs the failure and
  substitutes an empty leaf, so a report filtered by a date range silently returns the
  whole ledger. ADR-0008 records the same fault costing the old OWL queues their
  dimension filters. `_search_paid_date` partitions the vouchers by which instrument
  answers for them and applies the operator to that instrument's date, so it is correct
  for negative operators too, and it reaches a cheque through `cheque_id` — the live one
  — rather than through `cheque_ids`, because a cancelled cheque's date answers for
  nothing.
- **The certificate now reads the field** instead of repeating the chain. The behaviour
  is unchanged: the old code fell through to `super()`, which dates the certificate from
  `payment.date`, and the field's last branch is `payment.date`. The certificate's
  `@api.depends` still names the effective date and the cheque date directly as well as
  `paid_date`, so the recompute cannot depend on a trigger travelling through an
  unstored computed field.
- **It cannot be sorted or grouped by in a list view**, which is why it is an optional,
  unsorted column on ใบสำคัญจ่าย. The reports that need it ordered sort in Python, over
  a set already narrowed to one period.
- **A voucher always has one.** The last branch is `date`, which is required, so
  `paid_date` is never empty on a real voucher — including one that has not been paid
  yet, where it reads as "the day it would be paid if it went out today". Callers that
  mean _paid_ filter on `finance_state = 'paid'`; the field answers "which day", not
  "whether".
- **Files that do not require an effective date fall through to the voucher date.**
  `is_required_effective_date` is False by default in the base module, and only some
  bank layouts turn it on, so a BAY or KBANK file left without one dates its vouchers by
  the day they were authorised. That is the honest answer — nothing in the system knows
  any better — and not a branch that fails.

## Rejected alternatives

- **Store it, filled by the three writers.** Three models would each have to remember to
  write it, on every path that touches a date, forever; the first one that forgot would
  produce a report that disagreed with the certificate for the same voucher. Plus a
  migration.
- **Stamp it when ยืนยันจ่ายสำเร็จ is pressed.** The press records when a person got
  round to confirming the outcome, which is routinely days after the bank moved the
  money and is not what any of these documents is dated from. It also does not exist for
  a transfer: the Hand-over there is closing the file, and the file already carries the
  date the bank acted on.
- **Put the field in the reports module.** The concept belongs to this context — its
  first user is the certificate, which predates any report — and defining it upstairs
  would let a reporting module dictate a term to the module that owns the vocabulary.
- **Leave the certificate's inline `or` chain alone and give the reports their own.**
  Cheapest today, and it is precisely the duplication this decision exists to stop: the
  day one of them gained a fourth instrument and the other did not, the ภ.ง.ด. filing
  and the payment report would disagree about the same money.
