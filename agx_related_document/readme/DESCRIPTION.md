Lets a record **cite other documents as supporting evidence** (เอกสารอ้างอิง) — in-system
ones picked from a dropdown or found by number, or out-of-system ones given by number and
subject, each optionally with a file. A citation is evidence only: it never drives
budget, dimensions, route or prefill.

A model opts in by inheriting `related.document.mixin` and showing `related_document_ids`
with the embedded list view; the module adds no field to any other model.

- **Kinds** (ชนิดเอกสารอ้างอิง, Settings ▸ Technical) are master data: a model, its
  number/subject/date fields, which models may cite it, a target domain, whether a typed
  number is also looked up under sudo, and whether the target gets a **ถูกอ้างอิงโดย**
  action-menu entry.
- Rows keep a snapshot (number, date, subject, file). **เปิดเอกสาร** opens the target
  under the reader's own rights.
- Whoever reads the citing record reads its rows; who may change them is the citing
  model's `_related_document_check_change` hook (default: write access). Every addition and
  removal is logged in its chatter.
- Rows are never copied, die with the citing record, and never block deleting or cancelling
  either document.
