# A ศูนย์งาน is a stamped owning unit, routed only while draft

Every work area (พัสดุ, การเงิน, งบ) needs to split the work of one Operating Unit by
document data — a คณะ split by ภาควิชา, plus central units. We model this as a
**ศูนย์งาน** (`work.center`) **stored on the document** (`work_center_id`, via
`work.center.mixin`), chosen by ordered **routing rules** (`work.center.rule`: document
model + domain) **only while the document is draft**. After draft the value is sticky —
rules never move it — but anyone who may write the document can still change it by hand.
The ศูนย์งาน is the unit that _owns and follows_ the document for its whole life, not
the place where its next action happens; who acts at each state stays governed by the
existing per-state rights.

## Why

- **Ownership must not move.** A พ.1 from ภาควิชาไฟฟ้า stays ภาคไฟฟ้า's work through
  ส่งตรวจ → ยืนยัน → จองงบ; re-routing it to whoever acts next (the MRP station reading)
  would make the ภาควิชา lose track of its own documents.
- **Stamped, not a live lens.** A live domain would silently move in-flight documents
  whenever an admin edits a rule, allow a document to sit in two ศูนย์งาน or none
  without anyone noticing, and could not express "this one was put elsewhere by hand". A
  stored value is also what makes per-card counters a single `read_group`.
- **Draft-only routing** lets a requester fix the routing data (e.g. ส่วนงานผู้ขอ)
  before submitting, and freezes ownership from the moment the document enters someone's
  queue.
- **A hand-picked ศูนย์งาน pins the document** (`work_center_manual`) when it differs
  from the rule result, so a deliberate choice survives later edits of the routing
  fields; clearing the field un-pins it. Writing the value the rules would give anyway
  (the form's onchange preview) does not pin.
- **Membership is focus only.** It drives the "ศูนย์งานของฉัน" overview and filters,
  never access, so introducing ศูนย์งาน changes nobody's rights; OU record rules and
  per-state rights stay authoritative. This is also why
  [mail_activity_todo ADR-0002](../../../mail_activity_todo/docs/adr/0002-group-todos-route-by-role-in-unit-resolved-live.md)'s
  rejection of materialised teams does not apply: that rejection was about membership
  _synced_ from role ∩ OU drifting stale; a ศูนย์งาน's membership is curated directly
  and is itself the source of truth.

## Considered options

- **Live domain lens** (no field on the document): zero per-model code, but silent
  moves, overlaps and gaps (see above). Rejected.
- **Current station, re-routed on each state change / work items per step (mrp.workorder
  style)**: models who acts next, which per-state rights already answer, and breaks the
  ภาควิชา's follow-up. Rejected.
- **Forward button between ศูนย์งาน**: couples ownership to the workflow. Rejected —
  moving is a plain field edit.
- **Rules win in draft (no pin)**: simpler, but silently undoes a deliberate choice.
  Rejected.
- **Generalise one of the four ordered-rule engines already in the repo**
  (`budget.buddy`, `purchase.buddy`, `disbursement.assignment.rule`,
  `finance.assignment.rule`): tempting, because `work.center.rule` is a fifth list of
  "first row whose condition matches wins". Rejected for now because all four resolve to
  a **`res.users`** and are explicitly advisory, while a ศูนย์งาน is an **organisational
  unit** that owns the document — a different noun with a different lifetime (a buddy
  may be recomputed at any state; a ศูนย์งาน freezes at draft). Extracting a shared base
  was also already weighed and rejected once, in
  [purchase ADR-0013](../../../docs/adr/0013-pa-assigned-to-is-assigned-officer-from-purchase-buddy.md),
  on the cost of the xmlid pre-migration. Once ศูนย์งาน proves out, the merge goes the
  other way: derive the officer **from** the ศูนย์งาน.

## Consequences

- Each consumer model needs a small bridge: inherit the mixin, extend
  `_work_center_routing_fields` (rules are only re-evaluated when one of these changes)
  and, if "draft" is not `state == 'draft'`, override `_work_center_is_routable`. Models
  under `tier.validation` must whitelist `work_center_id` / `work_center_manual`.
- A ศูนย์งาน with an Operating Unit (หน่วยงาน-level) implicitly ANDs
  `operating_unit_id = its OU` into its rules; without one (ส่วนกลาง-level) it matches
  any OU.
- Documents no rule matches are never blocked; each area has one synthetic
  **ยังไม่มีศูนย์งาน** card — a real, flagged `work.center` record (`is_unassigned`)
  rather than a JS-injected card, so it renders, counts and tests like any other card.
  Documents can never point to it.
- Card counters are configurable data (`work.center.counter`), counted with the viewer's
  own rights so each number equals the list it opens.
- Known limits: `child_of` / `parent_of` are resolved in memory only on a direct
  relational field (dotted paths fall back to a database check and may be stale in an
  unsaved form); a document returned to draft is routable again but only moves when a
  routing field is edited.
- The live assignment mechanisms are left untouched: `purchase_request_verifier`
  (ผู้ยืนยันตรวจสอบ on พ.1), `purchase_request_approval_buddy` (เจ้าหน้าที่ผู้รับผิดชอบ
  on พจ.1, from `purchase.buddy`), `budget_transfer_verify` (from `budget.buddy`),
  `disbursement_assignment_kmitl` and `finance_kmitl_assignment`. If ศูนย์งาน proves out
  it is meant to replace them. (`procurement_assignment_kmitl`, the Assigned Officer
  module an earlier draft of this ADR named, has since been removed from the repo.)
- This module is the core only. Each work area arrives as its own bridge module that
  seeds the area, inherits the mixin on its documents and adds the overview menu.
