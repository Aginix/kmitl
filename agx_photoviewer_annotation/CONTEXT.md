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
reviewer's mark and asks nothing of anyone, unless its author makes it a Change request.
_Avoid_: sticky note, remark, thread

**Change request**: A Comment its author flagged, when writing it, as asking the maker to
fix or explain something. Not flagged by default: most of what a reviewer writes or
draws (ticks, highlights, "matches the invoice") is just the trace of their review, and
only Change requests are followed up. Other kinds of Annotation are never Change
requests; a reviewer who wants a mark fixed pins a Change request beside it. It is
**open** when pinned or reopened, **answered** once someone other than its author gives
a Response, and **closed** only by its author, who may reopen it instead. Open ones are
shown on the file but never hold up the record by themselves; the record's own module
may refuse a step while some are open. _Avoid_: issue, task, open comment

**Response**: The one short text that answers a Change request — "fixed in revision 2",
"not changed because…" — given by anyone who can read the file except the request's
author. Not a conversation: a longer discussion belongs in the record's chatter.
_Avoid_: reply, answer thread

**Annotation layer**: All Annotations of one attachment, from every author. Everyone who
can read the attachment sees the whole layer and may add to it. Adding to it is
reviewing the file, not editing the record it belongs to: a record the user cannot edit
does not stop them, and the layer stays open once the record is done unless it is a
Locked layer. _Avoid_: overlay (implementation word), annotated file

**Revision**: One upload of a file in its chain of uploads. Uploading a revision of an
attachment adds the next one, which supersedes the previous; every revision of the chain
is the same document. A superseded revision stays viewable with its Annotations, pinned
where they were drawn; nobody annotates it any more, but its Change requests still open
are listed on the latest revision, where they are answered and closed, until closed. The
record the file belongs to shows only the latest revision; earlier
ones are reached from the viewer. A file that carries Annotations is never overwritten:
changing it means uploading a revision. Uploading one changes the record, so it needs the
right to edit the record, like attaching any file, and is refused on a Locked layer —
unlike annotating, which only needs to read the file. _Avoid_: version, new file, copy

**Locked layer**: An Annotation layer the record's own module has closed, e.g. once the
record is done. Nobody adds, changes or removes Annotations on it, their authors
included, and its Change requests are no longer answered, closed or reopened: those
still open stay open as the record of the review. It can still be viewed, its Comments
read and the Annotated export downloaded. Records are never locked unless their module says so. _Avoid_: frozen,
read-only layer

**Annotated export**: A PDF built on demand from the original file with its Annotation
layer drawn on top and the Comments listed on a closing summary page. Downloaded, never
stored. _Avoid_: annotated copy, flattened file

**Session note**: The single internal note posted on the source record's chatter when a
user leaves an attachment they annotated, summarising what they added, changed or
removed. Posted even when the user may not write on that chatter themselves. _Avoid_: notification, log
