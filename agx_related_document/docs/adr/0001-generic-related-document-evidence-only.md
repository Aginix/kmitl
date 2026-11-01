# Related documents: one central module, evidence only

Users cite in-system documents from a form — a budget support request citing a project or
a procurement plan, a transfer citing an approval request. The idea first existed only for
loans (advance_payment ADR-0029). It is now one module, `agx_related_document`, that a
model opts into through `related.document.mixin`; every consumer is a thin bridge. It
supersedes the related-document part of advance_payment ADR-0029.

- **Evidence only.** A cited document never drives budget, dimensions, route or prefill.
- **Lookup under the user's rights.** The dropdown searches the kind's model as the user.
  Typing an exact number falls back to sudo only when the kind enables
  `allow_number_lookup` (e.g. หนังสือสารบรรณ across units). A picked id is re-validated on the
  server, so an RPC cannot cite an arbitrary id.
- **Access derived from the citing document**, like `mail.activity`: whoever reads it
  reads its rows. Who may change them is the model's `_related_document_check_change`
  hook (default: write access); the loan overrides it with its borrower/staff rules.
- **Snapshot plus open-as-user.** The row stores kind, number, date, subject and file;
  เปิดเอกสาร browses the target as the reader and says so when they have no access.
- **Reverse view.** A kind may publish ถูกอ้างอิงโดย on its target model via a bound
  server action; it lists only rows whose citing document the user can read.
- **Never copied, never blocking.** Rows are not copied, die with the citing document,
  and citing never blocks deleting or cancelling either side.

## Considered Options

- *A bridge module per kind* — rejected: what gets cited changes with practice (ADR-0029).
- *The generic `reference` widget* — rejected: it reads `ir.model`, which regular users
  cannot; the picker widget gets its model and domain from the row instead.
- *Sudo lookup always* — rejected: it would let any user read the subject of any record
  of any configured kind; now a per-kind opt-in.

## Consequences

- A kind with `allow_number_lookup` exposes the subject of any record whose number is typed.
- Rows of a citing model whose module is uninstalled are invisible but remain.
- A bridge must pass `default_res_model` in the field's view context so the kind dropdown
  can offer only the kinds usable on its model.
