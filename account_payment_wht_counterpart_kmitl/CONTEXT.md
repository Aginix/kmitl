# CONTEXT — Account Payment: WHT Counterpart Leg

One line added to a payment voucher's journal entry, so that a voucher which withheld
tax says on its own what cleared the payable. Owns no document, no state and no setup —
install it and the entry gains a line, uninstall it and everything else carries on.

## Whose this is, and why it lives here

**The accounting office reads this, not the finance office.** The finance office works
on the voucher form and never opens its journal items — the booking side is theirs to
hand over, not to correct (`finance_kmitl` ADR-0002) — so the people this extra line is
_for_ are the ones who post the entry and read the books.

It depends on `finance_kmitl` all the same, because that is where the machine that
builds a payment's journal items lives: every line of a voucher's entry comes out of
`account.payment._prepare_move_line_default_vals`, on create and on every rebuild alike,
and core's "one and only one receivable/payable line" rule is checked through
`account.payment._seek_for_lines`. An `account.move` has no counterpart line to speak of
— a vendor bill has no withholding-tax write-off and a plain journal entry has no
counterpart at all — so there is no accounting-side seam to hang this on either.

That is why the module is **named after the model it extends, not after an office**.
`finance_kmitl_*` would have read as the finance office's, which it is not;
`accounting_kmitl_*` would have read as the accounting office's while depending on
`finance_kmitl`, pointing the name one way and the dependency the other. Naming it for
`account.payment` claims neither, and leaves the audience to be stated here, in words.
See [ADR-0001](./docs/adr/0001-every-credit-on-a-voucher-has-its-own-debit.md).

## Terms

- **ขาเจ้าหนี้คู่ภาษี / WHT counterpart leg**
  (`account.move.line.is_wht_counterpart_line`): one withholding-tax line's own mirror
  on the payable — same account as the real payable line, opposite sign, same amount —
  so the entry says the payable was cleared by the bank credit **and** by the tax
  withheld, without having to be read against the withholding-tax line to be understood.
  One leg per tax line, so a payee withheld on at two rates gets two of them. Named
  _counterpart_ after core's own vocabulary (`counterpart_lines`,
  `destination_account_id`) and _leg_ after `disbursement_cash_movement_kmitl`'s, and
  not tied to "payable" in the field name because the account it mirrors is not always
  one — an operation type may override it to something else entirely. See
  [ADR-0001](./docs/adr/0001-every-credit-on-a-voucher-has-its-own-debit.md). _Avoid_:
  "ล้างหนี้" / "clearing", which `disbursement_finance_kmitl` reserves for
  `paid → cleared` on a disbursement request; "write-off" on its own, since the leg
  cancels nothing out — it gives an existing credit its debit; and naming the field
  after "เจ้าหนี้", since the account it mirrors is whatever `destination_account_id`
  says.

## Rules

- **A leg is derived, never entered.** It is built from the withholding-tax line it
  mirrors every time the entry is built or rebuilt, and dropped and rebuilt rather than
  carried over — so a tax line that loses its `wht_tax_id` loses its leg with it, and
  the voucher falls back to the plain entry core would have built.
- **Nothing outside the payable side changes.** The amount the bank is told, the
  withholding-tax line, the certificate, the ภ.ง.ด. report and the paying account are
  all exactly what they were; only the debit facing them is split.
- **The inter-account cash-movement legs get no leg of their own.**
  (`disbursement_cash_movement_kmitl`): they are already Dr/Cr mirror pairs that net to
  zero, so they have no unpaired credit to give a debit to.
