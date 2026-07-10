# Web Attachment Classifier

Reusable OWL widget kit that lets consumer modules replace the standard
"attach a file" affordance with "attach a file **together with one
categorical value**" — a Document Type, an Attachment Type, a Fund Source,
etc. UI-only; the classifier field itself lives on `ir.attachment` in each
consumer module.

> Historical note: this context was initially scaffolded under the name
> "web_attachment_metadata". The domain term is **classifier**, not
> metadata — a physical rename of the module directory is a pending
> follow-up.

## Language

**Attachment Classifier**:
A *single* categorical value attached to an `ir.attachment` alongside the
file itself — either a Many2one to a taxonomy model (e.g.
`kris.project.document.type`) or a Selection field (e.g.
`ir.attachment.attachment_type`). One classifier per widget instance.
_Avoid_: metadata (too broad — a classifier is *one* categorical
dimension, not an open bag of fields), tag (implies multi-value), category
(overloaded in Odoo).

**Classifier Value**:
The value the user selects — for Many2one, the target record; for
Selection, the raw string value. Stored on `ir.attachment.<consumer-field>`.
Optional at upload time by default; consumers can require it via factory
config.

**Classifier Field**:
The Python field on `ir.attachment` that stores the Classifier Value.
Declared by the *consumer* module, never by this module. Naming
convention: prefix with the consumer's short name to avoid cross-consumer
collisions (e.g. `kris_document_type_id`, `pr_attachment_type`) — this is
a convention, not enforced.

**Consumer Module**:
Any Odoo module that `depends` on this kit and calls
`registerAttachmentMetadataWidget(...)` in its own JS asset to bind a
widget name to a specific Classifier Field. First consumers:
`kris_project` and `purchase_request_kmitl`.
_Avoid_: user (too generic), client (implies UI code, not a whole module).

**Factory (registration API)**:
The JS function that consumers call to produce a concrete widget
subclass. Named `registerAttachmentMetadataWidget` (kept for now — will
rename with the module). See [ADR-0001](./docs/adr/0001-factory-not-xml-options.md)
for why this is a JS factory instead of XML `options`.

**External Attachment**:
An `ir.attachment` linked to the same `(res_model, res_id)` as the
widget's One2many but *created outside the widget* — typically by mail
chatter, Odoo report generation, or admin action. These render in the
widget list with a "-" placeholder for the classifier and stay editable
after the fact (see "Post-hoc edit" below).

## Rules of the game

- **Single dimension only.** One widget = one Classifier Field. Extension
  to *N* classifiers per widget is possible but not implemented — would
  require changing the factory signature to accept a list and reworking
  the dialog to render N dropdowns.
- **UI kit, no data model.** This module *never* touches `ir.attachment`.
  All classifier fields are owned by consumer modules. As a result, the
  module is `category = "Hidden"` — installing it standalone provides no
  visible feature.
- **Selection tuples are consumer-declared.** For Selection classifiers,
  the consumer either passes the `[[value,label],...]` tuples to the
  factory (recommended, matches the Python side) or lets the widget look
  them up via `fields_get` at render time (fallback for Selection whose
  values are not stable at JS-load time).
- **Classifier is set at upload time only** — until post-hoc edit lands
  (see backlog), the badge shown next to a file is read-only. Missing a
  value is not an error; the badge just renders as "-".

## Manual verification checklist

Test end-to-end after touching the widget, the factory, or a consumer's
widget registration:

1. Install `web_attachment_metadata` + upgrade the consumer module
2. Open a form that uses the widget → tab shows a card list of existing
   attachments with a badge per file (or "-" for unclassified)
3. Click **Attach** → dialog opens with a file picker and a dropdown
   labelled with the consumer's `metadataLabel`
4. Select file + classifier → **Save** → new attachment row appears with
   the correct badge
5. Reload the form → badge still shows the classifier label (proves
   `fieldsToFetch` for that field is wired)
6. Upload an attachment via mail chatter → it appears in the widget list
   with a "-" badge (see [External Attachment](#language))
7. Register a *second* widget in another consumer with a different
   `metadataField` → both work on the same form without cross-talk
   (validates that factory-per-consumer subclassing keeps `fieldsToFetch`
   isolated)

## Backlog (design agreed, not yet implemented)

Locked in during the review that produced this document but deliberately
out of scope for PR #969:

- **Rename to `web_attachment_classifier`** — module directory + factory
  function + all JS/XML identifiers. Follow-up PR.
- **`required: true/false`** — factory option to force a value at upload
  time. Consumers that previously had `required="1"` in a tree row
  (kris_project, purchase_request_kmitl) will opt in.
- **Post-hoc edit** — click the badge → popover to change the classifier
  via `orm.write` (v1: `ir.attachment.write` from the client). Prefer
  this over "delete + re-upload" to preserve the attachment record and
  its audit trail.
- **Multi-file upload with shared classifier** — dialog accepts
  `multiple` files but exposes one dropdown; loops upload + write with
  best-effort semantics (per-file notification on failure, no rollback).
