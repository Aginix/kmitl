=================================
Photo Viewer - Annotation Review
=================================

Follows up a review done with ``agx_photoviewer_annotation``: the reviewer asks
for fixes, the maker answers them and uploads the corrected file as a revision
of the original. See the glossary in ``agx_photoviewer_annotation/CONTEXT.md``
(Change request, Response, Revision) and its ``docs/adr/0003``.

* **Change requests** — a reviewer ticks *Ask for a fix* on a Comment; most
  marks stay plain review marks. A request is *open*, *answered* once someone
  else gives a Response, and *closed* (or reopened) by its author only. Pins
  wear a ring in the colour of their state; files show a ``! n`` badge of the
  requests still open on any of their revisions.
* **Revisions** — *Upload a revision* (needs the right to edit the record,
  like attaching any file) adds the next revision of the file: the record and
  its chatter then show only the latest one, the earlier ones are reached from
  the viewer's revision picker. A superseded revision keeps its marks where they
  were drawn and is no longer annotated; an annotated file can no longer be
  overwritten.
* The **Change requests** panel lists those not closed on every revision of
  the file, answers and closes them, and jumps to their pin on the revision they
  were made on.
* Open requests never hold up a record by themselves; its module may call
  ``record._annotation_open_change_requests()`` to refuse a step while some are
  open. A record whose layer is locked (``_annotation_is_locked``) freezes its
  requests too.
