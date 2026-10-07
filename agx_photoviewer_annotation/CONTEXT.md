# Photo Viewer — Annotation

Lets whoever checks an attachment (ผู้ตรวจสอบ) mark it up directly in the photo viewer —
tick, cross, draw, highlight and comment on an image or a PDF — so the maker sees
exactly what to fix. Marks live beside the file, never inside it (ADR-0001).

## Language

**Annotation**: One mark a user placed on one page of an attachment: a pen stroke, a ✓
or ✗ stamp, a highlight, a rectangle or a Comment. Belongs to its author; only the
author changes or removes it. _Avoid_: markup, drawing, note

**Comment**: An Annotation that is a single text pinned at a point of a page. Has no
replies and no resolved state — discussion belongs in the source record's chatter.
_Avoid_: sticky note, remark, thread

**Annotation layer**: All Annotations of one attachment, from every author. Everyone who
can read the attachment sees the whole layer and may add to it. _Avoid_: overlay
(implementation word), annotated file

**Annotated export**: A PDF built on demand from the original file with its Annotation
layer drawn on top and the Comments listed on a closing summary page. Downloaded, never
stored. _Avoid_: annotated copy, flattened file

**Session note**: The single internal note posted on the source record's chatter when a
user leaves an attachment they annotated, summarising what they added, changed or
removed. _Avoid_: notification, log
