# Cash Debit stays one lump per line; only the revenue Credit fans out

An allocated receipt line's journal entry keeps `receipt_kmitl`'s existing
**one Dr Cash leg per line**, sized at `line.amount` and carrying the
receipt header's own dimensions (`_prepare_debit_line_vals`, unchanged). Only
the **Cr revenue side** fans out into `N` legs, one per allocation bucket,
each on its own account with its own merged dimensions. This diverges from
`receipt_kmitl` ADR-0004, which pairs every Dr Cash leg 1:1 with its Cr
revenue leg on identical dimensions.

## Considered options

- **Split Cash 1:1 per bucket too** (`N` Dr Cash legs mirroring the `N` Cr
  revenue legs, each on the bucket's own dimensions). Rejected: Cash is an
  asset account — no repo report (`budget_revenue_comparison`,
  `accounting_kmitl_reports`, the receipt summary report) reads its analytic
  dimensions; splitting it would only add noise to the journal entry with no
  reader to benefit. It would also multiply the number of `account.move.line`
  rows a receipt with several fee products produces, for no analytic payoff.
- **Chosen: keep Cash lumped**, split only the accounts that actually carry
  the department-level detail Finance is asking for (the revenue accounts).

## Consequences

- ADR-0004's net-zero-per-pair property — every Dr Cash / Cr revenue pair
  nets to zero under stock Odoo's analytic balance reporting, because the
  pair shared one `analytic_distribution` — no longer holds for an allocated
  line. The lumped Cash leg carries the header's dimensions while its `N`
  revenue legs may carry different (bucket-pinned) dimensions, so the
  per-dimension analytic balance across the whole entry is not zero for an
  allocated line. Accepted for the same reason ADR-0004 accepted it in the
  first place: this repo's analytic reports read `account.move.line`
  directly (filtered by account type/code and `analytic_distribution`), not
  the stock analytic balance — see `receipt_kmitl/CONTEXT.md` → Known
  limitations.
- `kmitl.receipt._create_move()` itself needed no change beyond the
  `_get_revenue_splits` hook — the loop already builds one Dr per line
  followed by however many legs the hook returns.
