# Patch `Many2ManyBinaryField` in place instead of adding a new widget

We apply the drag-and-drop and Document-Type behaviour by `patch()`-ing
the standard `Many2ManyBinaryField` class and its OWL templates (via
`t-inherit`). All 12 Odoo core usages of `widget="many2many_binary"`
and all 17 in this repo pick up the enhancement automatically — no
widget rename, no per-consumer JS, no view edits.

Chosen over the earlier "custom widget name + JS factory per consumer"
route (ADR-0001) because consumers really want *"turn on document
classification for this model"* to be a couple of XML data records,
not a JS `register()` call plus a view attribute change. Scope lives
in a dedicated Mapping table (`ir.attachment.document.type.rel` — one
row per (model, doctype), with a `sequence`) so turning classification
on/off per model, and ordering the dropdown, are data, not code.

## Consequences

- Adding classification to a new model = one XML record in a data
  file; opening the widget is unchanged.
- Odoo core widget behaviour changes globally: every place with a
  `many2many_binary` now supports drag-and-drop. This is additive and
  documented.
- The patch depends on the stability of the standard template
  structure (`aria-atomic='true'` root, `attachment_preview` sub-
  template with its `caption small` / `o_attachment_delete` markers).
  Any breaking change to these on Odoo upgrade would require adjusting
  the `t-inherit` xpath expressions.
- The `document_type_id` column is added to `ir.attachment` by this
  module. Consumers must not re-declare it. Enforcing "must have
  doctype" is left to each consumer.
