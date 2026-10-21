# Web Attachment Link

Lets users attach a link — a YouTube video, a Google Drive item, a record or action in
this Odoo database, or any web page — wherever they attach files, so evidence that lives
outside a file still sits with the document. The add-on `agx_photoviewer_links` (no own
glossary — part of this context) opens links in the photo viewer next to the files.

## Language

**Link Attachment**:
An attachment that points somewhere instead of holding a file — Odoo's own `url`-type
`ir.attachment`, never a new kind of record.
_Avoid_: URL file, web attachment, link file

**File Attachment**:
An attachment that holds the uploaded bytes itself (`binary` type) — what users simply call
ไฟล์แนบ.
_Avoid_: binary attachment, upload

**Link Kind**:
What a Link Attachment points to, read from its URL every time it is shown and never
stored: **YouTube**, **Google Drive**, **Odoo Link** or **Other Web Link**.
_Avoid_: attachment type (collides with Document Type and mimetype), link type, provider

**Odoo Link**:
A Link Attachment pointing at a record or an action of this same database, kept as a
host-less `/web#…` address so it survives copying the database to another server.
_Avoid_: internal link, action link, deep link

**Other Web Link**:
Any Link Attachment that is not one of the recognised kinds; shown, never embedded.
_Avoid_: external link (YouTube and Google Drive are external too)

**Link Card**:
The viewer page standing in for a link that cannot be embedded — an Odoo Link or an Other
Web Link — naming what the link points to and offering to open it.
_Avoid_: preview (the card shows no content of the target)

**เปิดต้นทาง (Open at origin)**:
The viewer action that opens a Link Attachment where it lives — on YouTube, in Google
Drive, on the Odoo record or on the web page — taking the place a File Attachment's
Download holds.
_Avoid_: download (a link has nothing to download)
