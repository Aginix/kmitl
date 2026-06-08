# Plan-driven purchase requests are created from the plan, one active at a time

A purchase request that spends a procurement plan is **created from the plan** (a "สร้าง PR" action on `procurement.plan`), not by ticking `use_procurement_plan` and picking a plan on the PR form. The action prefills budget account, analytic distribution, fiscal year, procurement method and title, links the plan's **existing** `budget.commitment`, and moves the plan to `in_progress`. A plan allows **at most one active PR** (state ≠ `rejected`); if that PR is rejected the plan returns to `ready` so a new one can be created.

The "สร้าง PR" button shows while the plan is `new` or `ready` (and has no active PR); pressing it on a `new` plan raises a `UserError` telling the officer to complete the ETA fields and press *Ready* first — the ETA gate.

Refines the discriminator in [ADR-0004](./0004-procurement-plan-shared-commitment.md): the `use_procurement_plan` flag is **kept** as the internal discriminator — the purchase order, the make-PO wizard, the `purchase.request.approval` model and the over-budget exception rule all read it — but the user can no longer set it. The in-form checkbox + plan dropdown are removed; the flag and `procurement_plan_id` are populated only by the create-from-plan action. The shared-commitment draw-down model itself is unchanged.

## Why

- One plan = one procurement = one PR. The in-form selector let many PRs point at one plan, and let users pick a plan that was not yet reserved (the dropdown filtered `state='new'` while the commitment only existed from `ready` — a live inconsistency).
- Creating from the plan guarantees the PR is backed by an existing reservation and carries the plan's dimensions; the existing prefill onchange now fires from the create-from-plan context defaults instead of a manual toggle.

## Consequences

- The in-form selector is removed: the `use_procurement_plan` checkbox and the `procurement_plan_id` dropdown no longer appear on the PR form. Both fields stay on the form as invisible so the prefill onchange still fires from the create-from-plan context defaults.
- `use_procurement_plan` is **retained** as the cross-module discriminator (purchase order, make-PO wizard, `purchase.request.approval`, over-budget exception rule), set automatically by the create-from-plan action.
- Budget fields (budget account + analytic dimensions) stay **read-only** on a plan-driven PR via the existing `is_budget_editable=False` lock (keyed on `use_procurement_plan`), unchanged.
- Plan-driven PRs reuse `action_reserve_budget` only to advance `to_verify → to_approve`; its plan branch links the existing reservation and never creates a second commitment (see the terminology note in `procurement_plan/CONTEXT.md`).
- A rejected plan PR detaches from (never cancels) the shared reservation and bounces the plan `in_progress → ready`; full consumption auto-closes the plan to `done`.
