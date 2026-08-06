# A paying account is one of Odoo's payment method lines

A paying account (หัวจ่าย) answers "out of which account does the money leave, by
which means, under which voucher, booked against which GL account". Odoo already
has a record that answers exactly that: `account.payment.method.line`. It hangs
off a journal, names a payment method, and carries `payment_account_id` — the
money side of the entry, which core computes and validates without any help. We
had built two models over the top of it instead: a flag and a GL account on
`res.partner.bank`, then a `kmitl.paying.account` pairing model, each needing
`_compute_outstanding_account_id` and `_get_valid_liquidity_accounts` overridden
so that core would accept an account it had not chosen. All of that is gone; the
method line *is* the paying account, and this module only adds what the bank
needs and Odoo does not keep there — the institute's own bank account and the
cheque print calibration.

What makes a method line a paying account is that it names its GL account. The
lines Odoo seeds on every bank journal by default do not, so they are filtered
out of every หัวจ่าย field by that same test — which is also what lets cash be a
paying account without inventing a bank account for it.

## Consequences

- **The journal stays the voucher type (ใบสำคัญ).** Its sequence *is* the voucher
  number, so it cannot become a bank account. Several banks therefore appear as
  several method lines on the same journal, and choosing a paying account
  determines the journal rather than the other way round — the inverse of Odoo's
  own direction, done in an onchange, with the journal left hidden on the form.
- **The payment method stops being named anywhere else.** It was a `Selection` on
  the disbursement payment line, a `default_method` on the payment subject, and a
  pair of `is_cheque` / `is_cash` flags on `kmitl.payment.type` that had to be
  mapped onto Odoo's methods by hard-coded xmlid at payment-creation time. All
  gone: the paying account names its method, and the subject points at an
  `account.payment.method` only to say which of a bank's paying accounts
  auto-matching means.
- **`kmitl.payment.type` is now purely the counterpart side** — what the money
  *is* (a guarantee deposit, an advance), through its override account. The two
  records that described the money side from the wrong side of the entry
  (จ่ายเช็ค, จ่ายเงินสด) are deleted. It keeps `journal_id` as the default voucher
  for payments that have no paying account to derive one from, which is how
  `advance_payment` and `purchase_guarantee` still work.
- **The GL account belongs to the bank account, not to the pairing.** A transfer
  and a cheque out of the same account hit the same GL — KMITL keeps no
  "เช็คจ่าย" holding account; a cheque's not-yet-presented state is the cheque
  register's business. Odoo stores that account per method line, so a constraint
  requires every paying account on one bank account to agree, and an onchange
  proposes the sibling's value so it is only ever entered once.
- **A change of paying account still repoints the money line surgically.** The
  method line stays out of the move-synchronisation triggers, because rebuilding
  the move recreates the withholding-tax write-off lines from name/account/amount
  and loses `wht_tax_id`.
