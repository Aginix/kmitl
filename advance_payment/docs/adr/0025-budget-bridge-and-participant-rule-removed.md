# The budget bridge and the participant rule are removed

Status: accepted (2026-10 UAT feedback; pre-production, no migration/version bump). Supersedes ADR-0008, ADR-0009 and ADR-0019 for the loan; amends ADR-0023 and `agx_approval` ADR-0003.

## Context & Decision

**`advance_payment_budget` is removed.** It carried the loan's financial dimensions (`analytic_distribution` and the four `*_analytic_id` pickers), the ใบจองงบประมาณ (`budget_commitment_id`), the blocking dimensions rule, and the dimensions on the outbound and return payments. The institute no longer uses any of it on the loan. The source bridges stop copying `analytic_distribution` and `budget_commitment_id` from the source document, and drop it from `depends`. `purchase_request_advance_payment` also drops `purchase_request_budget`, which it only needed for those two fields.

**The participant rule is removed.** `agx_approval` ADR-0003 let only a participant of an approval request (`participant_ids`) borrow against it, enforced by the picker's baseline and by `_check_reference_status`. The participant roster is not used any more; on real data no approval request had a participant, so nobody could borrow against one. The AR baseline is now only "approved". Who may pick a request is left to `approval.request`'s own record rules and to the loan type's Reference filter (ADR-0023), which can still express a narrower rule if one is needed.

## Consequences

- A loan carries no dimensions or commitment. Anything downstream that needs them reads the source document (`reference`).
- `advance_payment_budget` was never installed in production. On a database that has it (UAT), do **not** uninstall it before deploying: with the old code both source bridges depend on it, so the uninstall would take them (and their data) with it. Deploy this code, `-u` the bridges (dropping the dependency), then uninstall `advance_payment_budget` from Apps — Odoo removes its fields, columns and rule from `ir.model.data` without needing the code (verified on a pre-production copy).
- The borrowing-headroom rule (`excep_ar_borrowing_headroom`) is unchanged; it reads the request's own `budget_commitment_amount`, not the loan's.
