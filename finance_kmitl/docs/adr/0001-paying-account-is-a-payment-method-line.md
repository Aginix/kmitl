# A paying account is one of Odoo's payment method lines

A paying account (หัวจ่าย) answers "out of which account does the money leave, by
which means, under which voucher, booked against which GL account". Odoo already
has a record that answers exactly that: `account.payment.method.line`. It hangs
off a journal, names a payment method, and carries `payment_account_id` — the
money side of the entry, which core computes and validates without any help. So
หัวจ่าย gets no model of its own; `account_kmitl` only adds what the bank needs
and Odoo does not keep there — the institute's own bank account, which the
e-payment file sends as its sending account and the cheque register uses as the
cheque book.

## Consequences

- **The journal stays the voucher type (ใบสำคัญ).** Its sequence *is* the voucher
  number, so it cannot double as a bank account. Several banks therefore appear
  as several method lines on the same journal, and choosing a paying account
  determines the journal rather than the other way round — the inverse of Odoo's
  own direction.
- **The payment method stops being named anywhere else.** A paying account names
  its method, so nothing else may: the flag on `kmitl.payment.type` that said a
  payment was settled by cheque is gone, and with it the hard-coded xmlid mapping
  that turned it into one of Odoo's methods at payment-creation time. Whether a
  payment travels in an e-payment file is read off the paying account's method
  code (`account.payment.needs_bank_export`).
- **`kmitl.payment.type` is now purely the counterpart side** — what the money
  *is* (a guarantee deposit, an advance), through its override account. It keeps
  `journal_id` as the default voucher for payments that have no paying account to
  derive one from, which is how `advance_payment` and `purchase_guarantee` still
  work.
- **The GL account belongs to the bank account, not to the pairing.** A transfer
  and a cheque out of the same account hit the same GL — KMITL keeps no
  "เช็คจ่าย" holding account; a cheque's not-yet-presented state is the cheque
  register's business. Odoo stores that account per method line, so a constraint
  requires every paying account on one bank account to agree, and an onchange
  proposes the sibling's value so it is only ever entered once.
- **Cash qualifies without a bank account at all.** What makes a line a paying
  account is that it knows the money's origin, not that it has a bank.
- **A change of paying account repoints the money line surgically**
  (`account.payment.write`). The method line stays out of the move-synchronisation
  triggers, because rebuilding the move recreates the withholding-tax write-off
  lines from name/account/amount and loses `wht_tax_id`. The money line is
  captured *before* the write: afterwards it carries the old account and no
  longer counts as a liquidity line, so looking it up then finds nothing.

## Rejected alternatives

- **A `kmitl.paying.account` model pairing a bank account with a method**, and
  before that a flag plus a GL account on `res.partner.bank`. Both needed
  `_compute_outstanding_account_id` and `_get_valid_liquidity_accounts`
  overridden so core would accept an account it had not chosen — machinery whose
  only purpose was to re-teach core something it already knew.
- **Making the journal the bank account**, which is Odoo's own convention. It
  cannot be done here: a KMITL journal code *is* the voucher type and its
  sequence *is* the voucher number.
