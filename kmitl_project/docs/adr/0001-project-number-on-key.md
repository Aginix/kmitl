# `key` carries the Project Number, not yet the รหัสโครงการ

A `kmitl.project` needs a stable running number for identification and as its analytic-account `code`. We issue it from an `ir.sequence` (`kmitl.project`, prefix `PROJ/%(year_be)s/`, 4-digit, `no_gap`) and store it in the **existing `key` field**, rather than adding a new field. It is minted once, at the `draft→new` confirmation (alongside the analytic and the budget commitment), and is sticky — a later reset-to-draft never re-issues or clears it. The number is stamped with the project's **fiscal year** (the sequence is drawn on `account_fiscal_year_id.date_to`, not the confirmation calendar date), so it always reads as its ปีงบประมาณ; consequently `account_fiscal_year_id` is frozen once `key` exists (view + a server-side write guard).

The real **รหัสโครงการ** — the institutional project code issued at *approval* — is **deferred**. When it lands it will be a separate field; `key` is the running number only. The two are intentionally distinct (see CONTEXT.md » Project Number).

## Why

- Reusing `key` avoids a new field and any view churn: `key` was already displayed and already wired as the analytic `code` source and the `budget.commitment` `ref` — it was simply never populated. The previous fallback (`code = self.key or self.name`) therefore always resolved to the **project name**, which is the bug this fixes.
- Fiscal-year stamping (vs the `procurement_plan` calendar-date pattern) makes the number unambiguous for a government fiscal-year process and makes freezing the fiscal year meaningful: a project confirmed in Sept 2568 for FY2569 reads `PROJ/2569/...`, not `PROJ/2568/...`.

## Consequences

- `key` is overloaded until the approval-time รหัสโครงการ ships; the glossary flags this so the two are never conflated. Repurposing `key` later would require a migration — hence this record.
- The counter is a single global `no_gap` sequence; the fiscal year only stamps the prefix and does not reset the count (same as `procurement_plan`).
