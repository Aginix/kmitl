===================================
Photo Viewer - Annotation Revision
===================================

A corrected file is uploaded as the next **revision** of an annotated one,
never over it (``agx_photoviewer_annotation/docs/adr/0003``; see *Revision* in
``agx_photoviewer_annotation/CONTEXT.md``).

* *Upload a revision* in the viewer (needs the right to edit the record, like
  attaching any file) adds the next revision of the file. The viewer's picker
  reaches every revision; a superseded one keeps its marks where they were drawn
  and is no longer annotated. An annotated file can no longer be overwritten.
* The record shows only the latest revision among its files: its many2many
  file fields are rewritten, its One2many of attachments (by ``res_id``) and the
  chatter's attachment box leave superseded ones out.
* The chatter is history: a message keeps the revision it was posted with,
  marked *Replaced by revision n*, and each upload is noted with the new file.
