# A receipt kind is a different document in the same model

KMITL receipts money it owes back — a supplier's security deposit — and wants an
official receipt for it, numbered and remitted like any other. That receipt
books a **deposit liability**, not revenue, and `kmitl.receipt` was written for
revenue: `kmitl.receipt.line.account_id` was domain-locked to
`account_type = 'income'` and labelled Income Account, and `CONTEXT.md` called
every line a revenue line.

**Chosen: one model, a `receipt_kind` discriminator, a register per kind.**
The account domain drops its type restriction, the field becomes *Account*, and
a kind decides the running number (`RC/` vs `RG/`), the printed title, and which
remittance a receipt may join.

## Considered options

- **A separate model for guarantee receipts.** Rejected: it would duplicate
  numbering, the remittance workflow, the six dimensions, Operating-Unit
  scoping, the printed form, the exception rules and both reports — all of which
  are identical, because the *act* is identical. Only what is credited differs.
- **Keep the `account.payment` route** (`purchase_guarantee_account_payment`).
  Rejected, and this ADR replaces it: it booked the same liability but produced
  no numbered document, appeared in no KMITL report, and had no counterpart on
  the way out. See that module's own deprecation note.
- **One shared register for every kind.** Rejected: a kind prints its own
  letterhead, so a receipt book has to explain every number in it. `RC/2569/0005`
  turning out to be a guarantee receipt is exactly the question a register
  exists to answer. `_receipt_sequence_vals()` is the seam; the base keeps `RC/`.
- **A boolean `is_guarantee` instead of a Selection.** Rejected: the base module
  must not know what the kinds are. A Selection takes `selection_add`, so an
  add-on names its own kind and the reports pick its label up off the field
  without this module changing.

## Consequences

- **`account_type = 'income'` no longer guards anything.** It was a client-side
  domain only — no constraint ever enforced it — so a liability account already
  posted correctly (Dr Cash / Cr liability); removing it only stops the UI from
  hiding the account. What a line may book is now decided by the product and by
  whatever stamps the line, not by the field.
- **A remittance carries a kind and rejects foreign receipts** — in the pending
  pull domain, in `_check_receipt_consistency`, and in the picker's own domain
  on the form. `action_create_report` refuses a mixed selection.
- **The Remit to Treasury leg is unchanged and still correct.** A guarantee
  arrives at the same counter and lands in the same bank account, so the
  Dr Deposit Bank / Cr Cash pair means for it exactly what ADR-0004 says it
  means for revenue. The *name* นำเงินส่งคลัง is a worse fit for money held on
  deposit; accepted rather than split the leg in two.
- **The printed title moved out of the template** into `_report_title()`, so a
  kind overrides a method instead of inheriting QWeb.
- **Existing receipts all become Revenue** by the column default, which is what
  they are.
