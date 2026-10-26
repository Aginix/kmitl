# Change requests live in their own module, opted into per model by a mixin

Change requests started as a flag on a photo-viewer Comment (photoviewer annotation
ADR-0003). Once a request could also be General — on the record, with no file — and
gained Assignees, activities and a chatter trail, nothing in it needed the viewer any
more. So the record-level part moves to `agx_change_request`, which depends on `mail`
only and offers a mixin a model inherits to take Change requests (like
`mail.activity.mixin`); pinning a request on a file is the bridge
`agx_photoviewer_change_request` between it and `agx_photoviewer_annotation`.
`agx_photoviewer_annotation_review` is split up before release: its Revisions, which no
longer need requests once those are listed on the record, become
`agx_photoviewer_annotation_revision`. A record kind opts in through its own module; files of
records that did not opt in can be annotated and commented on, never asked to be fixed.

## Considered Options

- **Keep everything in `agx_photoviewer_annotation_review`** — rejected: a record kind
  that only wants General requests would have to install the whole viewer stack, and the
  module name would no longer say what it does.
- **Offer requests on every record with a chatter** — rejected: a Pinned request on a
  record kind with no list of requests would leave its Assignees an activity pointing at
  a form where the request cannot be found.

## Consequences

- The record lock hook `_annotation_is_locked` is dropped before release: no record kind
  used it, and freezing requests on a done record left Assignees with activities they
  could not clear. A module still holds up its own steps with the open requests.
- A Pinned request whose file is deleted is Cancelled, so the request outlives its pin and
  keeps its own text instead of reading it from the Comment.
