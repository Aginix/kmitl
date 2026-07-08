# Trial balance renders as an OWL client action, not a native list/pivot

The Trial Balance opens straight from the menu as an OWL `ir.actions.client` whose filter bar and Debit/Credit/Balance table are custom OWL, fed by a backend method that reuses the OCA trial-balance compute. We did **not** express it as a native list/pivot view, and we deliberately did **not** add stored convenience dimension fields to `account.move.line`.

## Considered Options

- **OWL client action reusing the OCA compute (chosen).** A native list/pivot cannot express opening/ending balances, which are cumulative sums *before* / *through* a user-chosen date — a search filter only narrows rows, it cannot re-parametrise a cumulative aggregate (the reason Odoo Enterprise/OCA build bespoke report engines; Enterprise `account.report` is absent from this source tree). The client action mirrors the existing `budget` overview/dashboard pattern.
- **Native list/pivot on a SQL-view model (rejected).** Cannot carry opening/ending balances under an arbitrary date filter.
- **Stored `*_analytic_id` convenience fields on `account.move.line` + native search view (rejected).** Would give fully-native multi-select facets for free, but at the cost of four stored computed fields + indexes + a recompute migration on a million-row table — heavy and hard to reverse. Dimension filtering is done instead via `analytic_distribution` JSONB leaves, leaving the ledger schema untouched.

## Consequences

- The on-screen report and the PDF share one compute (`get_trial_balance_data`), so the printout always matches the screen.
- Filtering by a dimension narrows the lines feeding each balance, so dimension-filtered Debit and Credit totals need not net to zero (analytic distribution is not present on every line of every move).
