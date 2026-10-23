# Photo Viewer — Annotation

Lets whoever checks an attachment (ผู้ตรวจสอบ) mark it up directly in the photo viewer —
tick, cross, draw, highlight and comment on an image or a PDF — so the maker sees
exactly what to fix. Marks live beside the file, never inside it (ADR-0001).

## Language

**Annotation**: One mark a user placed on one page of an attachment: a pen stroke, a ✓
or ✗ stamp, a highlight, a rectangle or a Comment. Belongs to its author; only the
author changes or removes it. _Avoid_: markup, drawing, note

**Comment**: An Annotation that is a single text pinned at a point of a page. Has no
replies — discussion belongs in the source record's chatter. A plain Comment is only the
reviewer's mark and asks nothing of anyone; a Comment that asks for a fix is the pin of
a Pinned Change request. _Avoid_: sticky note, remark, thread

**Change request**, **Reply**, **Assignee**: defined in Change Requests
(`agx_change_request/CONTEXT.md`). Only a Pinned Change request touches a file: its pin is
a Comment of the file's Annotation layer.

**Annotation layer**: All Annotations of one attachment, from every author. Everyone who
can read the attachment sees the whole layer and may add to it. Adding to it is
reviewing the file, not editing the record it belongs to: a record the user cannot edit
does not stop them, and the layer stays open once the record is done. _Avoid_: overlay (implementation word), annotated file

**Revision**: One upload of a file in its chain of uploads. Uploading a revision of an
attachment adds the next one, which supersedes the previous; every revision of the chain
is the same document. A superseded revision stays viewable with its Annotations, pinned
where they were drawn; nobody annotates it any more, but its Change requests are still
listed on the record with the others, where they are answered and closed. The
record the file belongs to shows only the latest revision among its files; earlier
ones are reached from the viewer. Its chatter is history: a message keeps the revision
it was posted with, shown as superseded, and the upload of each revision is noted with
the new file. A file that carries Annotations is never overwritten:
changing it means uploading a revision. Uploading one changes the record, so it needs the
right to edit the record, like attaching any file — unlike annotating, which only needs to read the file. _Avoid_: version, new file, copy

**Annotated export**: A PDF built on demand from the original file with its Annotation
layer drawn on top and the Comments listed on a closing summary page. Downloaded, never
stored. _Avoid_: annotated copy, flattened file

**Session note**: The single internal note posted on the source record's chatter when a
user leaves an attachment they annotated, summarising the Annotations they added, changed or
removed. Change requests are not in it: each of their steps is posted on its own. Posted even when the user may not write on that chatter themselves. _Avoid_: notification, log
