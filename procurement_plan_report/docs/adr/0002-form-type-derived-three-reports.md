# Form type is derived from the budget account; delivered as three separate reports over the full stack

The submission form comes in three government layouts. We **derive** which layout an item belongs to instead of storing it: **สิ่งก่อสร้าง** = `budget_account_id.is_asset == False`; **ครุภัณฑ์ (งวดเดียว)** = `is_asset == True` and ≤ 1 installment; **ครุภัณฑ์ (หลายงวด)** = `is_asset == True` and > 1 installment. The equipment-only "ประเภทครุภัณฑ์" column is just `budget_account_id.name`. Each layout is a **separate report — its own menu, OWL screen, and Excel workbook** (not one screen with tabs), and the whole thing is **one module** depending on the full workflow stack.

## Considered options

- **Stored `procurement_category` Selection** — explicit, but a redundant field users must keep in sync with the budget account that already encodes it (5411 = construction, 5412 = equipment, recursively via `is_asset`). Rejected as duplication.
- **One combined overview with tabs/sections** — matches "one report" framing, but the three layouts differ enough (columns, disbursement grain) that a split is cleaner to read and to export. Rejected in favour of three screens.
- **Bridge-module-per-layer** (report core + `_purchase` + `_disbursement`), the usual KMITL house style — over-engineered for a pure reporting concern where every target deployment already runs budget + พ.1. Rejected.

## Consequences

- `procurement_plan_report` depends on `procurement_plan_budget` (for `budget_account_id`/`is_asset`), `purchase_request_procurement_plan` (procurement method + พ.1 link), and `report_xlsx`. It is deliberately **not** installable on a bare `procurement_plan` — this form has no meaning without the budget + พ.1 workflow.
- The single-vs-multi split keys on installment **count** (`len(payment_ids) > 1`), so moving a plan between the two equipment reports needs no data change.
- A plan's smart button opens the screen for its own derived type, pre-scoped to its ปีงบ + หน่วยงาน. Only plans in `verified` / `in_progress` / `done` appear (draft/cancel excluded).
