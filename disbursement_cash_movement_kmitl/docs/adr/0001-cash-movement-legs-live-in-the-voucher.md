# Cash-movement legs live in the voucher's own journal entry, not a separate one

Accounting reads a cheque's whole trail — source account down to the paying
account that settled one payee — as part of that payee's ใบสำคัญจ่าย, not as an
event of its own. Booking the legs inside the voucher's own `account.move`
keeps that reading literal, and keeps reverse/cancel/reset-to-draft working on
the voucher without a second lifecycle to keep in step.

## Considered options

- **A separate journal entry per voucher, linked by a field**, the same shape
  as `disbursement_cash_revenue_handover`'s handover entry. Rejected: that
  entry is deliberately decoupled because a *different* team (accounting)
  reviews and posts it on its own schedule, after the bill. A cash-movement
  leg has no such second reviewer — it is exactly as true as the voucher it
  rides on — so a second document would only add one more thing to keep in
  sync, for no one to review differently.
- **Legs inside the voucher's move** (chosen). Costs an override of
  `_seek_for_lines` / `_synchronize_to_moves` / `_prepare_move_line_default_vals`
  — the same core synchronisation `finance_kmitl` already overrides to protect
  the withholding-tax write-off through a rebuild — plus every leg carrying the
  payee's own `partner_id`, because core requires every line of a payment's
  move to share one partner even though a cash-movement leg pays nobody.

## Consequences

- **A voucher's cash-movement legs and its withholding tax share one rebuild
  path**, and both have to survive it: core's `_synchronize_to_moves` folds
  every non-liquidity, non-counterpart line into one merged dict. Left alone,
  that merge would hand back a single bogus zero-amount line on any voucher
  that carries a route but no withholding tax — legs are Dr/Cr mirror pairs
  that always net to zero. Guarded the same way withholding tax already is.
- **A leg's `partner_id` is the payee, not the bank the money passed through.**
  Cosmetically odd on a line that settles nobody, but required: core rejects a
  payment move whose lines do not all share one partner.
- **No route lookup, no legs — silently.** A route is discovered per payment,
  not declared per voucher, so a paying account or source of funds nobody has
  configured yet costs a warning (Known limitations), never a blocked voucher.
- **Re-derivation has to be tried again right before posting.**
  `analytic_distribution` — what a route is looked up from — is not one of
  `account.payment`'s trigger fields for `_synchronize_to_moves`, so a voucher
  created before its dimensions were known does not otherwise get a second
  chance once they arrive. `account.move._post()` gives it one, scoped to
  vouchers that resolve to a route with hops but currently carry no leg.
