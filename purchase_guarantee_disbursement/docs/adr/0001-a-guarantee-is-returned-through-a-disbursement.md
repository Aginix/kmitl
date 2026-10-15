# A guarantee is returned through a disbursement, not a payment voucher

A monetary guarantee's money has to go back when the contract closes. Two routes
existed in the repo already, and they disagree about what this is.

**Chosen: a `disbursement.request` raised from the guarantee**, carrying the
เงินหลักประกัน product, the Guarantee Kind's own deposit account, the
guarantee's dimensions and its supplier — and flagged **No Budget Consumed**
(disbursement ADR-0003).

## Considered options

- **An outbound `account.payment` with a `kmitl.payment.type` whose
  `override_account_id` is the deposit liability** — one data record, mirroring
  `advance_payment`'s รับคืนเงินยืม / จ่ายเงินยืม pair, and using machinery
  (`_compute_destination_account_id`, `_seek_for_lines`) written for exactly
  this. Genuinely the cheaper option, and rejected on what the act *is*: a loan
  return is the borrower handing money back, while this is KMITL paying money
  out of its own bank account to a supplier. The treasury office wants that to
  carry a ใบขอเบิก, the Finance Director's and the Rector delegate's approvals,
  and the signature block — none of which a voucher raised by hand has.
- **Reviving the upstream `bill_ids` route** (`l10n_th_gov_purchase_guarantee`
  builds a vendor bill from the guarantee). Rejected: KMITL hides those fields,
  and the module's own code marks the onchanges that drive them "ไม่ได้ใช้"
  (unused); it also skips the approval chain entirely.
- **A dedicated return document.** Rejected: it would reproduce the disbursement
  workflow for one case.

## Consequences

- **The budget layer needed a seam.** Nothing in `disbursement` could express
  "this consumes no budget" — see disbursement ADR-0003, which this decision
  forced.
- **"Returned" means paid, not approved.** `amount_returned` and `date_return`
  are computed from requests that reached `paid`/`cleared`, so this module
  depends on `disbursement_finance_kmitl` rather than plain `disbursement`.
  `date_return` stays editable: it was a hand-typed field upstream and
  guarantees returned before this module existed keep what was typed.
- **One return per guarantee**, mirroring one receipt per guarantee. Partial
  returns would need `amount_returned` to drive the next request's amount and
  both buttons to stop keying off a simple boolean.
- **The account comes from the Guarantee Kind, not the product.** The
  เงินหลักประกัน product is shared with the receipt side and carries the contract
  deposit account only as a fallback; both sides stamp
  `purchase.guarantee.method.account_id` over it, so a bid bond books to its own
  account on the way out as well as on the way in.
