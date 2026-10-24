# All four dimensions are required on an invoice

A receipt requires only its department; an invoice requires **all four** of the
dimensions the accounting office reads — ส่วนงาน (`departments`), แหล่งเงิน (`sources`),
กองทุน (`funds`) and ด้าน/แผนงาน/กิจกรรม (`activities`). The other two
(`kmitl_project`, `procurement_plan`) stay optional. The four fields are stored and
`required`, so the database refuses a row without them, and the form marks them required.

## Why stricter than the receipt

`accounting_kmitl/views/account_move_views.xml` makes the four required on the
`account.move` form of **every** move type. An invoice raises a draft `out_invoice`; if that
came out with a dimension missing, the accounting office could not save the form when it
presses **Submit**, and the problem would surface at the far end of the chain, in another
office, on a document the department can no longer edit.

## Considered options

- **Relax the accounting form for an `out_invoice`.** Rejected: it would reach into
  `accounting_kmitl` to make a rule weaker for one document, and would leave receivables
  with dimensions that no report could filter by.
- **Require only the department, as a receipt does, and let accounting fill the rest.**
  Rejected: the accounting office does not know the fund an officer is billing to.
- **Chosen: require all four at the source**, on the document of the office that does know.

## Consequences

- **A programmatic `create()` must name all four.** They are stored computed fields with
  an inverse, `NOT NULL` at INSERT, and Odoo computes stored fields only after the INSERT.
  Stating the JSON alone is not enough. The receipt a payment creates states every one of
  them too: its `source_analytic_id` carries a default whose inverse would otherwise write
  over the invoice's own source.
- **Header and lines.** The header's distribution is the single source of truth and is
  pushed onto every line when the invoice is created and whenever a dimension, the JSON or
  the lines change (`_sync_analytic_to_lines`); the line column is read-only. The
  convenience fields are only compute/inverse views of `analytic_distribution`.
- **The receivable leg carries the dimensions as well**, which changes what a dimension
  filter on the Trial Balance and the General Ledger returns — see `CONTEXT.md` →
  Known limitations.
