# Receipt Remittance workflow: approval stage + two error-correction paths

`kmitl.receipt.remittance` (รายงานนำส่งคลัง — the renamed `kmitl.cash.deposit`)
is the document a department submits to remit its confirmed receipts to the
central treasury. It follows an HR-expense-sheet-like flow.

## Workflow

- States: `draft → submitted → approved → posted` (+ `cancelled`).
- `submitted`: department action; stamps `date` = the actual submission date,
  mints the number `RM/<FY>/nnnn` where `<FY>` is the 4-digit Buddhist-era fiscal
  year of that date, and schedules a mail activity on the remittance's
  `approver_id`. Header becomes read-only.
- `approved`: the `approver_id` (a `group_receipt_kmitl_remittance_approver`
  user) action; completes the approver's activity.
- `posted`: central treasury/finance action; creates one accounting entry per
  receipt and marks each receipt `done`.
- `action_draft` can reset a remittance back to `draft` from `submitted`,
  `approved`, or (manager-only) `posted` — this was originally planned as an
  extension point and has since been implemented, reversing this ADR's original
  "once submitted, a remittance can never be reset to draft" statement.

This adds the approval step this ADR originally described as a future
extension — the approver reviews before treasury posts.

## Error correction — two mechanisms

1. **Remove one receipt** from a `submitted` remittance using the standard
   `many2many`-style widget on the `receipt_ids` field (the × on a row). The
   receipt's `remittance_id` clears and its state automatically returns to
   `to_submit`, so it re-enters the pending pool and can be corrected and
   pulled into a later remittance. The remittance itself stays `submitted`.
   No custom detach button/method is needed — the widget already supports
   this per-receipt use case.
2. **Reject the whole remittance** (`action_reject`, approver-only, from
   `submitted`) with a required reason logged to chatter. All its receipts
   return to `to_submit` and the remittance itself returns to `draft` for
   correction and resubmission.

This is a change from the original detach-only design (see "Why" below).

## Scope of a remittance

- A remittance names one `department_analytic_id`; it pulls and validates
  receipts by `child_of` that department, so a parent (rollup) department gathers
  all sub-department receipts. Department here is a business/bundling dimension,
  not access control (see ADR-0001).

## Why

The original design rejected whole-batch reject/reset in favor of a custom
per-receipt "detach" button, reasoning that a remittance can carry hundreds of
receipts and an error usually affects only a few. In practice the custom
detach button was never implemented or wired to the UI — the standard o2m
widget already gives departments and approvers that exact per-receipt
granularity for free, so a bespoke detach action was unnecessary. A whole-
remittance reject was added back on top of that, gated to the approver, for
the case where the entire batch needs to go back for rework (e.g. wrong
department or approver) rather than a single bad line.
