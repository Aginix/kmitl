# Plan entry is a live-bound OWL grid over a sparse amount store

The plannable grid is large (Activity × Fund × Budget Line × 12 months) and the Template is edited centrally after units have started filling it — edits must reflect in every Plan Document **immediately**, and entry must be fast rather than row-by-row. So a Plan Document does **not** snapshot Template rows into stored lines.

Instead:
- A lightweight `budget.expense.plan` **header** per (ส่วนงาน × แหล่งเงิน × ปีงบ) holds state, ownership, access and chatter.
- Plan amounts are stored **sparsely**, keyed by (header, **Template row id**, month) — only filled cells exist.
- A custom **OWL client action** renders the grid live from the *current* Template and writes amounts; the Actual column is computed on the fly from budget consume.
- Headers are **push-generated** for the Required Departments (one draft per required ส่วนงาน) so central can track who has/has not filled — chosen over lazy-on-first-open for v1 to make compliance visible; cheap to switch since the header carries no snapshot.

## Considered options

- **Classic one2many snapshot lines** (each document copies the Template rows). Rejected: Template edits would not propagate; row-by-row entry is slow for a grid this size; and a standard editable list can't give the pivot UX asked for.
- **Full per-document snapshot** (freeze the grid at generation). Rejected: documents drift from the Template and the real-time requirement is lost.

## Consequences

- Amounts key to a **Template row id** (a persistent record, not a transient config line), so editing a row's Fund/Budget Line **re-labels** existing amounts (they follow the row) and adding a row shows blank cells.
- Removing a Template row that carries amounts **soft-hides** them (kept for audit, excluded from totals, restorable) — entered numbers are never silently dropped; central is warned before removing/editing a row that has data.
- A custom OWL grid is more work than standard views, and its consolidation/report surface must be built rather than inherited — accepted for the UX and the live binding.
- The same OWL surface can host both entry (แผน only) and comparison (แผน beside ผล); the printed/consolidated report is a separate rendering over the same computed data.
