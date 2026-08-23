# The payee's bank account freezes when the file leaves, not when the voucher is confirmed

The money side of a voucher (ฝั่งเงิน) freezes the moment the finance office confirms it
for the bank, because from then on the record has to keep saying what the bank was told
to do. The payee's bank account is money side — and it is the one field of that set that
stays correctable afterwards, until the e-payment file carrying it has been exported.

The reason the rest freeze at confirmation is not that the bank has been told anything.
It is that confirmation issues the ใบสำคัญจ่าย number, and Odoo binds that number to the
voucher's date, which is also the accounting period. Amount, payee, currency, journal,
paying account and date all either _are_ those facts or move the entry that carries
them. The payee's bank account moves none of them: it appears in no debit and no credit,
and changing it re-derives nothing. It is purely the instruction handed to the bank.

And the bank is handed nothing at confirmation. A voucher can sit confirmed for days
before it enters a file, and a file can sit in draft after that. Through both, a wrong
account number is a mistake nobody has acted on. Refusing the correction there does not
protect a record of what was instructed — there is no instruction yet — it only pushes
the fix outside the system, which is the one place the finance office's own rules say
outcomes should not have to live.

So the field has a guard of its own (`account.payment._check_payee_account_open`), keyed
on whether the instruction has left rather than on `finance_state`:

- a voucher that travels in an e-payment file is open until `export_status` is
  `exported`;
- a voucher settled by cheque or cash names no account the bank acts on, so it closes
  with the rest of the voucher, at **ยืนยันจ่ายสำเร็จ**.

## Consequences

- **`partner_bank_id` leaves `MONEY_FIELDS`.** It is still money side in the glossary;
  what changed is that the set is no longer a single freeze point. The constant is kept
  as `PAYEE_ACCOUNT_FIELD` beside it so the split is visible where the guard is written
  rather than only here.
- **The row in the file stops holding a copy.** `bank.payment.export.line` used to
  snapshot the account when the row was created and let it be edited independently, and
  it is the row — not the voucher — that is written into the bank file
  (`_get_receiver_information`). Two editable copies of one fact meant a file could
  instruct a bank to credit an account the voucher did not name, with nothing anywhere
  saying so. The row now follows the voucher (`_compute_payment_default` depends on it)
  and writes back to it (`_inverse_payment_partner_bank_id`), so correcting either
  corrects both and they cannot disagree.
- **The correction is made on the row, because the voucher form is shut.**
  [ADR-0002](./0002-the-payment-voucher-form-belongs-to-the-finance-office.md) closes
  the whole `account.payment` form at confirmation, so this field has no editable node
  there even though the guard would allow the write. That is the right place for it to
  happen anyway: the officer meets a wrong account number while assembling the file, not
  while re-reading a voucher. The guard stays keyed on the instruction rather than on
  the form, so any other path — a bridge, a wizard, a correction script — is judged by
  the same rule and does not have to know which nodes a view happens to offer.
- **The row stays editable only while the file is draft**, which is narrower than the
  guard allows. That is the base module's `states` on the column and it is left alone:
  an officer who spots a wrong account on a confirmed file takes the file back to draft,
  which is tracked, rather than editing underneath a file that is a press away from
  going out.
- **A file already at the bank is corrected by rejecting it**, not by editing a row. The
  rejection releases every voucher in it, and the corrected ones go into the next file.

## Rejected alternatives

- **Keeping the freeze at confirmation and correcting nothing.** The account would have
  to be fixed by rejecting a file that had not gone anywhere, or by cancelling and
  re-raising the voucher — which would issue a second ใบสำคัญจ่าย number for one
  payment.
- **Letting the row diverge and writing the row into the file.** This is what the base
  module does. It is the cheapest to build and the only one where the voucher can end up
  a false record of what the bank was instructed to do.
- **Freezing at `to_export` (the voucher is in some file) rather than at `exported`.**
  Simpler to read, but a draft file has been uploaded to nobody, and assembling a file
  is exactly when an officer checks the accounts and finds the bad one.
