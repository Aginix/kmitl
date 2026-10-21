# Link Kind is read from the URL, not stored

A Link Attachment is Odoo's own `ir.attachment` with `type='url'`, and its Link Kind
(YouTube, Google Drive, Odoo Link, Other Web Link) is recognised from the URL by the
viewer each time it is shown. We neither add values to `ir.attachment.type` nor store a
kind field.

## Considered Options

- **New values in `ir.attachment.type`** (`selection_add` of `youtube`, `gdrive`,
  `odoo_action`) — rejected: core code branches on `type == 'binary'` / `'url'` by name
  (the `type`/`url` constraint, the filestore, `/web/content` streaming that redirects
  `url` attachments, the mail viewer's `isUrl`), so every new value would silently fall
  out of all of them.
- **Stored `link_kind` field on `ir.attachment`** — rejected: it would duplicate what the
  URL already says, drift when a URL pattern is learnt later, and require a migration for
  every link already in the database; nobody needs to search attachments by kind.

## Consequences

- Teaching the viewer a new kind is a new renderer in `agx_photoviewer_links`, with no
  data or migration; links attached before it was installed are recognised at once.
- Without `agx_photoviewer_links` a Link Attachment is just a URL that opens in a new
  tab, because `/web/content/<id>` already redirects `url` attachments.
