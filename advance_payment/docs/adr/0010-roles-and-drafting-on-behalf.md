# Roles restructured to own-only / user / manager / loan officer; drafting on behalf allowed

Status: accepted (2026-08; UAT-only) — amends ADR-0005

## Context & Decision

The permission model is restructured into a clean implied chain **own-only → user → manager**, plus two standalone groups:

- `group_advance_payment_own_only` (was `group_advance_payment_user`): sees and creates only their own agreements — the default borrower tier.
- `group_advance_payment_user` (was `group_advance_payment_officer`): sees every agreement and may **draft one on behalf of another borrower** — data entry only, no verify/approve/workflow actions.
- `group_advance_payment_manager` (unchanged xml id): approves (manual fallback) and cancels; implies `user`.
- `group_advance_payment_loan_officer` (**new**): the standalone oversight tier — owns every workflow action (verify, reset-to-draft, accept-report, reconcile/return-lines, due-date, bank correction, return-line approve/reject). Implies `user` (sees all).

A new per-record field, `loan_verifier_id` (Many2one `res.users`, domain = loan-officer group members, defaulted to the sole member when exactly one exists, editable by the creator while in `draft`, manager-only after — see ADR-0013) — "เจ้าหน้าที่งานเงินยืม" — records who is responsible for a given agreement.

`_check_creator_only` is relaxed: a `user`-tier staffer (or a `base.group_system` admin) may create a loan with `requested_by` pointing at someone else — but `_check_submit_permission` is **unchanged**, so only the borrower (or an admin) may call `action_submit()`. The borrower still has to submit personally; only *drafting* moves.

> ADR-0014 retypes `requested_by` into `employee_id` (`hr.employee`) + a separate `user_id` (`res.users`, "ผู้จัดทำ"), moves `_check_creator_only` to compare `employee_id.user_id` against `user_id`, and adds a Strict mode setting that can switch this tier's draft-on-behalf power off.

The escape hatch for exceptional data fixes stays `base.group_system`, never `manager` — a manager only gets the normal manager buttons.

## Why

- Front-desk / department staff routinely help borrowers fill in a request, but the borrower must remain the one who commits to the loan (external-audit transparency, legal liability) — splitting "who may draft" from "who may submit" satisfies both.
- The old `officer` tier conflated "sees everything" with "does workflow actions" (verify/accept-report/bank correction). Splitting that into a data-entry `user` tier and a standalone `loan_officer` tier matches how the institute actually staffs the role: several people can help enter requests, but only the designated เจ้าหน้าที่งานเงินยืม signs off on them.
- The xml-id rename (`user`→`own_only`, `officer`→`user`) keeps the group ids matching the words the UI now uses for each tier, instead of carrying forward the old officer-centric naming.

## Consequences

- All group xml-id references inside `advance_payment/` are renamed in lockstep (security.xml, ir.model.access.csv, views, menus, tests, i18n) — verified no other installed module references these ids, so the rename is safe.
- ACLs simplify: since permissions are additive across the implied chain, the old officer's read-only ACL rows on `advance.payment` / `usage.line` / `return.line` are dropped as redundant (already inherited from `own_only`'s R/W/C via the `own_only → user` implication).
- `write()`'s protected-field guard (material fields, bank correction) re-gates from the old `officer` group to `loan_officer`.
- `is_officer` is renamed `is_loan_officer` throughout (model + views); a new `is_manager` computed field is added to gate `loan_verifier_id`'s edit rights in the form.
- The submit button is additionally gated on a `can_submit` computed field (mirrors `_check_submit_permission`: requester or admin) so a `user`-tier drafter never sees a submit button that would raise a `UserError` on click.
- Symmetrically, `requested_by` is a single field gated on a `can_draft_on_behalf` computed field (mirrors `_check_creator_only`: `user` tier or admin). The form previously rendered an editable copy only for `base.group_system`, which made drafting on behalf unreachable from the UI.
- ADR-0014 changes the type of the borrower field (`requested_by` → `employee_id`) and makes `can_draft_on_behalf` togglable via a Strict mode setting; see that ADR for the up-to-date field names.
