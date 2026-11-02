# The History is replayed from an event log kept beside the annotations

`agx_photoviewer_annotation` only stores the current state of each Annotation: an edit
overwrites it and a removal deletes it. To show past states, every addition, change and
removal now writes an **Event** holding the Annotation before and after, and the viewer
replays the Events to draw the layer as any Change left it. Events are grouped into
Changes by the visit they were made in (the key the viewer sends with every call, the
same visit the Session note summarises), not one entry per mark, so the History stays
short. Opening a Change shows the whole layer at that point with the Change's marks
highlighted, rather than its marks alone, so they are seen in context.

## Consequences

- Removing a mark no longer erases it: its last state, comment text included, stays in
  the History for everyone who can read the file. The History exists to show reviewers
  what happened, so this is intended.
- Events written before this module was installed do not exist. On install, the
  Annotations already on files are logged as additions by their author on the day they
  were made; their earlier changes and removals cannot be recovered.
- Events cascade with the attachment, like the Annotations.
