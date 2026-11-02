# Annotations are an overlay, the file is never rewritten

Annotations are stored as their own records (page + normalised geometry) next to the
`ir.attachment`, and drawn over the file when it is shown; the attachment's content is
never modified. The original upload stays the evidence of what the maker sent, each mark
keeps its author and can be removed on its own, and several reviewers can work on the
same file without overwriting one another. Burning marks into the file (as Odoo
Enterprise _Sign_ does) was rejected for those reasons; when a flattened file is needed,
the **Annotated export** builds one on demand and does not store it, so there is never a
second "which one is the original?" attachment.

## Consequences

If the attachment's content is replaced, existing Annotations may no longer line up;
each Annotation records the file checksum it was drawn on so the viewer can warn about
it.
