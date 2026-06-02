# Plan-driven purchase requests are created from the plan, one active at a time

A purchase request that spends a procurement plan is **created from the plan** (a "สร้าง PR" action on `procurement.plan`), not by ticking `use_procurement_plan` and picking a plan on the PR form. The action prefills budget account, analytic distribution, fiscal year, procurement method and title, links the plan's **existing** `budget.commitment`, and moves the plan to `in_progress`. A plan allows **at most one active PR** (state ≠ `rejected`); if that PR is rejected the plan returns to `ready` so a new one can be created.

The "สร้าง PR" button shows while the plan is `new` or `ready` (and has no active PR); pressing it on a `new` plan raises a `UserError` telling the officer to complete the ETA fields and press *Ready* first — the ETA gate.

Supersedes the discriminator in [ADR-0004](./0004-procurement-plan-shared-commitment.md): the link is no longer the `use_procurement_plan` flag on the PR but the create-from-plan action. The shared-commitment draw-down model itself is unchanged.

## Why

- One plan = one procurement = one PR. The in-form selector let many PRs point at one plan, and let users pick a plan that was not yet reserved (the dropdown filtered `state='new'` while the commitment only existed from `ready` — a live inconsistency).
- Creating from the plan guarantees the PR is backed by an existing reservation and carries the plan's dimensions, letting us drop the onchange prefill.

## Consequences

- `use_procurement_plan`, the in-form `procurement_plan_id` selector and `_onchange_procurement_plan_id` are removed.
- Budget fields (budget account + analytic dimensions) stay **read-only** on a plan-driven PR so they cannot diverge from the plan; the existing `is_budget_editable=False` lock is kept, re-keyed from `use_procurement_plan` to `procurement_plan_id`.
- Plan-driven PRs do not call `action_reserve_budget` (they never reserve — see the terminology note in `procurement_plan/CONTEXT.md`); non-plan PRs keep their own per-document reserve flow unchanged.
- A rejected PR must bounce the plan `in_progress → ready`; full consumption auto-closes the plan to `done`.
