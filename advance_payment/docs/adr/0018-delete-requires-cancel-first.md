# An agreement may only be deleted once cancelled

Status: accepted (2026-09; UAT-only) — amends ADR-0005

## Context & Decision

`group_advance_payment_own_only` had no delete right on `advance.payment` at all (`perm_unlink=0`) — a borrower who mis-created a request had no way to remove it, only `button_cancel()` from `draft` to mark it `cancel` and leave it sitting in the list forever. Grant the right, gated by state instead of by group: `perm_unlink=1` for `group_advance_payment_own_only`, plus a Python `unlink()` override that requires every record be in `state == 'cancel'` first — `base.group_system` excepted, the same escape hatch `write()` already uses for its protected-field guard.

The gate is on `unlink()` itself, not on who is deleting, so it applies uniformly to every group with delete rights on the model (`own_only` and `manager` alike) — an agreement that is still active, in progress, or settled is the audit trail, not scratch data, regardless of who is holding the delete button.

## Why

- A borrower already has a self-service way to reach `cancel` from `draft` (`button_cancel`, no group restriction beyond seeing the record) — deletion just needed to be unlocked from the same state, not a new workflow.
- Requiring cancel-first instead of just checking "own record, draft only" means the same rule also covers a manager cleaning up an old cancelled agreement, without having to duplicate the check per group.
- `advance.payment.return.line` and `advance.payment.usage.line` are `ondelete="cascade"` on `agreement_id`; `account.payment.advance_payment_id` is `ondelete="set null"`. Requiring `cancel` first does not by itself stop a cancelled-but-once-disbursed agreement (with real return lines / vouchers) from being deleted and cascading — that risk already exists for `manager`'s unrestricted unlink today and is not newly introduced here. Narrower deletion protection for a settled record (e.g. gating on `effective_date`) is a separate follow-up if it turns out to matter in practice.

## Consequences

- `unlink()` raises `UserError` naming the blocked agreements, not a silent no-op — the caller finds out which records need cancelling first.
- `ir.model.access.csv`'s `access_advance_payment_user` row now grants full CRUD to `group_advance_payment_own_only` except that unlink is further restricted at the model level (ACL is necessary but not sufficient — the Python check is the real gate).
- `approval_request_allocation.advance_payment_id` (`agx_approval_advance_payment`) is `ondelete="restrict"` — deleting an agreement still allocated against an approval request fails with a `ForeignKeyViolation` regardless of this ADR; that FK is the safety net for that specific link, not something this change touches.
