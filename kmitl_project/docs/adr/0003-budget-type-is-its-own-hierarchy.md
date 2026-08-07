# ประเภทงบ is its own hierarchical model, Budget Items are flat

The **ประเภทงบ** categories (งบบุคลากร / งบดำเนินงาน / งบอุดหนุน) are modelled as their
own hierarchical master-data model **`project.budget.category`** (`_parent_store`,
up to three levels in practice). A **Budget Item** (`project.budget.item`) is now
**flat** and points at one category via `category_id`; a **Project Budget Plan** line
(`project.budget.line`) carries the chosen item's category as `category_id`, plus two
stored-related fields — `category_complete_name` and `category_parent_path` — that
expose the category's label and materialised path.

Previously ประเภทงบ was not a separate model: the categories were the *root records*
of the `project.budget.item` hierarchy, and a line grouped by a single-level
`budget_category_id` pointing at that root.

## Why

- **ประเภทงบ is real master data, not a special row of the item catalog.** Giving it
  its own model lets it carry its own hierarchy (a category can have sub-categories),
  its own settings page, tracking, archive and delete-guard, without those concerns
  bleeding into the item catalog.
- **Items are leaves, not containers.** Once categories own the hierarchy, an item no
  longer needs `parent_id`/`child_ids`; it just declares which ประเภทงบ it belongs to.
  An item may attach at **any** category level (not only leaves), matching how the
  seed files them directly under a top-level category today.
- **The expense table needs the full ancestor path, not a single level.** Exposing
  `category_parent_path` (ids) + `category_complete_name` (labels) on the line lets the
  OWL widget build nested section headers **client-side** — one per level, each with a
  roll-up subtotal and an "add line" action that pre-fills that level's category — with
  no extra RPC.

## Consequences

- **Two axes not to conflate** (already in CONTEXT.md » ประเภทงบ): `category_id` (the
  ประเภทงบ hierarchy, expense-only) vs `budget_type` (the income-vs-expense flag).
  Income lines/items always have `category_id = False`.
- The widget reconstructs the ancestry by zipping `category_parent_path` with
  `category_complete_name.split(" / ")`. This assumes **category names contain no
  " / "**. They are curated master data, so this holds; if it ever must, replace the
  string split with an explicit id/label payload on the line.
- `category_parent_path` is a **stored** related field so the line list can also order
  by it server-side (portal, non-widget contexts) and so onchange returns it to the
  editable list immediately when the item — hence category — changes.
- Deleting a category is blocked while it has sub-categories, items, or plan lines
  (archive instead), mirroring the item's own delete guard.
- This is an additive structural change on an as-yet-unmerged feature (PR #990); no
  data migration ships. A previously-seeded UAT database should be re-seeded on
  upgrade (the old `expense_root_*` item roots are dropped; the new `category_*`
  records and flat items take their place).
