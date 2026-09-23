# The approver is a named field, configured in Settings, and gets a To-Do when verification finishes

Status: accepted (2026-09; UAT-only) — amends ADR-0006, extends ADR-0015

## Context & Decision

Approval (`to_approve` → `waiting_transfer`) was a single manager sign-off with **no named owner**: `action_approve` is gated on `group_advance_payment_manager` and any member could act, so nothing told a specific person a request was waiting on them. The verification step had already grown both halves of that (ADR-0013's `loan_verifier_id` + its To-Do, ADR-0015's lifecycle); this mirrors them on approval.

- **`approver_id`** (`res.users`, `required=True`, `tracking=True`, domained on `group_advance_payment_manager`) records who is expected to approve a given agreement. Manager-editable after `draft`, like `loan_verifier_id`.

  > ADR-0017 moves this domain (and `action_approve`'s authorization) off `group_advance_payment_manager` onto a new standalone `group_advance_payment_loan_approver`, narrowing approval to the named assignee. `approver_id` stays manager-editable; see that ADR for the up-to-date group.
- **Settings carries the standing approver** — `advance_payment.default_approver_id`, a `res.users` `config_parameter` many2one. `_default_approver_id` prefers it, ignores it when the target is no longer an active member of the manager group, and otherwise falls back to `base.user_admin`. The parameter is also **seeded to the admin** in `data/advance_payment_config_parameter.xml` (`noupdate="1"`) so a fresh database shows a real value in Settings rather than an empty picker.
- **`action_verify` now schedules the approval To-Do** on `approver_id`, immediately after closing the verification one. `action_approve` marks it done; cancel / ดึงกลับ drop it. All of this reuses ADR-0015's stage-keyed helpers — `_workflow_activity_specs()` simply gained a `to_approve` entry, so no new activity plumbing was added.

Deliberately **not** included: `action_approve` is still open to any manager, not narrowed to `approver_id` the way ADR-0013 narrowed `action_verify`. `approver_id` is an assignment and a routing target, not yet an authority check.

> **Superseded by ADR-0017**, which does narrow `action_approve` to the named `approver_id` (or an admin) — the "not yet" above became "now."

## Why

- The verification step proved the pattern: a named assignee plus an inbox To-Do is what makes a queue-driven workflow work, and ADR-0013's officer inbox is the only reason officers stopped hunting through the list view. Approval had the same gap and the same fix.
- Falling back to `base.user_admin` rather than leaving the field empty is the difference between "an un-configured database still works" and "every create raises". ADR-0013 learned this the hard way — its `required=True` with a default that only resolved for single-officer institutes made every create fail on a multi-officer database, which ADR-0015 then had to fix. Approval has no "sole member" to infer at all (root/admin are standing managers), so a fallback is the only way to keep the field required.
- Seeding the parameter *and* keeping the code fallback is not redundant: the seed makes the setting discoverable in the UI, the fallback covers a database that clears it or was upgraded past the `noupdate` seed.
- Membership is checked against the group's `users` (direct membership) rather than `has_group` (which also accepts implied membership), so a configured user can never resolve to a default that the field's own domain then rejects.
- Not narrowing `action_approve` keeps this change to routing only. Approval authority is a governance question (ADR-0006 deferred the whole multi-tier Endorse → Approve chain), and tightening it silently — while the ADR-0011 e-Saraban route is still parked — would pre-empt that decision.

## Consequences

- `approver_id` is `required=True` on an existing table. Odoo's `_init_column` evaluates the default once and backfills every row before adding NOT NULL, so pre-existing agreements all get the seeded admin — no migration script needed.
- Because approval is not restricted to `approver_id`, a manager other than the assignee can approve. The To-Do is still closed (the helpers `sudo()`, see ADR-0015), but it will read as done by someone who was never the assignee. That is accepted for now; narrowing `action_approve` is the follow-up if it matters. **Done in ADR-0017.**
- `_default_approver_id` reads an `ir.config_parameter` on every create, `sudo()`'d so an own-only borrower can create without read access on the parameter — same shape as `_default_loan_verifier_id`.
- Two To-Dos of the generic "To Do" type now exist per agreement over its life, distinguished only by summary (`"ตรวจสอบคำขอยืมเงิน <name>"` vs `"อนุมัติคำขอยืมเงิน <name>"`). ADR-0015's warning applies to both: renaming either string orphans to-dos raised before the change.
- `action_recall` from `to_approve` drops the approval To-Do (it calls `_drop_workflow_activities()` with no stage, i.e. all of them), so a borrower pulling a request back does not leave the approver something to act on.
- If the ADR-0011 e-Saraban bridge is ever revived, it must close the approval To-Do on the Sarabun completion callback as well — the bridge calls base `action_approve()`, which already does it, but any path that bypasses `action_approve` would not.
