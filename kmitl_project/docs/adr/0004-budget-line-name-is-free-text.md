# Project Budget Plan line identity is free text; the catalog is optional

A **Project Budget Plan** line (`project.budget.line`) is identified by a
**free-text `name`** typed by the planner. Picking a catalog **Budget Item**
(`project.budget.item`) is an **optional** convenience that pre-fills that `name`
(and the line's `category_id` and reference unit/price). `budget_item_id` is
therefore **not required**; `name` is.

The ประเภทงบ classification (`project.budget.category`) is the structural axis —
seeded as a two-level tree (e.g. งบดำเนินงาน → ค่าใช้สอย). The expense catalog ships
**empty**; the former expense "items" (ค่าตอบแทน, ค่าใช้สอย, …) are now the ประเภทงบ
sub-categories, not catalog entries.

## Why

- Real project expenses are open-ended (e.g. "จ้างเหมาจัดงาน X", "ค่าอาหารว่างวันที่ 3").
  Forcing every line to match a curated catalog entry blocked planners, and regular
  users only have **read** access to the catalog (they cannot create entries), so a
  quick-create path would have failed for them and polluted shared master data.
- The government budget classification (ประเภทงบ → หมวด) is the part that must be
  standardised; the individual line description is not. So the classification lives
  in a controlled hierarchy while the line label is free text.
- The catalog is kept (optional) so managers can still offer common reusable items
  that pre-fill a line — hence `budget_item_id` stays, just non-mandatory.

## Consequences

- `name` is required at the row level; a picked item overwrites it (onchange), after
  which it stays freely editable. Confirmation validates amount, not the source of
  the name.
- An expense line's `category_id` is set **directly on the line** (an editable picker
  column, `optional="show"`), defaulted from the section's "add line" button, or
  copied from a picked item — so a free-text line can be categorised even with an
  empty catalog (no chicken-and-egg with the section headers).
- The OWL expense table groups purely on the category path (`category_parent_path` /
  `category_complete_name`), independent of `budget_item_id`, so free-text and
  catalog-backed lines nest identically.
- Each section offers **two** add buttons — **เพิ่มจากรายการ** (fill the line from the
  catalog picker) and **เพิ่มแบบพิมพ์เอง** (type a free-text name) — so free text is an
  *addition* to the catalog, never a replacement. Both create the same kind of line
  in that section; the catalog picker column stays visible for either path.
- Portal and the confirmation message show the line `name` (with the ประเภทงบ path as
  muted context on the portal), not the catalog `complete_name`.
- Possible follow-up: render every seeded ประเภทงบ as an always-present section (even
  empty) so lines are added purely via per-section buttons and the per-row category
  picker can be dropped. Deferred — needs the widget to load the category list.
