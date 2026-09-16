# The trial balance computes its own balances instead of reusing the OCA engine

`report.accounting_kmitl_reports.trial_balance_kmitl` aggregates
`account.move.line` itself — an opening pass for balance-sheet accounts, an
opening pass for profit & loss accounts since the start of the fiscal year, and
a pass over the period — rather than inheriting
`report.account_financial_report.trial_balance` and calling its private
`_get_data`. This supersedes the "reuses the OCA trial-balance compute" part of
[ADR 0001](0001-trial-balance-owl-client-action.md); the client action itself is
unchanged. The General Ledger and the Aged Partner Balance still use their OCA
engines.

## Considered Options

- **Own the compute (chosen).** KMITL switches off every feature the OCA engine
  layers on top of those three aggregations — partner details, foreign
  currency, account hierarchy, analytic grouping, unaffected earnings — so the
  inherited code we actually executed was about a hundred lines we can write
  and read directly. Owning it also drops the context-passing indirection that
  injected the dimension leaves through four domain-hook overrides.
- **Keep inheriting, pin the OCA repo (rejected as the whole answer).** `_get_data`
  is private and has no stability guarantee: OCA inserted a mandatory
  `hide_account_at_end_0` argument mid-list in 16.0.1.18.0, which broke the
  report on every image built after that. Pinning the OCA clone is still worth
  doing for the General Ledger and Aged Partner Balance, but for the trial
  balance it would only defer the same breakage to the next upgrade.
- **Filter the keyword arguments by the installed signature (rejected).** Cheap
  and it unblocks both releases, but it keeps the coupling and turns a future
  incompatible change into a silent behaviour difference instead of an error.
- **Drop OCA from the General Ledger and Aged Partner Balance too (rejected).**
  Those engines carry real accounting logic we do not otherwise have — running
  balances, reconciliation as of a date, residual ageing — and OCA still fixes
  bugs in the code paths we use. The trial balance had no such fixes in two
  years of history.

## Consequences

- `account_financial_report` stays in `depends`, for the other two reports.
- The dimension leaves are appended to each domain where it is built, so there
  is no longer a `kmitl_dim_leaves` context key.
- Equivalence with the OCA engine was verified account-by-account on UAT data
  across full-year, mid-fiscal-year and next-fiscal-year windows, with and
  without draft entries, account filters, journal filters and "hide accounts
  at 0".
- `trial.balance.report.wizard.kmitl` no longer inherits the OCA wizard; it
  declares the three fields it carries for the PDF/XLSX/CSV actions.
