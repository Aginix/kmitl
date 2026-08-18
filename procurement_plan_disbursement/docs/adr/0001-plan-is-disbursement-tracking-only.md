# Procurement plan tracks disbursement; it does not author it

## Context

A procurement plan reserves one shared `budget.commitment`, and the disbursement
requests (ใบขอเบิก) that ultimately consume it already exist — they are created
and operated on the **purchase order** (`purchase_order_disbursement`), which
holds the vendor and the lines. In practice users do *everything* on the PO; the
plan exists to **control the budget and track results**. What was missing was any
way to see, from the plan, how much of each planned installment (งวด) had
actually been disbursed.

## Decision

Add a **tracking-only** bridge. Each งวด (`procurement.plan.payment`) carries a
manual `disbursement_request_id` (1 งวด → 1 DR), authored on the plan's งวด line;
the plan rolls up "planned งวด vs actual disbursed" and a DR smart button. Actual
= the linked DR's consumed budget, counted only once the DR is `approved`.

We deliberately **do not** let a plan or a งวด create a disbursement request
(no plan-side "create DR" button). That path was considered and rejected: a plan
names no vendor (the payee is only known at PO time) and a DR requires a payee per
line, so a plan-authored DR would fight the operational reality that everything is
done on the PO.

## Consequences

- No changes to the `disbursement.request` schema — the link lives on the งวด.
- The งวด→DR link is manual (the PO does not know about งวด), and intentionally
  **not** guarded by a uniqueness constraint — kept loose. The picker is
  domain-filtered to DRs drawing this plan's reservation, which is the only guard.
- The budget draw-down itself is unchanged: DRs still obligate+consume the plan's
  shared commitment through the PO chain (budget ADR-0004); this bridge only makes
  that legible on the plan, per งวด.
