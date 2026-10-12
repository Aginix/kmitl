# Workflow To-Dos cover the back half of the lifecycle

Status: accepted (extends ADR-0015/0016/0020; pre-production, no migration/version bump)

## Context & Decision

ADR-0013, 0015, 0016 and 0020 added a workflow To-Do one approval step at a time, each as that
step gained a named owner: `to_endorse` → `endorser_id`, `to_verify` → `loan_verifier_id`,
`to_approve` → `approver_id`. Nothing after approval ever got one. That was never decided — the
back half was simply never reached — but the effect was that once a loan was approved, nobody's
tray said what was waiting on them: not the officer who has to issue the ใบสำคัญจ่าย, not the
borrower who has to file the expense report, not the officer who has to accept it.

(`advance_payment_followup`'s "ติดตามลูกหนี้เงินยืม" To-Do is a different thing: a cron-driven
debt-chasing task for the officer near and past the due date, only present when that module is
installed. It is keyed on its own summary and does not collide with these.)

The four back-half states now each own a To-Do in `_workflow_activity_specs()`:

| State | Assignee | Raised by | Closed (done) by |
|---|---|---|---|
| `approved` | `loan_verifier_id` | `action_approve` | `action_create_payment_voucher` |
| `in_progress` | the borrower, `employee_id.user_id` — due on `return_due_date` | `action_start` | `action_submit_report` |
| `reported` | `loan_verifier_id` | `action_submit_report` | `action_accept_report` |
| `to_reconcile` | the borrower | `action_accept_report` (when there is money to return) | `_do_close` |

## Design

- **Two stages wait on the borrower, not on staff.** Every earlier To-Do belongs to an approver
  or an officer; `in_progress` and `to_reconcile` are genuinely the borrower's move.
- **No assignee, no To-Do.** A borrower whose employee has no linked user gets none.
  `activity_schedule(user_id=False)` would otherwise fall back to the *acting* user — the officer
  who accepted the report would find the borrower's task in their own tray.
- **Only the report To-Do carries a real deadline** (`_workflow_activity_deadline`), and it is
  `return_due_date`. The officer usually sets or moves that date after the transfer, so `write()`
  updates the open To-Do's `date_deadline` in place rather than re-raising it.
- **`_do_close` closes whatever is open.** Every close funnels through it — accepting a report with
  nothing to return, `action_close`, and the auto-close once the debt is settled — so the
  `reported` / `to_reconcile` To-Do is marked done there instead of in each caller.
- **`action_start` drops a leftover `approved` To-Do** before raising the next one, in case a
  voucher was produced some other way than `action_create_payment_voucher`.
- **Cancel needs nothing new.** `_drop_workflow_activities()` already iterates every stage in the
  specs, so the added stages are dropped on cancel for free.
- No new permission surface: `activity_schedule` marks its activities `automated`, which Odoo
  exempts from the assignee-can-read-the-document check at create.

## Not covered

- **`action_reopen`** (`done` → `in_progress`/`to_reconcile`) does not re-raise the To-Do of the
  state it returns to. It is an admin-only recovery path; left for when it is needed.
- **The officer's side of returning money.** Approving a return line happens on
  `advance.payment.return.line`, a separate model, and raises nothing on submission
  (`pending_review`).
- **Reassigning `loan_verifier_id`** does not move its open To-Do, for `to_verify` (pre-existing)
  as well as the new `approved` / `reported` stages — unlike `endorser_id`, which does (ADR-0020).
