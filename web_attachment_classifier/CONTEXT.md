# Web Attachment Classifier

Odoo web enhancement that adds two things to the standard
`many2many_binary` attachment widget:

1. **Drag & drop** file upload — always on, for every place in Odoo that
   uses `many2many_binary`.
2. **Document Type classification** — an optional Many2one on
   `ir.attachment` picking from a shared taxonomy (`ir.attachment.document.type`)
   whose values are scoped per parent model via a `res_model_ids` link.
   The classifier UI (badge + pencil button) shows up only on forms whose
   `res_model` has at least one doctype mapped to it.

There is no custom widget name to remember and no per-consumer JS. A
consumer module that wants classification just declares one or more
`ir.attachment.document.type` records via XML data and points their
`res_model_ids` at whatever parent models it owns.

## Language

**Document Type**:
A record in `ir.attachment.document.type`. The taxonomy of possible
"kinds" of attachment (Contract, Receipt, TOR, etc.) that live *anywhere*
in Odoo. Each type declares which parent models it applies to via
`res_model_ids`.
_Avoid_: classifier (implementation-level jargon), metadata (too broad),
category (overloaded in Odoo), attachment type (was the old Selection
field name — now migrated away).

**Scope (of a Document Type)**:
The set of parent models a doctype is offered on, stored in
`res_model_ids` (Many2many to `ir.model`). A doctype is *visible* on a
form's attachment widget iff the form's `res_model` is in this set.
Doctypes with an empty scope are hidden everywhere by design (management
records only).

**Attached-to Model** (or *parent model*):
The `res_model` of an `ir.attachment` row — the model of the record the
file is attached to (e.g., `kris.project`, `purchase.request`,
`account.move`).

**Base Widget** vs **Patched Widget**:
Base = the stock `Many2ManyBinaryField` from
`@web/views/fields/many2many_binary/`. Patched = the same class after
`web_attachment_classifier` has applied its `patch()` — everywhere in
Odoo that uses `widget="many2many_binary"` sees the patched behaviour.

**Consumer Module**:
Any Odoo module that adds one or more `ir.attachment.document.type`
records via a data XML file and points their `res_model_ids` at its own
models. Consumers hold no Python or JS related to the widget. First
consumers: `kris_project` and `purchase_request_kmitl`.

## Rules of the game

- **Doctype is always optional.** `ir.attachment.document_type_id` is
  declared `required=False` at base. Files coming in through any path
  (widget Attach button, drag & drop, mail chatter, API, import) are
  accepted with `document_type_id = NULL`. The badge displays "-" for
  those, and the user can set the value later via the pencil button.
- **Business rule "must have doctype" is a consumer concern.** If a
  workflow needs every attachment classified before a state transition
  (e.g. `kris.project.action_confirm`), the consumer writes an
  `@api.constrains` or a check in the transition method that raises
  `UserError` when `attachment_ids.filtered(lambda a: not a.document_type_id)`
  is non-empty. Base does not enforce.
- **Scope is data.** Adding a new doctype to a new parent model = one
  XML record in a data file. No JS, no widget re-registration, no view
  edits. The dropdown/badge/pencil appear automatically on that model's
  form.
- **UI is conditional.** A form whose `res_model` has zero doctypes
  mapped to it renders the widget unchanged from Odoo standard — no
  badge, no pencil, no dropdown. It does still get drag & drop
  (unconditional).
- **Post-hoc edit via pencil button.** Each attachment row shows a
  pencil icon (before the trash icon) when doctypes exist for the
  parent model. Clicking it opens a small dialog with a single dropdown
  pre-populated. Save writes `document_type_id` via `orm.write`; Cancel
  closes. The attachment record itself and its id are preserved
  through-out.
- **Drag & drop is always on.** All 12 Odoo core usages of
  `many2many_binary` (mail composer, hr leaves, account invoice send,
  survey, etc.) and 17 in this repo (disbursement, advance_payment,
  agx_approval, …) get drag & drop for free — pure UX enhancement, no
  behavioural change.
- **Attach button behaviour is unchanged.** Clicking Attach still opens
  the OS file picker via Odoo's `FileInput` component and uploads via
  `/web/binary/upload_attachment`. The doctype is set (or left empty)
  post-upload via the pencil button.
- **`document_type_id` is fetched reactively.** Added to
  `Many2ManyBinaryField.fieldsToFetch` at patch time, so the badge
  updates immediately when a user edits it — no full-form reload
  needed.

## Manual verification checklist

Test end-to-end after touching the patch or the taxonomy model:

1. Install `web_attachment_classifier`, upgrade `kris_project` and
   `purchase_request_kmitl` so migrations run.
2. Migration lands cleanly (log has "remapped N attachments" lines for
   old doctype rows; legacy `kris_project_document_type` table dropped;
   `ir_attachment.attachment_type` column dropped).
3. Open a `kris.project` form → attachment tab uses the standard
   `many2many_binary`:
   - Drag a file over the card list → dashed outline overlay "Drop
     files to attach" appears → release → file uploads → row appears
     with a pencil icon and a "-" badge.
   - Click pencil → dialog with a Document Type dropdown showing
     kris_project's doctypes (Contract / Purchase / Receipt) → pick a
     value → Save → badge updates.
4. Open a `purchase.request` form → same behaviour but the dropdown
   lists TOR / Quotation / Etc.
5. Open a vendor bill (`account.move`) or any other form with
   `many2many_binary` and no doctypes mapped → drag & drop still works,
   but there is **no** badge, **no** pencil, **no** dropdown — widget
   looks exactly like Odoo standard.
6. Reload a form after tagging → badges still show. This confirms
   `document_type_id` is in `fieldsToFetch`.
7. Settings > Technical > Attachment Document Types → tree/form UI
   works; create a doctype with `res_model_ids = [purchase.order]` →
   open a PO form → pencil + dropdown appear immediately for the new
   type, no JS reload.
8. Historical attachments (created before the migration) still show
   their correct badges: the migration mapped their old
   `kris.project.document.type` id / `attachment_type` Selection value
   to the new `ir.attachment.document.type` records by NAME/value
   respectively.
9. Chatter D&D bug (see commit `97af33e`) still works: dragging over a
   form with a chatter and dropping on the attachment widget does not
   leave the chatter drop overlay stuck.
10. Upload via mail chatter → attachment appears in the widget list
    with a "-" badge → pencil to set doctype.
11. Consumer constraint enforcement: if `kris.project.action_confirm`
    is wired to check `attachment_ids` doctypes, confirming a project
    that has an unclassified attachment raises `UserError` — implement
    this only where the workflow actually needs it, not by default.
