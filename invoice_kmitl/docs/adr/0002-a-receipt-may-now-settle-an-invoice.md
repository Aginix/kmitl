# A receipt may now settle an invoice

`finance_kmitl_reports` recorded, as a rule, that *an ใบเสร็จรับเงิน never settles an
ใบตั้งหนี้* — a receipt's entry is Dr Cash Account / Cr revenue per line plus a Dr Deposit
Bank Account / Cr Cash Account remittance leg, and not one of the three legs is a
receivable — and that money settling an ใบตั้งหนี้ was outside every report "until that
settlement has a workflow of its own". This module is that workflow, so the rule is
reversed, and was rewritten in the same commit.

A receipt raised from an invoice (`kmitl.receipt.invoice_id`, a **ใบเสร็จตัดหนี้**) keeps
its whole route — draft, remittance, approval, posting, the deposit leg — and differs in
exactly one leg: the per-line credit goes to the customer's **receivable** account instead
of the line's revenue account.

## Considered options

- **A separate settlement document.** Rejected: the receipt already is the document the
  department issues and the treasury office remits, and a second document for the same
  money would be one more thing to keep in step. One route, one leg changed.
- **Debit cash, credit revenue as always, and reconcile by hand.** Rejected: it books the
  revenue a second time and leaves the invoice open — the very failure the old rule was
  written to prevent.
- **Chosen: the credit leg is swapped through the existing hook.**
  `kmitl.receipt._prepare_move_line_vals` is overridden to set `account_id` to the
  invoice's receivable account. The deposit pair (`_prepare_deposit_line_vals`) is not
  touched: per line Dr Cash / Cr Receivable, then once Dr Deposit / Cr Cash, nets to
  **Dr Deposit Bank Account / Cr Receivable** — the settlement and the remittance to the
  treasury in one entry.

## Consequences

- **The receivable account is read back from the invoice's own entry, never derived from
  the partner again.** `partner_type_kmitl_accounting` re-stamps
  `property_account_receivable_id` whenever a partner's type changes and can do it for a
  whole set at once; if the account moved in between, `reconcile()` would refuse with
  "Entries are not from the same account". The lookup is `sudo()`, as the entry may sit in
  an operating unit the reader cannot see.
- **The override calls `super()` and edits the values; it never returns early.**
  `receipt_kmitl_operating_unit` overrides the same hook to stamp `operating_unit_id`, and
  which of the two loads last is not pinned. An early return would drop the operating unit
  off the receivable leg whenever this module loaded second.
- **One debit against N credits.** A receipt credits the receivable once per receipt line
  (`_create_move` splits per line), while the invoice's entry has a single receivable
  debit. `reconcile()` accepts N against one; nothing may assume 1:1.
- **Full payment only, enforced.** A constraint on `kmitl.receipt` requires the receipt's
  total to equal the invoice's. Without it a receipt edited down would leave the invoice
  half settled in the books while the department sees it paid. The "Income Account" column
  on such a receipt is kept, as the receipt line requires one, and says where the revenue
  came from; the form carries a note saying it is not the account booked to.
- **The payer cannot be swapped.** The walk-in switch and the partner are read-only on a
  receipt that settles an invoice: the switch would replace the customer with the walk-in
  partner.
- **The same money now shows in two reports.** รายงานการรับเงิน counts the receipt once it
  reaches the treasury; รายงานการตั้งลูกหนี้ counted the invoice when it was raised. They
  are still different documents and still never mix inside one report, but a reader adding
  the two reports will count the baht twice.
- **Revenue is recognised when the ใบตั้งหนี้ posts, not when the money arrives**, for
  anything invoiced. See `CONTEXT.md` → Known limitations.
