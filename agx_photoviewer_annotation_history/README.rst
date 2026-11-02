==================================
Photo Viewer - Annotation History
==================================

Adds a **History** panel to the annotation toolbar of
``agx_photoviewer_annotation``: every visit in which someone added, changed or
removed marks on a file is listed, newest first, with who and when.

* Clicking a Change draws the annotation layer as that Change left it, read-only:
  marks it added glow green, marks it changed glow orange with their earlier
  place shown faded, and marks it removed are shown faded with a dashed outline.
  **Current** goes back to the live layer.
* Every addition, change and removal is logged in
  ``ir.attachment.annotation.event``, kept once the mark is removed (removed
  comments stay readable in the History). Whoever can read the attachment sees
  its History (``docs/adr/0001``).
* On install, the annotations already on files are logged as one addition per
  author and day; earlier changes and removals were never recorded.
