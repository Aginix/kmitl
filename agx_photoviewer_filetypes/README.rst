=========================
Photo Viewer - File Types
=========================

Adds renderers to ``agx_photoviewer`` so these attachments preview in the same
viewer, both in ``many2many_binary`` fields and the chatter:

* PDF (Odoo's bundled pdf.js), video (``<video>``)
* Word ``.docx`` (docx-preview), Excel ``.xlsx/.xlsm/.xls`` (SheetJS, first
  5000 rows per sheet), PowerPoint ``.pptx`` (pptx-preview)

Office files are rendered in the browser; nothing leaves the server. Legacy
``.doc`` / ``.ppt`` are not supported. The libraries in ``static/lib`` are
lazy-loaded on first use:

* jszip 3.10.2 (MIT/GPL-3), docx-preview 0.4.1 (Apache-2.0),
  SheetJS 0.20.3 (Apache-2.0), pptx-preview 1.0.7 (ISC)
