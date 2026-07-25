# Standalone budget reservation, picked and drawn down by consuming documents

A `budget.commitment` can now be created **directly** as a first-class ใบจองงบประมาณ (Budget Reservation) — reserved up front (`draft → reserved` via a "จองงบประมาณ" action; a `budget_user` may reserve immediately, no tier.validation) with **no originating source document** — generalising the shared-commitment pattern that previously only a `procurement.plan` or `kmitl.project` could own (ADR-0004, ADR-0007). Consuming documents (`purchase.request` พ.1 and `approval.request`) gain a **draw-down mode**: selecting an existing commitment (`budget_commitment_id`) makes them link-and-obligate/consume against it instead of reserving their own — **the presence of a picked commitment IS the discriminator, no new flag**. This inverts the old "select dimensions → reserve" flow into an optional "reserve first → pick up later," so a unit can spend a reservation without jumping into the plan/project modules to create the พ.1.

## Considered Options

- **Model a separate "budget support request" parent** that owns the commitment — rejected: reintroduces the parent model the standalone concept was meant to remove; the reservation slip itself is the artifact, and any future request document can *feed* its creation without being its structural parent.
- **Limit the picker to standalone slips only** — rejected: plan/project พ.1 would still require module-hopping, missing the point of the feature.

## Consequences

- The capability lives on the shared `budget.commitment.mixin`, so `purchase.request` and `approval.request` behave identically (both are named in the original problem as select-then-reserve implementations).
- A drawn document **never re-reserves** and inherits the commitment's `analytic_distribution` + fiscal year **locked** (same server-side lock as project พ.1, ADR-0007), so spend can never diverge from the reservation.
- **Cardinality is preserved per source**: plan keeps one-active-PR (ADR-0006 — the picker excludes plan commitments that already have an active PR); project and **standalone** allow many drawing documents, capped at the commitment amount, with the ledger `_check_commitment_limits` as the backstop. The picker is a *new entry point*, not a change to existing invariants.
- **Lifecycle stays with the reservation's owner**: cancel (keep-if-touched, per the plan/project `_release` rule — a touched commitment is kept for audit, never stranded) and return-unused (คืนจอง, ADR-0009) are owner actions; a beneficiary spends but does not cancel/return. Draw-down itself is open to anyone who can *see* the slip (KISS). `operating_unit_id` and `beneficiary_operating_unit_id` are editable only in `draft`.
- **Phasing**: phase 1 exposes `budget_commitment_id` as a filtered dropdown (`state in (reserved, partial)`, `available_to_obligate > 0`, matching fiscal year, visible to the user); phase 2 unifies selection into the existing reservation picker **widget**, where one "เลือก/จองงบประมาณ" action lets the user either pick an existing slip or fall through to the reserve-new flow.
- Cross-OU access and accounting of a picked slip are covered by [ADR-0011](./0011-cross-ou-reservation-beneficiary-unit.md).
