# Borrower is an hr.employee; drafter is a separate field; Strict own-only mode

Status: accepted (2026-09; UAT-only) — amends ADR-0005 & ADR-0010

## Context & Decision

Three identity-shaped gaps, folded into one decision because they all touch the same field:

1. **The borrower must be an organization staff member.** `requested_by` (`res.users`) is too broad — it admits portal users and bots, and carries no link to personnel data. It is retyped to `employee_id` (`hr.employee`), required, defaulting to `self.env.user.employee_id`.
2. **The drafter must be a real, correctable field.** "Who filled this form in" previously lived only in `create_uid`, which cannot be fixed when mis-attributed. A new `user_id` (`res.users`) field — "ผู้จัดทำ" — becomes the source of truth instead, editable only by a manager/admin.
3. **Some organizations want to disable draft-on-behalf entirely.** ADR-0010 gave the `user` tier the power to draft for someone else; a new Strict mode setting (`advance_payment.strict_own_only`, default off) switches that power off, `base.group_system` excepted.

`employee_id` does double duty: it is both the **borrower's identity** on the contract (name shown, payable partner, one-agreement-per-person rule) and a **security key** (own-only ir.rule, who may submit). Retyping it therefore touches every comparison against `self.env.user` / `create_uid` / `uid`, and every read of the borrower's partner.

**Field shapes:**
- `employee_id` (Many2one `hr.employee`, required, `default=lambda self: self.env.user.employee_id`) — no `domain` restricting to employees with a linked user: an employee without one can still be picked as borrower, they just cannot submit for themselves (decision below).
- `user_id` (Many2one `res.users`, required, `default=lambda self: self.env.uid`) — "ผู้จัดทำ".
- `partner_id` (Many2one `res.partner`, `related="employee_id.work_contact_id"`, `store=True`) — replaces `requested_by_partner_id`; the single source for bank matching (`bank_id` domain) and payment `partner_id`. `work_contact_id` is this repo's employee↔partner link (used already by `agx_approval`'s participant resolver and backfilled by `hr_partner_type_kmitl`) — not `address_home_id`, which core `hr_expense` uses but which is `groups="hr.group_hr_user"` and unused elsewhere in this repo.

**No new ACL on `hr.employee` is needed**: `HrEmployeePrivate` falls back to `hr.employee.public` on every path a form/dropdown exercises (`name_get`, `read`, `_read`, `_search`, `get_view(s)`, `get_formview_id/action`), so a borrower holding only `base.group_user` can display/search employees without explicit rights.

**Permission matrix for editing `employee_id`:**

| Actor | Strict off (default) | Strict on |
|---|---|---|
| `base.group_system` | editable | **editable** (escape hatch) |
| `group_advance_payment_user`+ (incl. `manager`, `loan_officer`) | editable | not editable |
| `group_advance_payment_own_only` | not editable (defaults to self) | not editable (defaults to self) |

Both the UI gate and the constraint read the same helper (`_can_draft_on_behalf`) — the split expression across form and Python was finding #2 from the prior review round.

```python
def _is_strict_own_only(self):
    return str2bool(
        self.env["ir.config_parameter"].sudo()
        .get_param("advance_payment.strict_own_only", default=False)
    )

def _can_draft_on_behalf(self):
    if self.env.user.has_group("base.group_system"):
        return True
    return not self._is_strict_own_only() and self.env.user.has_group(
        "advance_payment.group_advance_payment_user"
    )
```

`_check_creator_only` now compares `employee_id.user_id != user_id` (both correctable) instead of `requested_by != create_uid` (immutable creator).

## Why

- The borrower must be provably an employee of the institute — `res.users` is too wide (portal, bots, users without personnel records) and gives no path to personnel data.
- `create_uid` cannot be corrected, so a mis-attributed "who drafted this" was permanent; a real field lets a manager fix it.
- Organizations differ on whether draft-on-behalf should exist at all — a toggle avoids forking ADR-0005 (creator-only) vs. ADR-0010 (draft-on-behalf) per deployment.
- `work_contact_id` is already this repo's employee↔partner bridge; `address_home_id` (core `hr_expense`'s choice) is unused here and gated behind `hr.group_hr_user`.

## Consequences

- The "one active agreement per borrower" key moves from `res.users` id to `hr.employee` id (`_check_one_active_agreement`), which is the more correct key.
- `_check_creator_only` compares `employee_id.user_id != user_id`, not `create_uid` — a manager correcting `user_id` changes what the constraint checks against.
- The own-only ir.rule ORs two paths — `('employee_id.user_id', '=', user.id)` and `('user_id', '=', user.id)` — so a staffer who drafted on someone else's behalf keeps seeing that record even after being removed from the `user` tier.
- `hr_employee_security_role/security/hr_security.xml` restricts `hr.group_hr_user` holders to their `master_department_id` when browsing employees — so a staffer who *also* holds an HR group sees a **narrower** borrower dropdown than one who doesn't (who gets the public-model fallback = everyone). `group_hr_central_user` is unaffected.
- `work_contact_id` can be empty (an employee archived before `hr_partner_type_kmitl` was installed, or cleared by core when `user_id` is unset) → `partner_id` empty → no bank options and a payment with `partner_id = False`.
- Trap to remember: `hr/security/hr_security.xml` hides `res.partner.bank` from `base.group_user` once `partner_id.employee_ids` (i.e. `address_home_id`) is non-empty. Harmless today because this repo never writes `address_home_id`, but setting `address_home_id = work_contact_id` anywhere would silently hide the borrower's bank accounts.
- No migration script is written; UAT clears the `advance_payment` table before upgrade (see module README/PR notes) instead of converting the old `res.users` ids, because the two tables' ids are independent sequences that collide low — a same-value id after retype would silently point at the wrong employee rather than fail loudly.
- No manifest version bump — module is not yet in production.
