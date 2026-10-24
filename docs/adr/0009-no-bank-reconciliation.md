# KMITL does not do bank reconciliation in the system

## Context

Several modules book banking-adjacent journal entries — cash routes in
`disbursement_cash_movement_kmitl`, the current/savings account sweep in
`withholding_tax_remittance_kmitl` — and each one has, independently, had to
decide what to do about the fact that the entries they post don't line up
with a real bank statement line by line. That decision keeps getting made
locally and explained in module-level `CONTEXT.md` files
(`finance_kmitl/CONTEXT.md:225-229`,
`disbursement_cash_movement_kmitl/CONTEXT.md:61-72`). It deserves a root-level
answer instead of N restatements of the same fact.

## Decision

KMITL does not reconcile bank accounts against bank statements in this
system, and has no plan to. Concretely:

- No bank statement import, no `account.bank.statement` reconciliation
  workflow, no bank feed integration.
- No use of core's outstanding-payments/outstanding-receipts accounts
  (`account.journal.payment_debit_account_id` /
  `payment_credit_account_id`) as a reconciliation mechanism.
- Every module that books a movement through a bank-labelled account is free
  to leave that account's balance not bank-accurate, as long as the amounts
  that matter (what was paid, to whom, for what dimension) are correct.

This is a permanent scope boundary, not a gap to close later. Where a module
needs to reconcile *something* against a bank-labelled account — e.g.
`withholding_tax_remittance_kmitl` matching a WHT payable debit against its
own source credit (ADR-0004 in that module) — that is GL reconciliation
between two entries this system itself posted, never a reconciliation against
an external bank statement.

## Why

- **Nothing here is told by a bank.** No result file is imported from any
  bank; every settlement outcome in KMITL's finance modules is a person's
  word (an accountant confirming a cheque cleared, a voucher being marked
  paid), and exceptions are chased down outside the system, on paper.
  Reconciling against a statement that never enters the system is not
  something the ORM can do — it would require building bank feed ingestion
  KMITL doesn't have and doesn't currently need.
- **The accepted trade-off is already priced in everywhere it applies.**
  Modules that route cash through intermediate accounts (savings → current,
  or the disbursement cash routes) already accept that those accounts carry
  balances a real reconciliation wouldn't expect, in exchange for every
  voucher/entry carrying the full 6D dimension set. That trade was made
  deliberately, per module, and this ADR just names it once at the root so
  future modules don't have to re-derive or re-justify it.
- **Outstanding accounts solve a problem KMITL doesn't have.** Core's
  outstanding-payment reconciliation exists to match a payment against the
  bank statement line that actually cleared it. KMITL's paying accounts are
  themselves the ledger of record for "did this get paid" — a cheque going
  outstanding is tracked as a line item on paper, not as an unreconciled
  journal entry waiting for a statement that will never arrive.

## Accepted consequences

- Bank-labelled accounts (savings, current, and the disbursement cash-route
  accounts) can carry non-zero, non-statement-matching balances indefinitely.
- A cheque that is outstanding (written but not yet cashed) is tracked
  outside the system, on paper — the system has no record of "still
  outstanding" separate from the voucher/entry that issued it.
- If KMITL ever needs statement-level bank reconciliation (e.g. for audit or
  a future digital-banking integration), it is new scope, not a gap in
  existing modules — this ADR should be revisited, not silently worked
  around inside one module.
