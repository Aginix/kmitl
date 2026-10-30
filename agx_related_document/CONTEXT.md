# Related Documents

Lets a record cite other documents as supporting evidence — a request citing the
project it is for, a transfer citing its approval, a loan citing a letter. Only models
that opt in have them; each consumer is a thin bridge.

## Language

**Related document (เอกสารอ้างอิง)**: A document cited on a record, beside whatever the
record already links to by its own workflow. Purely supporting evidence: it never drives
budget, dimensions, route or prefill, and the record's own module never waits on it. A
bridge may relabel it (the loan says เอกสารอ้างอิงเพิ่มเติม).
_Avoid_: อ้างถึง (Sarabun's own term for its letters), attachment, origin, bare "reference"

**Kind (ชนิดเอกสารอ้างอิง)**: Master data an administrator configures: an in-system model
with its number, subject and date fields; ใช้ได้กับ (which models may cite it, empty =
all); a target domain (e.g. approved only); whether a typed number is also looked up under
sudo; and whether the target shows ถูกอ้างอิงโดย. No module per kind. A row with no kind is
an **out-of-system document (เอกสารนอกระบบ)**, given by number and subject.

**Citing document (เอกสารที่อ้าง) / Target (เอกสารที่ถูกอ้าง)**: The record carrying the
rows, and the record a row points at. Rows are visible to whoever may read the citing
document. The target is picked from a dropdown that runs under the user's own rights, or
found by typing its exact number — under sudo only if its kind allows it.

**Snapshot**: What the row keeps of the target: kind, number, date, subject, file. Every
reader of the citing document sees it. **เปิดเอกสาร** opens the target under the reader's
own rights, never sudo: no access says so, a deleted target says เอกสารถูกลบแล้ว.

**ถูกอ้างอิงโดย (cited by)**: An action-menu entry a kind may publish on its target model,
listing the rows citing the selected records — only those whose citing document the user
can read.

## Lifecycle

Rows are never copied (not to fulfilment documents, not on duplicate) and die with their
citing document. Deleting or cancelling a target leaves the row and its snapshot. Citing
never blocks deleting or cancelling either document. Every addition and removal is logged
in the citing document's chatter.
