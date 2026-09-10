# Treasury remittance leg lives in the receipt's own entry, keyed by payment method

Reproducing the legacy voucher requires two changes to `kmitl.receipt._create_move()`:
the Cash Account leg splits 1:1 against each revenue line instead of one lump
sum, and a Dr Deposit Bank Account / Cr Cash Account pair remits the
receipt's full total to the treasury (นำเงินส่งคลัง). Both live in the
receipt's single journal entry.

## Considered options

- **A separate journal entry, linked by a field** — the same shape as
  `disbursement_cash_revenue_handover`'s handover entry. Rejected: that entry
  is deliberately decoupled because a *different* team (accounting) reviews
  and posts it on its own schedule, after the bill. The treasury-remittance
  leg has no such second reviewer — a receipt is only posted once treasury
  has already approved and posted its remittance — so a second document
  would only add one more thing to keep in sync, for no one to review
  differently. Same reasoning as `disbursement_cash_movement_kmitl` ADR-0001.
- **Deposit account keyed by issuing department.** Rejected: which deposit
  account a receipt remits into depends on the payment channel (cash till vs.
  bank transfer both administered centrally), not the department, and a
  department may use more than one channel. Keying by `kmitl.payment.method`
  matches how the Cash Account is already keyed, and every receipt already
  picks its payment method.
- **Deposit account selected on the receipt header.** Rejected: it is not a
  fact about the transaction (like the amount or customer) but about how that
  payment channel is banked — a setup concern, so it belongs on
  configuration (payment method), not repeated on every receipt.
- **Chosen: the leg lives inside `kmitl.receipt`'s own move**, built by
  `_prepare_deposit_line_vals()`, sourced from the new
  `kmitl.payment.method.deposit_account_id`.

## Consequences

- Every revenue line's Dr (Cash Account) and Cr (revenue) `account.move.line`
  now carry the same `analytic_distribution`, so that pair's net analytic
  balance is zero under stock Odoo's analytic reporting — the revenue never
  shows up there. Accepted: this repo's own analytic reports
  (`budget_revenue_comparison`, `accounting_kmitl_reports`) read
  `account.move.line` directly, filtered by account type/code plus the
  `analytic_distribution` domain, not the analytic balance, so they are
  unaffected. See `CONTEXT.md` → Known limitations.
- `deposit_account_id` is `required=True` on the payment method, but that
  cannot retroactively enforce `NOT NULL` on rows that already exist when
  this change is deployed. `_create_move()` therefore still guards
  explicitly and raises a `UserError` if either account is missing, exactly
  as it already did for the Cash Account.
- `kmitl.payment.method.account_id` keeps its name but is relabelled from
  Debit Account to Cash Account: it is now debited per revenue line rather
  than once for the receipt total, and "debit account" no longer
  distinguishes it from the new Deposit Bank Account.
- A `@api.constrains` rejects a payment method whose Cash Account and Deposit
  Bank Account are the same account — otherwise the remittance pair would
  debit and credit the same account for the same amount and silently vanish.
