# Budget-vs-actual-revenue report is a bespoke config model + OWL, not MIS Builder

The report sets **budgeted revenue** (`budget.move`, revenue codes) beside **actual revenue** (`account.move.line`, income types) on each configured row. We build it as our own `budget.revenue.report.line` config model with a custom compute and an OWL screen, **not** on OCA MIS Builder — even though MIS Builder is already in the deployment and natively offers comparison and percentage columns.

The blocker is structural: the budget chart (`budget.account.code`) and the Chart of Accounts (`account.account.code`) are parallel charts with no stored link, so each row needs **two different formulas over two different account-code namespaces**. A MIS Builder KPI exposes exactly **one** expression, evaluated identically for every column regardless of that column's `source` — it physically cannot run a budget-code formula in one column and a CoA formula in the next. Making MIS Builder do it would require either re-keying all budget data into the CoA namespace or writing a custom `ExpressionEvaluator` plus a new period `source` — significant, fragile machinery for a single report.

## Considered options

- **MIS Builder with `mis_budget` / `mis_budget_by_account` sources** — its budget columns map onto the *same* KPI expression as the actuals column, so they only work when budget data lives in the account.account namespace. Ours doesn't, and we are not going to mirror the budget chart into the CoA.
- **MIS Builder with a custom `ExpressionEvaluator` + new `source`** — the only way to keep two genuinely different formulas on one KPI, but it means subclassing core MIS internals and shipping a new column source. Too much surface area, and it couples a budget report to the MIS framework's release cycle.

## Consequences

- We own a small formula engine (see ADR-0002) and the OWL/XLSX surfaces, mirroring the bespoke pattern already used by Trial Balance / Cash Flow in `accounting_kmitl_reports` — but **without** depending on that module (dependencies are `budget` + `account` + `report_xlsx`, copying the ~80-line dimension-filter mixin).
- If a future report needs budget-vs-actual on the *expense* side too, this engine generalizes; if MIS Builder ever gains per-source expressions, revisit this.
