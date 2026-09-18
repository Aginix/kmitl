# A cancelled agreement may be reset to draft only before disbursement

Status: accepted (2026-09; UAT-only) — extends ADR-0001

## Context & Decision

A manager may press "Reset to draft" from `cancel` only when `effective_date` is still empty. The reset clears `cancel_reason` and `date_submitted` / `date_verified` / `date_approved`, so the record starts its `draft` life clean rather than carrying stale processing timestamps from the cancelled cycle.

## Why

`_action_do_cancel` accepts cancellation up through `in_progress` / `to_verify_report` / `to_reconcile` — states where the disbursement `account.payment` has already been created and the money has moved. If such a record were reset to `draft`, the `write()` protected-field guard would reopen material fields for editing, and `contract_number`, `actual_expense_amount` and `return_line_ids` from the first cycle would still be attached. Re-submitting and re-approving would then call `action_approve()` again and mint a second disbursement payment for the same loan amount. The correct path once money has moved is a new agreement (consistent with the serial-borrowing model of ADR-0001), not editing the old one back to life.

## Consequences

- Cancelling from `to_verify` / `to_approve` / `waiting_transfer` is still reset-able — no payment was created yet (or the one that was is already cancelled by `_action_do_cancel`), so there is nothing to duplicate.
- A side effect is that `payment_count` still counts the cancelled payment from the void cycle, so the smart button may show a leftover count of payments in `cancel` state after a reset — accepted as a separate, cosmetic concern.
- The "Reset to draft" button hides itself once `effective_date` is set; `action_reset_cancel_to_draft()` raises a `UserError` if called directly (e.g. via RPC/shell) on such a record.
