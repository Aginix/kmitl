# Payment axes live on a payee-level payment line, not on the request line

The payment axes (method, paying account, payee bank account) were stored on
`disbursement.request.line`, which is one *item* being reimbursed — so a payee
with three receipts had three copies of a decision that must be identical
across all of them, and `_check_payment_classification` carried three blocks of
validation whose only job was to enforce that sameness. We introduced
`disbursement.payment.line`, one row per payee per request (1:1 with the posted
bill and with the `account.payment` that will pay it), and moved those axes
there. The mixed-value checks are gone: the invariant is now structural rather
than enforced.

## Considered Options

- **A representative "primary line" flag** on the request line, with the tab
  filtered to one row per payee and writes fanned out to the siblings. Cheaper
  (no migration, no new model) but keeps the duplicated-decision invariant and
  the validation that guards it, and makes "the first line of the payee" a
  load-bearing fiction.
- **Two fields on the vendor bill** (`account.move`), which is already the
  payee-level record. Rejected on security grounds: Odoo ACLs are model-level,
  so letting the disbursement auditor write those two fields would grant them
  write access to every bill in the system — the auditor group implies only
  `disbursement.group_disbursement_user` and has no accounting rights today.

## Consequences

- The payment line reads its amount from the **posted bill** (residual net of
  WHT), not from the sum of the request lines. Accounting may adjust a bill
  before posting, so the request-line sum is what was asked for while the bill
  is what will be paid — and the finance office's last screen before the money
  leaves must show the latter.
- Rows are made when the request reaches `bills_posted`. A bill later reversed
  or cancelled leaves its row behind rather than deleting it, so the audit
  trail of what was reviewed survives.
- Requires a migration that folds the existing per-item values into payee rows
  for requests already in flight past `bills_posted`.
