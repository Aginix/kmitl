# Access control for receipts/remittances via Operating Unit, not department

Row-level access to `kmitl.receipt` and `kmitl.receipt.remittance` is scoped by
**Operating Unit**, not by the issuing department. The base module therefore
carries no row-level record rules and no `res.users.kmitl_department_ids` field —
the department (`department_analytic_id`) is kept purely as a business dimension
(fiscal-year running number, remittance bundling, analytics).

## Considered Options

- **Department-based record rules** (the original design): cashiers saw only
  receipts whose department was in their `kmitl_department_ids`. Rejected —
  duplicates the Operating Unit access layer that every other KMITL app already
  uses, and forced a second per-user department list to maintain.
- **Operating Unit** (chosen): aligns with the repo-wide `*_operating_unit` /
  `*_operating_unit_access_all` pattern. Scoping lives in the add-on module
  `receipt_kmitl_operating_unit` as a global `ir.rule`; a companion
  `receipt_kmitl_operating_unit_access_all` group lets privileged users bypass it.

## Consequences

- Installing the **base** `receipt_kmitl` alone gives **no** row-level scoping
  (a cashier sees every receipt in the company). This is acceptable because the
  OU add-on is always installed in this deployment, matching every other module.
- The generated `account.move` inherits the receipt's `operating_unit_id` (the
  OU module depends on `account_operating_unit`), so OU-based accounting reports
  stay correct. `_create_move()` in the base exposes `_prepare_move_vals()`
  (header) and `_prepare_move_line_vals()` / `_prepare_debit_line_vals()` (lines)
  as override hooks. The OU bridge stamps the `operating_unit_id` on all three.
- **Note:** `account_operating_unit`'s `_check_journal_operating_unit` constraint
  will raise if a journal's `operating_unit_id` differs from the move's. No
  journal in this deployment sets `operating_unit_id`, so this is not triggered.
  If journals are later OU-scoped, payment method configuration must match.
