# PDFs are rendered page by page on canvases, not in the pdf.js viewer iframe

`agx_photoviewer_filetypes` shows a PDF in an iframe of Odoo's bundled pdf.js viewer
(2.2.228). That viewer has no annotation editor (added in pdf.js 3.x) and its pages move
and rescale inside the iframe, so no overlay can stay pinned to them. This module
instead renders each page itself with the pdf.js _library_ already shipped by `web`,
stacks the canvases, and puts one drawing layer on each page with coordinates normalised
to the page. Upgrading to a newer pdf.js with its own editor was rejected: it stores
annotations inside the PDF (contradicting ADR-0001) and would mean bundling a second
pdf.js. The price is that the viewer's text search, sidebar and in-viewer print are gone
for PDFs while this module is installed; download still works.
