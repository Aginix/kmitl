# Direct Allocation posts the project transfer without its approval and reserves in the same step

Most projects' budgets are approved **together with their floating money** at
ประมาณการรายจ่าย (expenditure estimate). Under
[ADR-0006](./0006-project-allocation-before-reserve.md) งานแผน must still raise a
Project Allocation `budget.transfer` and route it through its own approval (ยืนยัน →
หนังสือ e-Saraban → signature, budget ADR-0014) before the project can reserve —
approving the same money a second time. The system holds no record of which projects
ประมาณการรายจ่าย approved, so this cannot be automated from data.

**Decision:** add a **Direct Allocation (จัดสรรจากเงินลอย)** action on the project,
"จัดสรรและจองงบประมาณ", for **Budget Users** (งานแผน) while the project is in
`to_verify`. In one transaction it:

1. creates a `budget.transfer` FROM the Floating Budget at the project's **own**
   coordinate (รหัสงบ + the four dimensions, no project tag) TO the same coordinate
   **plus** the project's `kmitl_project` dimension, for an amount defaulting to the
   Project Budget Plan expense total minus what is already allocated (editable);
2. runs the transfer's normal ยืนยัน (`action_submit` — structure, exception rules,
   floating availability) and then **posts it straight away**, recording the clicking
   user as approver — no e-Saraban letter and no Budget Manager approval;
3. reserves the project exactly as the existing จองงบ step does (`to_verify → to_send`).

Lives in its own module, `kmitl_project_direct_allocation`, which is **not**
auto-installed: skipping the approval is a policy choice, and installing the module is
that choice. Uninstalling it removes the shortcut without touching anything else. The
ordinary path (a normal transfer and then the owner's จองงบ) is unchanged and remains
the route for money at another coordinate and for top-ups after reservation.

## Why

- **Skip the approval, not the ledger move.** Posting a real transfer keeps ADR-0006's
  load-bearing invariant: the allocation and the reserve check both carry the project
  dimension. As a result `budget_amount`, the availability engine, the reserve logic and
  per-project isolation all work unchanged, and the BTR number stays as the audit trail.
  Reserving straight from floating (ADR-0007-style) was rejected: `budget_amount` would
  have to become typed again, and isolation between projects would be lost.
- **One step.** Allocation and reservation happen together because, for these projects,
  there is nothing to wait for between them.
- **Fixed coordinate, no picker.** The floating money for these projects sits at the
  project's own coordinate. Anything else is an ordinary transfer, which keeps the
  action simple.

## Consequences

- A posted `budget.transfer` can now exist without a หนังสือ or a Budget Manager
  approver. It is identifiable by its reason ("จัดสรรจากเงินลอย …") and by the project's
  chatter note.
- The Budget User group gains the effective right to post project-allocation transfers
  through this action only. The base transfer `action_approve` stays
  Budget-Manager/not-self.
- Reversal is unchanged (ADR-0006 #6): reset the posted BTR (Budget Manager), and the
  project's reservation follows through the usual re-sync and release rules.
