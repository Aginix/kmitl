==========================
Photo Viewer - Annotation
==========================

Lets whoever checks an attachment tick, draw, highlight and comment directly on
an image or a PDF inside the photo viewer of ``agx_photoviewer``.

* Opening an image or a PDF shows its pages with every annotation on top; the
  **Annotate** button opens the tools: pen, ✓ / ✗ stamps, highlight,
  rectangle, comment, eraser (own marks), colours and undo. On a touch screen
  one finger annotates and two fingers scroll and pinch-zoom the pages; a palm
  resting on the screen while a stylus draws is ignored.
* Each mark is saved as soon as it is drawn, in ``ir.attachment.annotation``;
  the file itself is never modified (``docs/adr/0001``). Everyone who can read
  the attachment sees all marks and may add some; only the author changes or
  removes a mark, and drags their own comment pins to move them.
* The module of a record may lock the annotations of its files, e.g. once the
  record is done, by overriding ``_annotation_is_locked`` on its model (never
  locked by default). A locked layer can still be viewed and exported.
* The eye button hides every mark to show the file as it was uploaded;
  annotating is off meanwhile.
* **Download with annotations** builds a PDF of the file with the marks drawn
  on it and the comments listed on a last page; nothing is stored.
* Leaving an annotated file posts one internal note on the chatter of the
  record the file belongs to.
* Attachments with annotations show a ``✎ n`` badge in ``many2many_binary``
  fields, the chatter and the viewer's thumbnail strip.

See ``agx_photoviewer_annotation_history`` to browse the past changes of a file.
See ``agx_photoviewer_annotation_review`` for change requests and revisions of a
file.

PDF pages are drawn with the pdf.js library of ``web`` instead of its viewer
(``docs/adr/0002``): text search, the sidebar and printing from the viewer are
not available for PDFs while this module is installed.
