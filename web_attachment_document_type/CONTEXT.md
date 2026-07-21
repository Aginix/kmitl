# Web Attachment Document Type

Odoo web enhancement that adds two things to the standard `many2many_binary` attachment
widget:

1. **Drag & drop** file upload — always on, for every place in Odoo that uses
   `many2many_binary`.
2. **Document Type classification** — an optional Many2one on `ir.attachment` picking
   from a shared taxonomy (`ir.attachment.document.type`). Which doctypes appear on
   which forms is configured per model in a Mapping table
   (`ir.attachment.document.type.rel`) that also holds the display `sequence`. The
   doctype UI (dropdown + badge) shows up only on forms whose `res_model` has at least
   one Mapping.

There is no custom widget name to remember and no per-consumer JS. A consumer module
that wants classification ships two kinds of data XML records:
`ir.attachment.document.type` (the doctype names) and `ir.attachment.document.type.rel`
(the (model, doctype, sequence) mappings).

## Language

**Document Type**: A record in `ir.attachment.document.type` — the master name for a
"kind" of attachment (Contract, Receipt, TOR, etc.). Holds only its `name` and `active`
flag; scope and ordering are on the Mappings that point to it, not on the doctype
itself. _Avoid_: classifier (implementation-level jargon), metadata (too broad),
category (overloaded in Odoo), attachment type (was the old Selection field name — now
migrated away).

**Model Config**: A row in `ir.attachment.document.type.config` — one per parent model
that participates in doctype classification. Holds `res_model_id` and the ordered
`line_ids` (see Mapping). Uniqueness is enforced so a model has at most one Config. This
is what users create/edit from Settings — "New" makes a Config, not a new `ir.model`, so
the tree can safely use `create="true"` without Studio-style side effects.

**Mapping**: A line inside a Config (row in `ir.attachment.document.type.rel`) — the
pairing of a `Document Type` with a `sequence`, scoped to the Config's model via
`config_id`. There is at most one Mapping per (config, doctype) pair (SQL unique). A
doctype may appear in zero or more Configs; a Config may hold zero or more Mappings.
_Avoid_: link (too generic), assignment (implies workflow), scope (now derived from
Configs + Mappings rather than a field on the doctype).

**Scope (of a Document Type)**: The set of Models a doctype is offered on, derived from
its inbound Mappings. Not a stored field — read via the widget's query on the Mapping
table filtered by `res_model_name`.

**Attached-to Model** (or _parent model_): The `res_model` of an `ir.attachment` row —
the model of the record the file is attached to (e.g., `kris.project`,
`purchase.request`, `account.move`).

**Base Widget** vs **Patched Widget**: Base = the stock `Many2ManyBinaryField` from
`@web/views/fields/many2many_binary/`. Patched = the same class after
`web_attachment_document_type` has applied its `patch()` — everywhere in Odoo that uses
`widget="many2many_binary"` sees the patched behaviour.

**Consumer Module**: Any Odoo module that references doctypes from the shared
`ir.attachment.document.type` taxonomy and ships `ir.attachment.document.type.rel`
records (the Mappings that pin those doctypes to its own models) plus an
`ir.attachment.document.type.config` per model, via data XML. A consumer _may_ create
new doctype master records with `noupdate="1"` but should first check whether an
existing xmlid (in `web_attachment_document_type` or another consumer) already covers
the concept — the taxonomy is shared and duplicate names are blocked at the DB level
(`unique(name)` on `ir.attachment.document.type`). Consumers hold no Python or JS
related to the widget. First consumers: `kris_project` and `purchase_request_kmitl`.

## Rules of the game

- **Doctype is always optional.** `ir.attachment.document_type_id` is declared
  `required=False` at base. Files coming in through any path (widget Attach button, drag
  & drop, mail chatter, API, import) are accepted with `document_type_id = NULL`. The
  badge displays "-" for those, and the user can set the value later via the pencil
  button.
- **Business rule "must have doctype" is a consumer concern.** If a workflow needs every
  attachment classified before a state transition (e.g. `kris.project.action_confirm`),
  the consumer writes an `@api.constrains` or a check in the transition method that
  raises `UserError` when `attachment_ids.filtered(lambda a: not a.document_type_id)` is
  non-empty. Base does not enforce.
- **Scope is data — one Config per model, one Mapping per doctype.** To offer doctypes
  on a new parent model, ship (or add via UI) a Config
  (`ir.attachment.document.type.config`) with inline Mappings referencing the doctype
  master records. **New** on the Config tree creates a Config — no ir.model rows are
  ever created from the UI.
- **Two menus, two purposes.** Settings → Technical → Parameters exposes two menus:
  - **Document Types** — master taxonomy CRUD (create/rename/archive/delete). The action
    opens with `active_test: False` so archived doctypes are visible for un-archiving.
    Deletion is guarded by `ondelete="restrict"` on `ir.attachment.document_type_id` —
    Postgres blocks unlink of a doctype in use by any attachment.
  - **Attachment Doctypes** — model-Config: which doctypes are offered on which parent
    model, in what order. The doctype m2o inside each Config's Mapping tree is locked to
    select-only (`no_create`, `no_create_edit`, `no_open`) so admins can't accidentally
    spawn typo'd master rows from this form; new doctypes must be created explicitly
    from the **Document Types** menu first.
- **Sequence lives on the Mapping, not on the Doctype.** The same doctype can appear in
  a different position under different models.
- **UI is conditional.** A form whose `res_model` has zero doctypes mapped to it renders
  the widget unchanged from Odoo standard — no badge, no pencil, no dropdown. It does
  still get drag & drop (unconditional).
- **Post-hoc edit via clickable badge.** The Document Type badge next to each
  attachment's caption is itself the affordance — blue badge with the doctype name if
  set, yellow "- Set type -" badge if not. Clicking opens a dialog with the doctype
  dropdown pre-populated. Save writes `document_type_id` via `orm.write`; Cancel closes.
  The attachment record itself and its id are preserved throughout.
- **Drag & drop is always on.** All 12 Odoo core usages of `many2many_binary` (mail
  composer, hr leaves, account invoice send, survey, etc.) and 17 in this repo
  (disbursement, advance_payment, agx_approval, …) get drag & drop for free — pure UX
  enhancement, no behavioural change.
- **Attach button opens a dialog when doctypes exist.** On a `res_model` that has at
  least one Mapping, clicking Attach opens `AttachmentDocumentTypeDialog` with a file
  input (drag-drop capable) plus a Document Type dropdown — user picks the doctype at
  upload time and uploads via `/web/binary/upload_attachment`. On a `res_model` with
  zero Mappings, Attach falls through to Odoo's standard `FileInput` → OS picker.
- **Filenames open in a new tab, not download.** `getUrl` returns `?download=false`, the
  anchor's `download` attribute is stripped, and `target="_blank"` is added. Applies to
  every `many2many_binary` in the system, not only models with doctype mappings.
  Right-click → _Save link as…_ still triggers a download.
- **`document_type_id` is fetched reactively.** Added to
  `Many2ManyBinaryField.fieldsToFetch` at patch time, so the badge updates immediately
  when a user edits it — no full-form reload needed.
- **Chatter tracking on doctype change runs with sudo.** `ir.attachment.write` posts a
  "Document Type: old → new" message on the parent's chatter using `sudo()` on the
  parent browse. This means a user who can write an attachment always leaves a trail,
  even if they don't have read access to the parent record. Intentional:
  attachment-level writes are already permitted by policy, and the chatter trail is more
  valuable than the (rare) information-leak concern of a mysterious author appearing on
  chatter.

## Manual verification checklist

Test end-to-end after touching the patch or the taxonomy model:

1. Install `web_attachment_document_type`, upgrade `kris_project` and
   `purchase_request_kmitl` so migrations run.
2. Migration lands cleanly (log has "remapped N attachments" lines for old doctype rows;
   legacy `kris_project_document_type` table dropped; `ir_attachment.attachment_type`
   column dropped).
3. Open a `kris.project` form → attachment tab uses the standard `many2many_binary`:
   - Drag a file over the card list → dashed outline overlay "Drop files to attach"
     appears → release → file uploads → row appears with a pencil icon and a "-" badge.
   - Click pencil → dialog with a Document Type dropdown showing kris_project's doctypes
     (Contract / Purchase / Receipt) → pick a value → Save → badge updates.
4. Open a `purchase.request` form → same behaviour but the dropdown lists TOR /
   Quotation / Etc.
5. Open a vendor bill (`account.move`) or any other form with `many2many_binary` and no
   doctypes mapped → drag & drop still works, but there is **no** badge, **no** pencil,
   **no** dropdown — widget looks exactly like Odoo standard.
6. Reload a form after tagging → badges still show. This confirms `document_type_id` is
   in `fieldsToFetch`.
7. Settings > Technical > Parameters > **Attachment Doctypes**: click **New** → form
   opens → pick `Model` = `purchase.order`, pick or quick-create a doctype in
   `Document Type`, set `Sequence` → **Save**. Open a PO form → dropdown + badge appear
   immediately (order matches the sequence just set), no JS reload. Repeat to add more
   doctypes to the same model. The tree groups by model and only lists models that have
   at least one Mapping.
8. Historical attachments (created before the migration) still show their correct
   badges: the migration mapped their old `kris.project.document.type` id /
   `attachment_type` Selection value to the new `ir.attachment.document.type` records by
   NAME/value respectively.
9. Chatter D&D bug (see commit `97af33e`) still works: dragging over a form with a
   chatter and dropping on the attachment widget does not leave the chatter drop overlay
   stuck.
10. Upload via mail chatter → attachment appears in the widget list with a "-" badge →
    pencil to set doctype.
11. Consumer constraint enforcement: if `kris.project.action_confirm` is wired to check
    `attachment_ids` doctypes, confirming a project that has an unclassified attachment
    raises `UserError` — implement this only where the workflow actually needs it, not
    by default.
