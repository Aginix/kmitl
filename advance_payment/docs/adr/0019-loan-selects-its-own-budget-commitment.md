# A loan may select its own budget commitment, not only inherit one

Status: accepted (2026-09) — supersedes ADR-0008's read-only-snapshot decision

## Context & Decision

ADR-0008 made `budget_commitment_id` a read-only field, filled only by copying it off the source document (`purchase.request` / `approval.request`) when `reference` is picked. A loan with no source document was simply left with no commitment — "a separate policy question" the ADR left open.

`budget_commitment_id` now drops `readonly=True` and gains `domain=[("state", "in", ["reserved", "partial"])]`: while the loan is in `draft`, the officer may pick any open ใบจองงบประมาณ directly, the same way `agx_approval`'s `reservation_commitment_id` already lets a budget officer pick one. A new `@api.onchange("budget_commitment_id")` sets `analytic_distribution` from the chosen commitment, which cascades through the existing `_compute_analytic_ids` compute so the four dimension pickers (`department_analytic_id`, `source_analytic_id`, `fund_analytic_id`, `activity_analytic_id`) fill from it — overriding whatever `reference` had supplied. Picking a different commitment later (still in draft) overrides again.

The view field switches to `widget="budget_commitment_info"` (from `budget`, already a dependency) so the officer sees the commitment's code/dimensions/amounts card, not a bare Many2one. `budget_commitment_autocomplete`'s richer multi-line dropdown — the same widget name, replacing this one's registry entry when installed — is deliberately left out of `depends` for now; wiring it in is its own bridge-module change, not part of this ADR.

## Why

- **The office wants the officer in the loop, not just the source document.** A loan is not always backed by a PR/AR with its own commitment already chosen correctly for this specific disbursement; the officer needs the ability to point the loan at the right ใบจองงบประมาณ themselves.
- **Nothing about *why* the field is a snapshot changes.** ADR-0008's reasoning — a loan never reserves its own commitment (double-reservation risk), the source document stays free to release or re-point its own commitment afterwards, only the commitment itself needs to travel — is unaffected. Only *who* may set the snapshot, and *when*, changes: now either the source document (via `_apply_vals_from_reference`) or the officer (via the picker), and only up to `draft`.
- **`store=False` on the four pickers already made this cheap.** ADR-0009 already computes them off `analytic_distribution` rather than storing them independently, so re-pointing `budget_commitment_id` and re-deriving the dimensions from it needed no new plumbing beyond the one onchange.
- Restricting the picker's domain to `reserved`/`partial` keeps the officer from pointing a loan at a commitment that cannot actually fund it (`draft`, `done`, or `cancel`).

## Consequences

- **The dimension `attrs` stay gated on `is_locked_by_reference`, not on the commitment picker.** A reference-backed loan still shows the four pickers as read-only in the UI even after this change — the officer overrides the *commitment*, and the dimensions ride along underneath, computed and correct, even while displayed read-only.
- **Source bridges are unchanged.** `purchase_request_advance_payment` / `agx_approval_advance_payment` still prefill `budget_commitment_id` and `analytic_distribution` the same way; the officer may simply override the prefill before submitting.
- Consumption (ตัดงบ) is still parked exactly as ADR-0008/0009 describe — this ADR only changes who may point the carrier, not whether anything consumes.
