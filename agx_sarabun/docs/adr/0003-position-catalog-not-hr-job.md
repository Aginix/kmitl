# Position is a purpose-built catalog, not hr.job

Routing targets a ตำแหน่งบริหาร (administrative position — คณบดี, ผอ.กอง, อธิการบดี) and a document is signed in the capacity of that position. `hr.job` models *employment* positions, which carry the wrong semantics, and academic rank (ศ./รศ./ผศ.) is display-only, not authority — the old `sarabun.role.role_category` wrongly merged the two. We decided a dedicated **`sarabun.position`** catalog is the canonical routing target and signing capacity; it resolves to its current **holder(s) at the moment a step becomes active** and snapshots that person-set onto the step, so later org changes never rewrite history while routing still reaches whoever holds the post *now*. รักษาการ/มอบอำนาจ (acting & delegated authority) is a deliberate phase-2 seam — interim, add the acting user as a temporary holder.

## Consequences

- Signing capacity is validated against the step's target Position (or an acting capacity of it), not any role the user happens to hold.
- Academic rank lives on the person and renders only in the signature block.
