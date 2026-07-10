# Web Attachment Classifier

Reusable OWL widget kit that lets consumer modules replace the standard
"attach a file" affordance with "attach a file **together with one
categorical value**" — a Document Type, an Attachment Type, a Fund Source,
etc. UI-only; the classifier field itself lives on `ir.attachment` in each
consumer module.

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
`registerAttachmentClassifierWidget(...)` in its own JS asset to bind a
widget name to a specific Classifier Field. First consumers:
`kris_project` and `purchase_request_kmitl`.
_Avoid_: user (too generic), client (implies UI code, not a whole module).

**Factory (registration API)**:
The JS function that consumers call to produce a concrete widget
subclass. Named `registerAttachmentClassifierWidget`. See
[ADR-0001](./docs/adr/0001-factory-not-xml-options.md) for why this is
a JS factory instead of XML `options`.

**External Attachment**:
An `ir.attachment` linked to the same `(res_model, res_id)` as the
widget's One2many but *created outside the widget* — typically by mail
chatter, Odoo report generation, or admin action. These render in the
widget list with a "-" placeholder for the classifier; the user can click
the placeholder to set a value (see "Post-hoc edit" below).

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
- **Post-hoc edit via pencil button.** Each attachment row shows a
  pencil icon (before the trash icon) while the field is editable —
  clicking opens the dialog in edit mode with an optional file picker
  plus the classifier dropdown pre-populated. Save issues one
  `ir.attachment.write` covering both the new file (base64) and the
  classifier, so the `ir.attachment.id` is preserved (no dangling
  reference in chatter or downstream logs). The badge itself is
  display-only — all edits go through the pencil button.
- **File size ceiling for replace.** File replacement writes `datas` as
  base64 via ORM. Effective ceiling ≈ `web.max_upload_size` ÷ 1.33
  (Odoo 16 default ~128 MB → ~90 MB usable). Files larger than that
  should still use delete + Attach — this is a documented ceiling, not
  an error the UI shows.
- **Multi-file upload (add only).** The Add dialog's file input accepts
  multiple files and applies the *same* classifier to all of them.
  Uploads are best-effort — a failure on one file surfaces as a
  notification for that file, and successful uploads are kept. The
  Edit dialog's file input is single-select (replace is 1:1).

## Manual verification checklist

Test end-to-end after touching the widget, the factory, or a consumer's
widget registration:

1. Install `web_attachment_classifier` + upgrade the consumer module.
2. Open a form that uses the widget → tab shows a card list of existing
   attachments with a badge per file (or "-" for unclassified).
3. Click **Attach** → dialog opens with a file picker (multi-select
   allowed) and a dropdown labelled with the consumer's
   `classifierLabel`. If the widget was registered with
   `classifierRequired: true`, an asterisk shows next to the label and
   Save must reject an empty selection.
4. Select two files + a classifier → **Save** → both attachment rows
   appear with the same badge.
5. Reload the form → badges still show. This proves `fieldsToFetch` is
   wired for the classifier field.
6. **Edit classifier only.** Click the pencil button on a row → dialog
   opens in edit mode with an empty file picker and the classifier
   dropdown pre-populated → change the value → **Save** → badge updates
   in place. Confirm via Settings > Technical > Attachments that
   `ir.attachment.id` is unchanged.
7. **Replace file only.** Click pencil → pick a new file of a different
   type (e.g. `.png` in place of `.pdf`) → leave the classifier as-is
   → **Save** → the row's filename/extension update while the badge
   stays. Confirm `ir.attachment.id` is unchanged.
8. **Replace file + classifier.** Click pencil → pick a new file *and*
   change the dropdown → **Save** → both the file and the badge
   update; `ir.attachment.id` still unchanged.
9. **External attachment.** Upload an attachment via mail chatter → it
   appears in the widget list with a "-" badge (see
   [External Attachment](#language)) and a pencil button → click pencil
   → set a classifier → **Save** → badge updates.
10. **Badge is display-only.** Hovering the badge does not change the
    cursor; clicking it does nothing.
11. **Register a second widget** in another consumer with a different
    `classifierField` → both work on the same form without cross-talk
    (validates that factory-per-consumer subclassing keeps
    `fieldsToFetch` isolated).
