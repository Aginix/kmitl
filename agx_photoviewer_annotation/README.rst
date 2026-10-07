==========================
Photo Viewer - Annotation
==========================

Lets whoever checks an attachment tick, draw, highlight and comment directly on
an image or a PDF inside the photo viewer of ``agx_photoviewer``.

* Opening an image or a PDF shows its pages with every annotation on top; the
  **Annotate** button opens the tools: pen, ✓ / ✗ stamps, highlight,
  rectangle, comment, eraser (own marks), colours and undo.
* Each mark is saved as soon as it is drawn, in ``ir.attachment.annotation``;
  the file itself is never modified (``docs/adr/0001``). Everyone who can read
  the attachment sees all marks and may add some; only the author changes or
  removes a mark, and drags their own comment pins to move them.
* **Download with annotations** builds a PDF of the file with the marks drawn
  on it and the comments listed on a last page; nothing is stored.
* Leaving an annotated file posts one internal note on the chatter of the
  record the file belongs to.
* Attachments with annotations show a ``✎ n`` badge in ``many2many_binary``
  fields, the chatter and the viewer's thumbnail strip.

PDF pages are drawn with the pdf.js library of ``web`` instead of its viewer
(``docs/adr/0002``): text search, the sidebar and printing from the viewer are
not available for PDFs while this module is installed.
