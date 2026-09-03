# งวด is a user-entered input, and the clearing JE splits into one line pair per certificate per analytic distribution

## Context

The first cut of this module (ADR-0001) computed a display-only `period`
string from the date span of whatever certificates ended up on a remittance,
and posted one `Dr`/`Cr` line pair for the whole batch with no analytic
dimensions at all. A review of that cut, plus new requirements from the
module owner, changed both of those:

- The office files by calendar month regardless of which certificate dates
  happen to land in a batch, and needs to guarantee it never files the same
  ภ.ง.ด. form for the same month twice.
- The WHT payable and bank lines both need analytic dimensions so the
  clearing entry is attributable the same way every other KMITL journal
  entry is, and the two sides have to cancel out per dimension, not just in
  total.

## Decisions

### งวด is `period_month` + `period_year`, entered before certificates are loaded

The old `period` was computed from `cert_ids.date` — a display artifact, not
something you could act on before certificates existed. It's now
`period_month` (1–12) and `period_year` (a dynamic Buddhist-year selection
that always includes next year, so it never goes stale), both required,
both set by the accountant up front. `date_from`/`date_to` are computed from
them and used two ways: filtering candidate certificates
(`action_load_pending_certs`, the `cert_ids` widget's domain) and validating
them at `action_post` — a certificate whose date falls outside the declared
month blocks posting.

`action_create_remittance` (the shortcut from the WHT Certificate list) still
auto-fills the period from the selected certificates' dates, and now raises
if they span more than one month, instead of silently producing a
two-certificate, two-month period label as before.

### One ภ.ง.ด. form per month, enforced in Python

At most one `draft` or `posted` remittance may exist per
`(company, income_tax_form, period_month, period_year)`. A `cancelled` one
doesn't count — the office needs to be able to redo a botched month.
That "doesn't count" requirement is exactly why this is a
`@api.constrains` and not a `unique` SQL index: a unique index can't express
"unique among non-cancelled rows" without a partial index migration, and the
existing table already tolerates the pattern (see `budget_transfer`,
`sarabun`) of a Python constraint for state-conditional uniqueness.

### One JE, but one Dr/Cr line pair per certificate per analytic distribution

`analytic_distribution` is stored as `{analytic_account_id: percentage}` —
there is no way to "sum" two certificates' distributions into one line
without losing which certificate contributed which dimension. So the
remittance still posts exactly one `account.move` per remittance (nothing
about batching changed), but that move now has `2 × (certificates ×
distinct distributions on each certificate's source line)` lines instead of
2. Each pair debits the WHT payable account and credits the bank account for
the same amount and the same `analytic_distribution`, so every dimension
nets to zero within the one entry, the same way the whole entry always did
in total.

The distribution itself is read back from the certificate's *source* entry
(`cert.move_id`, the entry the WHT line was booked on) rather than
recomputed, because `finance_kmitl` already stamps the paying payment's
analytic distribution onto every line it creates, including the WHT
write-off line (`finance_kmitl/models/account_payment.py`). Reading it back
is strictly more accurate than re-deriving it, and it's the only place a
distribution is available at all for certificates booked from a plain
vendor-bill payment. A certificate whose source line carries no distribution
(and whose `payment_id`/`move_id` header distribution is also empty) blocks
`action_post` with the certificate's number in the error, rather than
silently posting an entry the budget/analytic reports can't attribute.

**The header-level `analytic_distribution` on `account.move` is never set.**
`accounting_kmitl`'s `_inverse_analytic_distribution`
(`accounting_kmitl/models/account_move.py`) copies whatever is on the
header down onto every line the moment it's written — exactly the
`disbursement_cash_revenue_handover` module hit before it worked around the
same inverse. Setting the header would collapse every per-certificate line
back onto one distribution, which is the bug this ADR exists to fix.

## Why not GL reconciliation for the per-certificate matching instead?

ADR-0001 already ruled out reconciling the WHT payable account for the
remittance-as-a-whole. Per-certificate analytic lines don't change that:
they make the *dimension* net to zero, not the *certificate's specific line*
reconcile against a specific remittance line. Reconciliation would still
require turning `reconcile=True` on for the payable account, with the same
migration cost ADR-0001 already declined to pay.
