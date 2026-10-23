# A corrected file is uploaded as a Revision of the original, never over it

When a maker fixes a file a reviewer annotated, the fixed file is uploaded as the next
**Revision** of the same document: it points back to the previous one, which it
supersedes. Overwriting the annotated attachment was rejected because its Annotations
would no longer line up and the file the reviewer actually checked would be lost
(ADR-0001). Uploading an unrelated new file was rejected because nothing would tell the
reviewer which file replaces which, and the open Change requests would stay behind on a
file nobody opens. Mainstream review tools (proofing tools, construction CDEs, version
history in file stores) work the same way: one document, a stack of immutable revisions,
markups pinned to the revision they were drawn on.

## Consequences

- An attachment that carries Annotations can no longer be overwritten; only a file
  nobody has annotated yet may still be replaced in place.
- Annotations stay on the revision they were drawn on and are never moved onto the next
  one, whose pages may differ. A superseded revision keeps its layer, locked, as the
  record of that round of review.
- Open Change requests have to be followed from one revision to the next by reference,
  not by position.
