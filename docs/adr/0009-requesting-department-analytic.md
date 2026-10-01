# Requesting Department is an analytic ส่วนงาน, not an hr.department

The PR's "which ส่วนงาน asks for this" used to be `department_id` (hr.department) from
the OCA `purchase_request_department` module, and the PA copied it into its own
`requesting_department_id` (also hr.department), which also named the หนังสือ's issuing
ส่วนงาน. We replace both with `requesting_department_id` → `account.analytic.account`
restricted to the `departments` plan, on the PR, the PA (copied, ADR-0004) and the PO
(copied by the PR→PO wizard), and drop `purchase_request_department` entirely: no module
depends on it any more and it is uninstalled by hand (only UAT carries data; existing
values are re-mapped by matching `hr_department.code` to the analytic `code`, unmatched
rows left empty). The Requesting Department is deliberately a separate field from the
budget's `department_analytic_id`, because the unit that asks is often not the unit
whose money pays. The e-Saraban sender stays an hr.department taken from the requester's
employee record (editable on the draft หนังสือ), because the register lookup is keyed on
hr.department and there is no stored link from analytic departments to hr.department.
`purchase.order.department_id` (hr.department, owned by `purchase_order_kmitl`) is kept,
hidden, because asset batches and asset numbering still read its `short_name`.

## Considered Options

- **Keep `purchase_request_department` installed and just hide the field**: no migration
  needed, but it leaves a dead, silently-defaulted column and a dependency nobody reads.
- **Reuse the budget's `department_analytic_id`**: wrong whenever a ภาควิชา requests
  against its คณะ's pool.
- **Keep hr.department**: it does not line up with the ส่วนงาน vocabulary used by every
  other financial document, and it cannot be reported alongside the six dimensions.
