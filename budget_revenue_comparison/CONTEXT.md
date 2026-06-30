# Budget Revenue Comparison

A configurable report that compares **budgeted revenue** (from the budget chart) against **actual revenue** (from the General Ledger), row by row, for a fiscal period. The budget chart and the Chart of Accounts are parallel charts with no stored link between them, so each report row carries two independent selectors — one over budget codes, one over GL accounts — and the report sets the two figures side by side.

## Language

**Budget Revenue (งบประมาณรายรับ)**:
The *Budget* column. The current revenue budget for the **whole fiscal year** = the net of posted `budget.move` lines on revenue-typed budget accounts (`budget.account.budget_type = "revenue"`) whose `move_type` is `appropriation` or `entry` (**excluding** `consume`) — initial appropriation plus supplementary plus transfers, i.e. the revenue-side analogue of the budget glossary's *Current Budget (a)*. Scoped by the fiscal-year FK (`account_fiscal_year_id`), never by a partial date range. "Posted" is the default of a screen toggle (`only_posted`); turning it off widens both columns to every non-cancelled move. A planned/target figure, not money received.
_Avoid_: revenue target, actual revenue (that is the other column), งบคงเหลือ

**Actual Revenue (รายรับจริง)**:
The *Actual* column. Revenue actually recognized in the General Ledger = posted `account.move.line` on income-type accounts (`account.account.account_type ∈ {income, income_other}`), dated within the report's date range — which defaults to the fiscal year but whose end (`date_to`) is an editable **as-of** date. It is recognized/earned revenue, **not** cash received (the GL carries no cash-basis tagging). The deliberate **full-year Budget vs to-date Actual** asymmetry is what makes the Percentage read as "% of the annual revenue target realized so far."
_Avoid_: cash received, collections, receipts (those imply cash basis, which is not tracked)

**Percentage (%)**:
Actual ÷ Budget × 100 — the share of the annual revenue target realized. Rendered to 2 decimals; shown as a dash (`–`) when Budget is zero (a percentage of nothing is meaningless). Header rows carry no percentage; total rows take it from their own Budget/Actual figures.
_Avoid_: variance, achievement ratio (keep the single label "Percentage")

**Indicator (ตัวชี้วัด)**:
A configured row of the report (`budget.revenue.report.line`), carrying a label, a `sequence`, a `row_type` (`header` / `line` / `total`), and — for `line`/`total` rows — two free-text formulas: a **budget formula** (`B[...]` over revenue budget codes) and an **actual formula** (`A[...]` over GL income accounts). The report is the flat, sequence-ordered list of these rows; there is no parent-child nesting and no auto-summing (a total row sums via its own formula, e.g. `B['4%']`).
_Avoid_: KPI (reserve for MIS Builder's `mis.report.kpi`, a different engine), line item
