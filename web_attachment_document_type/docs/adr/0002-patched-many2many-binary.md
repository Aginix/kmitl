# Patch `Many2ManyBinaryField` in place instead of adding a new widget

We apply the drag-and-drop and Document-Type behaviour by `patch()`-ing the standard
`Many2ManyBinaryField` class and its OWL templates (via `t-inherit`). All 12 Odoo core
usages of `widget="many2many_binary"` and all 17 in this repo pick up the enhancement
automatically — no widget rename, no per-consumer JS, no view edits.

Chosen after rejecting two alternatives:

1. **A per-consumer JS factory** (each module calls
   `registerAttachmentClassifierWidget({widgetName, classifierField, ...})` and
   references its own `widgetName` in XML) — rejected because consumers really want
   _"turn on document classification for this model"_ to be a couple of XML data
   records, not a JS `register()` call plus a view attribute change.
2. **A single generic widget configured via XML `options`** — rejected because
   `Many2ManyBinaryField.fieldsToFetch` is a static per-class contract; per-instance
   `options` can't feed into it without breaking reactive badge display.

Scope lives in a dedicated Mapping table (`ir.attachment.document.type.rel` — one row
per (model, doctype), with a `sequence`) so turning classification on/off per model, and
ordering the dropdown, are data, not code.

## Consequences

- Adding classification to a new model = one XML record in a data file; opening the
  widget is unchanged.
- Odoo core widget behaviour changes globally: every place with a `many2many_binary` now
  supports drag-and-drop. This is additive and documented.
- The patch depends on the stability of the standard template structure
  (`aria-atomic='true'` root, `attachment_preview` sub- template with its
  `caption small` / `o_attachment_delete` markers). Any breaking change to these on Odoo
  upgrade would require adjusting the `t-inherit` xpath expressions.
- The `document_type_id` column is added to `ir.attachment` by this module. Consumers
  must not re-declare it. Enforcing "must have doctype" is left to each consumer.
- `getUrl` and the `download` template attribute are patched globally to serve
  attachments inline (`?download=false` + `target="_blank"`). Every `many2many_binary`
  widget in the system is affected, not only models with doctype mappings. Right-click →
  _Save link as…_ still gives a download.
