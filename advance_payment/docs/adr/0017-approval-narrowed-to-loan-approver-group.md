# Approval is narrowed to a named approver group, mirroring the loan officer

Status: accepted (2026-09; UAT-only) — amends ADR-0006 & ADR-0016

## Context & Decision

ADR-0016 gave approval a named assignee (`approver_id`) and a To-Do, but deliberately left `action_approve` open to *any* `group_advance_payment_manager` member — "an assignment and a routing target, not yet an authority check." In practice that domain choice also meant the only people ever selectable as `approver_id` (in the record field or the Settings default) were whoever already held `group_advance_payment_manager` — a group that also carries cancel rights, drafter-editing rights (`can_edit_drafter`) and reassignment rights over `loan_verifier_id`/`approver_id` themselves. An institute could not name a pure approver without also handing them all of that.

This closes the gap the same way ADR-0013 already closed it for verification:

- **New standalone group `group_advance_payment_loan_approver`** — same shape as `group_advance_payment_loan_officer`: `category_id=False` (an independent checkbox, not part of the own_only→user→manager radio), implies `user`, seeded with `base.user_root`/`base.user_admin` as the standing escape hatch.
- **`approver_id`'s domain and `_approver_candidates()` move to the new group**, not `group_advance_payment_manager`. `advance_payment_default_approver_id` in Settings follows the same domain.
- **`action_approve` is narrowed**: a new `_check_approve_permission()` (`is_admin or rec.approver_id == self.env.user`) is called first, exactly mirroring `_check_verify_permission()`. The approve button's `groups=` moves from `group_advance_payment_manager` to `group_advance_payment_loan_approver`, and gains a `can_approve` computed field (mirrors `can_verify`) so a loan-approver-group member who isn't the one assigned never sees a button that would raise on click.
- **`is_manager` still gates who may *reassign* `approver_id`** (and `loan_verifier_id`, `user_id`) — that stays a `group_advance_payment_manager` privilege, unchanged. Only *who may click อนุมัติ* moves off manager.

## Why

- Symmetry: verification already went through exactly this evolution (ADR-0013 narrowed a group-wide action to a named assignee). Approval had the same shape of gap and the same fix was already proven out.
- Domaining the picker on `group_advance_payment_manager` conflated "eligible to be named approver" with "holds every manager privilege" — an institute could not grant approval authority narrowly. A standalone group separates the two, the same way `loan_officer` is already separate from `manager`.
- Leaving `action_approve` open to any manager (ADR-0016's original choice) meant `approver_id` could name someone who then wasn't the only one able to act — anyone else with the broader group could approve out from under them, undermining the point of naming an assignee at all.

## Consequences

- **Breaking for any database that already relied on "any manager can approve"**: after this change, a manager who is not also a member of `group_advance_payment_loan_approver` (or the specific record's `approver_id`) no longer sees the "อนุมัติ" button. Accepted because the module is still UAT-only — no migration script, no version bump. A real deployment must explicitly add its approvers to the new group (Settings → Users → Advance Payment) before upgrading.
- `base.group_system` remains the sole override — an admin may always approve regardless of `approver_id`, same escape hatch as verify.
- `group_advance_payment_manager` and `group_advance_payment_loan_approver` are independent siblings (both imply `user`, neither implies the other) — a manager is not automatically an eligible approver, and an approver is not automatically a manager (cannot cancel, cannot edit the drafter field, cannot reassign `loan_verifier_id`/`approver_id`).
- `_approver_candidates()` and `_default_approver_id()`'s fallback logic (Settings setting, else `base.user_admin`) are otherwise unchanged from ADR-0016 — only the group they draw from moved.
- No new `ir.rule` is needed: `group_advance_payment_loan_approver` implies `user`, which already carries the "sees all" record rule, exactly as `loan_officer` relies on the same implication today.
