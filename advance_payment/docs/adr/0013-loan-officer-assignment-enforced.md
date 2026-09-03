# The assigned loan officer is required and is the only one who may verify

Status: accepted (2026-09; UAT-only) — amends ADR-0010

## Context & Decision

`loan_verifier_id` becomes `required=True`. `action_verify()` (the ตรวจสอบข้อมูล step that sends the request into approval) is now gated on `_check_verify_permission()`: only the specific user named in `loan_verifier_id` on that record — or a `base.group_system` admin — may call it. Previously the button was gated only at the group level (`group_advance_payment_loan_officer`), so any officer could verify any agreement regardless of who it was assigned to.

`base.user_root` and `base.user_admin` are added as standing members of `group_advance_payment_loan_officer`, so an admin can always be picked as `loan_verifier_id` and always passes `_check_verify_permission` via the admin exemption. The auto-default (`_default_loan_verifier_id`, unchanged in spirit) still picks the sole officer automatically when exactly one exists — but now excludes `base.user_root`/`base.user_admin` from that candidate pool, so a genuinely single-officer setup keeps auto-defaulting instead of the admin's blanket membership making it permanently ambiguous.

Submitting a request (`action_submit`, draft → to_verify) schedules a "To Do" `mail.activity` on the assigned `loan_verifier_id`, so the officer's inbox surfaces the request without them having to search the list view. Recall/resubmit (`action_recall`, then `action_submit` again) clears any stale to-do of the same summary before scheduling a fresh one, so repeat cycles don't pile up duplicates.

## Why

The permission model already recorded who "owns" a given agreement's verification (`loan_verifier_id`, ADR-0010), but nothing enforced it — any loan-officer-group member could act on any record, undermining the "single named officer" design and making the assignment purely cosmetic. Requiring the field and checking it in `action_verify` closes that gap, matching the same creator/assignee pattern already used for `requested_by` (`_check_creator_only`/`_check_submit_permission`) and `requested_by`'s draft-on-behalf gate (`can_draft_on_behalf`).

The field was originally readonly for anyone but a manager at every state, including `draft` — combined with `required=True` and a default that only resolves when exactly one non-admin officer exists, that locked out any non-manager creator whenever the default came up empty. It is now readonly only once the record has left `draft` and the editor isn't a manager, matching how the other material fields (amount, loan type) behave: freely editable while drafting, manager-only to correct afterward.

## Consequences

- `action_reset_to_draft` and `action_accept_report` remain gated only at the `group_advance_payment_loan_officer` level (any officer, not just the assigned one) — this ADR narrows only `action_verify`, per explicit scope decision; extending the same per-record restriction to the other officer actions is a separate future change if needed.
- `can_verify` (computed, mirrors `can_submit`/`can_draft_on_behalf`) hides the "ยืนยันการตรวจสอบ" button in the form for a loan officer who isn't the one assigned, instead of letting them hit the `UserError` on click.
- Dependent create flows that don't explicitly set `loan_verifier_id` (e.g. `purchase_request_advance_payment`'s `action_create_advance_payment`) still rely on the auto-default; if the target database has more than one real named officer at creation time, that default resolves to empty and the create raises — same limitation the manual form already had, just enforced everywhere now.
