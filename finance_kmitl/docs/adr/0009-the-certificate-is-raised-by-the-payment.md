# The Hand-over raises the certificate, as a draft

Every **หนังสือรับรองการหักภาษี ณ ที่จ่าย** (50 ทวิ) is created by `_mark_paid()` — the
transition that says the money reached the payee — one per payee that withheld, in state
`draft`. The press left on the voucher (`action_create_wht_cert`) is for the ones that
transition could not write. Confirming a month's certificates `draft → done` is a
separate, monthly act on the certificate list.

## Why the payment raises it

KMITL **files ภ.ง.ด. itself**. It does not use a bank's withholding service — the SCB
export layout has fields for one (`WHT Form Type`, `WHT Tax Running No.`,
`WHT Attach No.`) and they go unused. The office gathers the month's withholding and
submits it.

That single fact changes what a certificate is. It is not a courtesy copy handed to a
payee; it is **the record the return is footed from**. `l10n_th_account_tax_report`'s
filing wizard reads `withholding.tax.cert.line` directly, filtered on `cert_id.date` and
`cert_id.state != 'draft'` — nothing else. So:

- **no certificate ⇒ a payee missing from the return**, and
- **a certificate still in draft ⇒ the same**.

A document with that consequence cannot be left to somebody remembering to press a
button. And the volume makes forgetting the normal case rather than the exception:
closing one e-payment file pays every payee it carried, so a utilities run is twenty
payees in one press. Twenty forms and twenty presses is precisely what
[ADR-0006](./0006-a-cheque-is-the-e-payment-file-of-one-voucher.md) took out of this
phase, and it should not come back on the certificate side.

`_mark_paid()` is also the _right_ moment, not merely a convenient one. It is the single
shared hook for "the money reached the payee" — closing an e-payment file
(`bank_payment_export`), **มอบเช็ค** (`cheque_register`), ยืนยันจ่ายสำเร็จ for cash, and
a disbursement request confirming all of its payees at once all pass through it. It is
therefore the moment the law's date is settled, and that date is what the certificate is
dated from and what decides which month's ภ.ง.ด. it belongs to. Raising it anywhere else
would mean deciding that date twice.

## Why a draft, and not finished

Because the review that matters is **monthly, not per voucher**. The officer's real task
is a return: a month × one ภ.ง.ด. form, footed and checked as a whole. At the counter,
handing a payee their paper, there is nothing useful to review — the figures were frozen
when the voucher was confirmed for the bank.

So the filing run is the review step, and `done` means "in this month's return", not
"printed" (the paper went out at the Hand-over). The certificate list carries the
filters and the totals that pass needs, and one press confirms the month.

The cost is accepted: **the OCA filing wizard cannot preview a month before it is
confirmed**, since its domain excludes drafts. The preview is the certificate list
instead, which is where the drafts are.

## Why it is built from the entry

`_prepare_wht_cert_vals` reads `move_id.line_ids.filtered("wht_tax_id")`, not the
voucher's own `wht_tax_id` / `wht_amount_base`. Both kinds of voucher have that line — a
hand-filled one puts it there from its own rate, a voucher billed through a request gets
it from the bill — and most of KMITL's withholding is the second kind. A builder that
read only the voucher's own fields would leave the majority of the return unwritten,
which is the same failure as forgetting to press.

`wht_cert_income_type` follows the same shape: computed from the voucher's own rate when
it has one, and from the entry's line otherwise, overridable either way. This is also
what lets the voucher **show** how much was withheld and under which type of income
before the accounting office posts anything — the native `wht_move_ids` table cannot,
because those records only exist after posting.

## Consequences

- **A certificate that cannot be written does not stop the Hand-over.** The money
  reached the payee; no document may contradict that. Each voucher gets its own
  savepoint and its own note in the chatter, the same pattern
  `disbursement_finance_kmitl._try_create_payments` uses for raising vouchers.
- **`_check_wht_complete` now guards the certificate as well as the books**, and it runs
  at ยืนยันพร้อมส่งธนาคาร — so a rate carrying no default type of income is refused to
  the person who can still fix it, rather than becoming a chatter note nobody reads.
- **The certificate menu is a filing screen, not a folder.** It opens on what is still
  draft, grouped by return.
- **`finance_kmitl_assignment` already overrides `_mark_paid()`.** Anything added here
  has to keep calling `super()` and stay indifferent to ordering.
- **Known gap: a cheque that dies after it was handed over.** `_unmark_paid` does not
  touch the certificate, so the paper in the payee's hand and the record can disagree,
  and a cross-month replacement moves the withholding between returns silently. ADR-0007
  already states the domain rule — the office files an amendment — and the certificate's
  date does follow the replacement cheque on its own. Cancelling and substituting the
  certificate (the model has `ref_wht_cert_id` and an `action_done` that cancels its
  predecessor) is deliberately left out of this change.

## Rejected alternatives

- **A press per voucher** (what the first cut of this feature shipped). Twenty forms for
  one e-payment file, and forgetting one means filing short.
- **A press on a list selection.** Better ergonomics, same failure: nothing makes it
  happen.
- **Raise them `done`.** Lets the filing wizard preview a month immediately, but puts
  the only review at the counter, where there is nothing to review and no time to do it.
- **Raise them at ยืนยันพร้อมส่งธนาคาร instead.** The figures are frozen there, so it
  would work — but the date the certificate needs is not settled until the money leaves,
  and a voucher confirmed and then never paid would file a withholding that never
  happened.
