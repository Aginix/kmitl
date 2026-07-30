# พจ.1 (PA) stays a separate model from พ.1 (PR) — not collapsed

พ.1 (`purchase.request`, ใบขอให้จัดหา, approved by the หัวหน้าส่วนงาน) and พจ.1
(`purchase.request.approval`, ขออนุมัติจัดซื้อจัดจ้าง, approved to actually buy) are two distinct
approval processes with different approvers. พจ.1 copies its data from พ.1 but may legitimately
diverge — vendor, tax, procurement type, and (God-Mode) the amount within the reserved budget can
all be re-edited on the พจ.1. We therefore keep `purchase.request.approval` as a **separate model**
(`_inherits purchase.request` via `request_id`), with **1 พ.1 → 1 พจ.1** enforced as a policy while
the schema stays one-to-many, rather than folding พจ.1 into a phase/report of the PR.

## Considered options

- **Collapse PA into the PR** as a lifecycle phase plus a generated PDF report — rejected: the two
  are genuinely separate documents whose data diverges and which carry separate approvers; collapsing
  would force divergent-data hacks and lose the distinct approval identity.

## Consequences

- The two approvals — พ.1 "อนุมัติให้จัดหา" (dept head) and พจ.1 "อนุมัติจัดซื้อ" — are a
  **legitimate double approval, not duplication**. The messiness today comes from cramming both onto
  overlapping PR states, not from the two documents existing.
- The PA-family modules keep their raison d'être. This **reinforces ADR-0001** (which already treats
  PA as its own document deriving the officer from its PR); nothing there is superseded.
- If split procurement (many พจ.1 per พ.1) is ever needed, only the 1:1 policy guard is relaxed — no
  schema migration.
