# The withholding-tax certificate belongs to the voucher, not to the entry

A **หนังสือรับรองการหักภาษี ณ ที่จ่าย** (50 ทวิ) raised by the finance office is created
with `payment_id` set and **`move_id` left empty**, from a button on the voucher
(`account.payment.action_create_wht_cert`) that opens as soon as the voucher is
confirmed for the bank.

Upstream models the certificate the other way round. `l10n_th_account_tax` builds it in
`account.move.create_wht_cert()` out of the `account.withholding.move` rows, and those
rows are only created in `account.move._post()`. It also, in that same `_post`, does
this:

```python
# When post, do remove the existing certs
self.mapped("wht_cert_ids").unlink()
```

Both halves of that are wrong for KMITL, for the same reason: **here the entry is posted
long after the payee has been paid.** The finance office confirms a voucher, sends it to
the bank or writes a cheque, and the money leaves; the entry stays `draft` for the whole
of that stretch and is posted by the accounting office after the Hand-over
(`disbursement_finance_kmitl` ADR-0005). So a certificate that can only exist once the
entry is posted cannot be handed to the payee with their money — and one that _is_
handed to them early would be deleted the moment the accounting office got round to
booking the voucher.

Binding it to the payment answers both at once. `move.wht_cert_ids` reaches certificates
through `move_id`, so a certificate with no `move_id` is invisible to that `unlink()`
and survives posting without anything having to intercept it. And
`account.payment.wht_cert_ids` already exists upstream, along with the smart button and
the count that read it, so the voucher shows its certificate with no new plumbing.

The certificate is also correct on the day it matters, because the date is not the
entry's: `withholding_tax_cert._compute_wht_cert_data` dates it from the e-payment
file's effective date or the cheque's date — the day the law treats the income as paid.

## Consequences

- **The certificate is issued from `confirmed`, not from `paid` or `posted`.** That is
  the first moment what it states can no longer change: the money side is frozen and the
  voucher has its ใบสำคัญจ่าย number, which is also the certificate's number. For a
  cheque payee it has to be available then, because the paper goes out in the same hand.
- **`account.move._compute_wht_cert_status` is widened to see the payment's
  certificates.** Otherwise the entry still reads `none` after posting and the stock
  banner invites an accountant to issue a second certificate for a payee who already
  holds one.
- **`account.move.create_wht_cert` refuses when the payment already has one.** The
  banner is not the only door to it, so the guard sits on the method.
- **`wht_cert_income_type` stays editable after the voucher is confirmed**, which is the
  one exception to ADR-0002's "the form closes whole". It moves no entry and the bank
  never saw it, and the certificate is issued _after_ confirmation — closing it with the
  rest of the form would leave it correctable nowhere. It closes when the certificate is
  issued.
- **`account.withholding.move` is still created at posting, unchanged.** The certificate
  and the ภ.ง.ด. substrate are two different records with two different owners, and only
  the certificate had to move. `_prepare_withholding_move` is overridden so the
  substrate inherits the type of income the finance office chose rather than the tax's
  default.

## Rejected alternatives

- **Guard `withholding.tax.cert.unlink()`.** Refusing the delete would break posting;
  silently dropping records from an `unlink()` is worse than not being in the recordset
  in the first place.
- **Create the `account.withholding.move` rows early so upstream's `create_wht_cert()`
  works.** `_post` clears and rebuilds them (`[Command.clear()] + …`), so anything
  written early is thrown away — and the certificate would still be unlinked.
- **Set `move_id` as well, and re-link after posting.** Two writes to keep in step, and
  every `button_draft` would cancel the payee's certificate again.
