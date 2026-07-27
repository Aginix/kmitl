# KRIS Project Revision

Extension to [KRIS Project](../kris_project/CONTEXT.md) that adds the **Revision** (ฉบับแก้ไข) feature: take a snapshot of a project before scope/value changes so the original is preserved for reference while a fresh editable copy moves forward.

## Language

**Revision** (ฉบับแก้ไข):
A snapshot of a project taken before scope/value changes. Creating a revision archives the source (`active=False`), cancels its state (`state="cancel"` via `action_cancel`), copies installments, allocations **and receipts** into a new `draft` record numbered with a `-NN` suffix (`KRIS0005` → `KRIS0005-01`), and points the source's `current_revision_id` at the new record. On the new revision each receipt's `installment_id` and `allocation_ids.allocation_line_id` are remapped to the new revision's records (positional zip). Only `in_progress` or `cancel` projects offer the **สร้างฉบับแก้ไข** button; `done` projects are frozen.
_Avoid_: "version", "copy" — "copy" specifically refers to Odoo's built-in **Duplicate** action, which is a different mechanism (and must not drag `current_revision_id` or receipts along).

**Recalculate** (Recalculate button):
A non-destructive companion to **Apply Template**. After the user edits a revision's `project_value` (and therefore `maintenance_deduction_amount` shifts), each `allocation_line_ids` row's `estimated_amount` becomes stale. Recalculate re-derives `estimated_amount` for each line in place from the linked `allocation_template_id`'s percentages and the new `maintenance_deduction_amount`, skipping locked lines (`is_locked=True`) and lines whose `item_id` isn't in the template. Unlike Apply Template it never `unlink()`s rows, so `receipt_allocation_ids` (and therefore `actual_amount` / รับจริง carried from previous revisions) is preserved.
_Avoid_: "reset allocations" — Recalculate updates existing lines; Apply Template is the one that wipes and rebuilds.
