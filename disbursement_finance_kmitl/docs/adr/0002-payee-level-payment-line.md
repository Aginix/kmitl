# The paying account lives on a payee-level payment line

A disbursement request pays a name list, and its payees genuinely are paid different
ways out of different accounts — so the paying account (หัวจ่าย) has to be recorded per
payee. It is stored on `disbursement.payment.line`, one row per payee per request, 1:1
with the posted bill and with the `account.payment` that will pay it.

## Considered options

- **On `disbursement.request.line`.** That is one _item_ being reimbursed, so a payee
  with three receipts would hold three copies of a decision that must be identical
  across all of them, plus the validation to enforce that sameness. Here the invariant
  is structural instead of checked.
- **A representative "primary line" flag** on the request line, with the tab filtered to
  one row per payee and writes fanned out to the siblings. Cheaper (no new model) but
  keeps the duplicated-decision invariant and makes "the first line of the payee" a
  load-bearing fiction.
- **Two fields on the vendor bill** (`account.move`), which is already the payee-level
  record — or on the `account.payment` itself, created early as a draft. Rejected on
  security grounds: Odoo ACLs are model-level, so letting the disbursement auditor write
  those fields would grant them write access to every bill (or every payment) in the
  system. The auditor group implies only `disbursement.group_disbursement_user` and has
  no accounting rights at all.

## Consequences

- The payment line reads its amount from the **posted bill** (residual net of WHT), not
  from the sum of the request lines. Accounting may adjust a bill before posting, so the
  request-line sum is what was asked for while the bill is what will be paid — and the
  finance office's last screen before the money leaves must show the latter.
- `_payment_amount_vals()` is the single place the money is worked out, so the row the
  finance office reviews and the payment that leaves the bank cannot disagree.
- Rows are made when the request reaches `bills_posted`. A bill later reversed or
  cancelled leaves its row behind rather than deleting it, so the audit trail of what
  was reviewed survives.
