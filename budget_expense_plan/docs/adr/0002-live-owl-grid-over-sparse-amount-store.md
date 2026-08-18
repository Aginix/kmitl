# Plan entry is a live-bound OWL grid over a sparse amount store

The plannable grid is large (Activity × Fund × Budget Line × 12 months) and the Template is edited centrally after units have started filling it — edits must reflect in every Plan Document **immediately**, and entry must be fast rather than row-by-row. So a Plan Document does **not** snapshot Template rows into stored lines.

Instead:
- A lightweight `budget.expense.plan` **header** per (ส่วนงาน × แหล่งเงิน × ปีงบ) holds state, ownership, access and chatter.
- Plan amounts are stored **sparsely**, keyed by the **dimension tuple** (header, Activity, Fund, Budget Line, month) — only filled cells exist (keying revised from a Template-row id to the tuple by ADR-0004).
- A custom **OWL client action** renders the grid live from the *current* Template and writes amounts; the Actual column is computed on the fly from budget consume.
- Headers are **push-generated** for the Required Departments (one draft per required ส่วนงาน) so central can track who has/has not filled — chosen over lazy-on-first-open for v1 to make compliance visible; cheap to switch since the header carries no snapshot.

## Considered options

- **Classic one2many snapshot lines** (each document copies the Template rows). Rejected: Template edits would not propagate; row-by-row entry is slow for a grid this size; and a standard editable list can't give the pivot UX asked for.
- **Full per-document snapshot** (freeze the grid at generation). Rejected: documents drift from the Template and the real-time requirement is lost.

## Consequences

- Amounts key to the **dimension tuple** (Activity, Fund, Budget Line, month) — not a stored row id (ADR-0004). This gives soft-hide for free: a row that leaves the grid (the ส่วนงาน de-selects an activity, or the Template drops a fund/budget line) keeps its amounts, hidden and excluded from grid totals, and they **reappear** on re-selection — entered numbers are never silently dropped.
- A custom OWL grid is more work than standard views, and its consolidation/report surface must be built rather than inherited — accepted for the UX and the live binding.
- The same OWL surface can host both entry (แผน only) and comparison (แผน beside ผล); the printed/consolidated report is a separate rendering over the same computed data.
- The grid opens on a **read-only overview** that sums every chosen activity by (fund, budget line); editing is done **one activity at a time** via tabs (rows grouped by fund). Overview aggregation and per-activity filtering are done client-side from a single payload, so no extra round-trip per tab.
