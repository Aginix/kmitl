# The verify To-Do is closed when the check happens, and the officer + bank account default themselves

Status: accepted (2026-09; UAT-only) — amends ADR-0005 & ADR-0013

## Context & Decision

Three loose ends left by ADR-0013's To-Do and by ADR-0014's borrower retype.

**The verify To-Do now tracks reality.** `action_submit` schedules a "To Do" `mail.activity` on `loan_verifier_id`; nothing ever closed it. `action_verify` now marks it **done** (`action_feedback`, which posts an `mail.mt_activities` message and unlinks the activity), and the three transitions that take a request out of `to_verify` *without* it having been checked — `_action_do_cancel`, `action_reset_to_draft` / `_action_do_reject` (ส่งกลับแก้ไข), `action_recall` (ดึงกลับ) — **drop** it instead. All four route through one `_workflow_activities(stage)` helper that matches on activity type **and** summary, because `mail.mail_activity_data_todo` is the generic type and a blanket `activity_feedback`/`activity_unlink` would sweep up unrelated to-dos on the same record. The helpers are keyed by the *state* that owns the to-do (`_workflow_activity_specs()` maps a state to its summary + assignee) rather than hard-coded to verification, so ADR-0016 could add the approval to-do without a second copy of the same four methods.

**`loan_verifier_id` gets a configurable default.** Settings carries
`advance_payment.default_loan_verifier_id` (a `res.users` `config_parameter` many2one, domained on the loan-officer group). `_default_loan_verifier_id` prefers it and falls back to the previous behaviour — the sole real officer, root/admin excluded. A stale setting (user deleted, archived, or dropped from the group) is ignored rather than fed to the field and rejected by its own domain.

**`bank_id` fills itself in from the borrower.** `_onchange_employee_id` no longer just clears a mismatched account; it re-points `bank_id` at the new borrower's **first** `res.partner.bank` (in that model's own order) via `_default_bank_id()`. Because the web client's initial onchange pass runs every onchange method, a borrower drafting for themselves also gets their account filled from the start.

## Why

- A To-Do that survives verification defeats the point of ADR-0013's officer inbox: the officer works from a queue that never shrinks, and the only way to clear it is the generic "mark done" button, which records a check that the state machine never saw. Worse, cancel had no reschedule to clean up after it (unlike recall/resubmit, whose reschedule already de-duplicated), so a cancelled loan left a permanently un-actionable to-do — the officer cannot verify a `cancel` record.
- Dropping rather than completing the negative transitions is deliberate: `action_feedback` writes a done-message into the record's chatter, and claiming "ตรวจสอบเรียบร้อย" on a request that was cancelled or bounced back would be a false audit trail. The chatter already logs those transitions on their own.
- ADR-0013 made `loan_verifier_id` `required=True` while its default only resolved for a single-officer institute; its own Consequences flagged that any multi-officer database would make every create raise, including the bridges' programmatic ones (`purchase_request_advance_payment.action_create_advance_payment`). A configured standing assignee closes that without weakening the per-record assignment that ADR-0013 enforces.
- The bank account was the one field a borrower had to re-pick by hand after ADR-0014 moved the payee partner from the user to `employee_id.work_contact_id`. Picking the first account outright — rather than only when unambiguous — is safe because the officer may still correct `bank_id` up to the transfer (ADR-0005), and a wrong-but-present account is caught by the same officer check that already guards the transfer.

## Consequences

- `_workflow_activities()` is keyed on the summaries declared in `_workflow_activity_specs()` (`"ตรวจสอบคำขอยืมเงิน <name>"`). Changing one of those strings orphans to-dos raised before the change — they will neither be closed nor dropped. Rename them only together with a data fix.
- The helpers `sudo()` the activity write/unlink. `mail_activity_rule_user` limits both to the activity's `user_id` or `create_uid` — the assignee and whoever moved the record into the stage — so a manager cancelling, or an admin acting for the assignee, would otherwise hit an `AccessError`. Authority is established by each caller's own check first, and `sudo()` keeps `env.uid`, so the done-message is still authored by the real actor.
- The done trail is a `mail.message` with subtype `mail.mt_activities`, not a surviving `mail.activity` row: Odoo 16 `_action_done` unlinks the activity. Any report counting "completed verifications" must read messages, not activities.
- `_default_loan_verifier_id` reads an `ir.config_parameter` on every create. It is `sudo()`'d, so an own-only borrower can create without read access on the parameter.
- The setting is a plain many2one `config_parameter`, so it stores the id as text; `res.config.settings.get_values` already tolerates a deleted target (`odoo/addons/base/models/res_config.py:497-503`) and `_default_loan_verifier_id` re-validates group membership on top of that.
- `_default_bank_id()` returns an empty recordset when the work contact has no bank account. That is left to the existing blocking exception rule on `bank_id`, which stops `action_submit` — the loan is not silently submitted without a payee account.
- Programmatic creates still do not run onchange, so a bridge that creates a loan without `bank_id` gets an empty one and is blocked at submit exactly as before. Bridges that want the default must call `_default_bank_id()` (or `_onchange_employee_id()`) themselves.
