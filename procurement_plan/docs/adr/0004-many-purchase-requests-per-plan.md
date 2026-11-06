# A plan may be realised through many purchase requests

A plan may raise **many** purchase requests (พ.1), not one at a time. One procurement line in the annual plan is often bought in several lots, and a rejected or cancelled พ.1 must not lock the plan. The cap is **blocking**: Σ `estimated_cost` of the plan's purchase requests that are not rejected or cancelled must stay ≤ the plan's **Plan Budget**; "สร้างใบขอซื้อ" stays available in `in_progress` while that headroom is above zero. Mirrors KMITL Project (kmitl_project, many PRs capped at the commitment). Decision D4 of the 2026-10-24 review.

Supersedes [budget ADR-0006](../../../budget/docs/adr/0006-plan-driven-pr-created-from-plan.md) ("one active PR"). Its create-from-plan rule stays: plan-driven purchase requests are still created from the plan, never by picking a plan on the PR form.

## Consequences

- A `cancelled` purchase request no longer counts as active (it did, by mistake, under the one-active rule).
- A rejected purchase request no longer bounces the plan back to `verified`; the plan stays `in_progress` and the headroom simply returns.
- The plan moves to `in_progress` only through its first purchase request — the manual "ดำเนินการ" button goes away.
