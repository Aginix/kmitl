# Budget Support Request

A requesting unit (หน่วยงาน) asks central for budget support (ขอรับการสนับสนุนงบประมาณ):
it states which department dimension it needs money on, how much, and why. Central
considers the request and, once approved, **fulfils** it by either transferring pool
into the requester's dimension or reserving a ใบจองงบประมาณ for the requester.

Part of the [Budget](../budget/CONTEXT.md) context. Structurally mirrors
`budget_transfer` (a simple approval workflow in the core, an e-Saraban approval
routed by a separate bridge).

## Language

**Budget Support Request (คำขอรับการสนับสนุนงบประมาณ)**:
The document a requesting unit files to ask central for budget. It carries only the
*request* side — the requester's `department` dimension, the amount asked for, a
rich-text justification (เหตุผล/ความจำเป็น), and supporting attachments. It does **not**
name the pool the money comes out of; central picks that when fulfilling.
_Avoid_: budget request (ambiguous with พ.1 purchase request), transfer

**แหล่งเงิน of a support request**:
Always **งบประมาณเงินรายได้** — central supports units out of revenue budget and nothing
else, so this is a stated fact about the request, not a question put to the requester. It
is shown, and travels onto whichever document fulfils the request (where ADR-0009 requires
both sides of a transfer to agree on it), but it is never chosen. A request naming any
other แหล่งเงิน is refused outright, however it was written.
_Avoid_: funding source (that is the *pool* central picks at fulfilment — a different
choice), budget type

**Requesting Unit (หน่วยงานผู้ขอรับการสนับสนุน)**:
The unit asking for support, identified on the request by its **`department` dimension**
(`department_analytic_id`) — the financial-dimension language of the budget side. Its
Operating Unit is secondary (access/visibility only) and is stamped from the requester's
default OU, later used as the **Beneficiary Unit** if the request is fulfilled by Reserve.
_Avoid_: beneficiary (that is the OU role on the reservation), applicant

**Requester (ผู้ขอ)**:
The one person who filed the request. Not transferable — the request stays attributed to
whoever raised it, which is what makes "an approver may not approve their own request"
meaningful. A colleague filing on someone's behalf files it in their own name.
_Avoid_: owner, responsible (the Buddy is the responsible party on central's side)

**Fulfilment Method (วิธีจัดสรร — โอน / จอง)**:
How an approved request is satisfied. **Transfer (โอน)** moves pool **out of central's own
`department` dimension (the source) into the requester's (the destination)** — a support
request is by definition central funding a unit, never the unit funding itself — so the
requester then owns and spends it freely (a `budget.transfer`). **Reserve (จอง)** creates a standalone ใบจองงบประมาณ (`budget.commitment`) with
the requester as **Beneficiary Unit**, keeping central's dimension on the slip; the
requester draws it down through its own พ.1/disbursement. Central always chooses the
pool and the remaining dimensions; on Transfer the target department is the requester's, on
Reserve the commitment's own department is central's (budget ADR-0011).
_Avoid_: allocation (that is ปรับเข้าแผน into a project dimension — a different move)

**Fulfil (จัดสรร)**:
The act, after approval, of opening the target document from an approved request: central
chooses the method, and the request opens a **new, pre-filled but unsaved**
`budget.transfer` form (requester's department + amount pre-filled as context defaults) or
`budget.commitment` form (amount pre-filled; the beneficiary OU is pre-filled by the
Operating Unit bridge) — never a persisted draft. `budget.move.line.account_id` and
`budget.commitment.account_id` are hard `required=True` with no default, so the document
cannot be `create()`-d before central has picked the funding account; pre-filling via
context defaults (`default_*`) lets the web-client new-record form carry
`support_request_id` and the known amounts without violating that constraint — the record
is only persisted once central fills in the account and saves. No second e-Saraban letter
is issued — the request's own approval is the authority; the generated transfer is posted
via the Budget Manager direct-post fallback, the commitment reserved directly. The request
links to the generated document and moves to `in_progress` the moment that document is
posted/reserved (not merely opened); central marks the request `done` by hand.
_Avoid_: execute, allocate, "spawns a draft" (nothing is persisted until central saves)

**Buddy (เจ้าหน้าที่ Buddy ส่วนกลาง)**:
The one central-office officer who looks after this request. The **same Buddy role as
everywhere else in Budget** — the coverage settings (which Buddy looks after which ส่วนงาน)
are shared, not re-declared here. Every request names exactly one, chosen by the requesting
unit itself and pre-filled with the Buddy who covers that unit; naming one is part of filing
the request, not an afterthought. The named Buddy — and only they — receive the Todo to
fulfil it once the request is approved. Approving and fulfilling remain the Budget Manager's
act; the Buddy is who gets told, and who the unit can chase.
_Avoid_: support officer (there is no separate role — it is the Buddy), manager, approver

**State lifecycle**:
`draft → submitted → approved → in_progress → done`, plus `cancelled` / `rejected` (and,
with the e-Saraban bridge, `sent` / `returned`). **`approved`** = approved in principle,
central has not yet acted. **`in_progress`** = central has fulfilled at least one
allocation (a linked `budget.transfer` posted or `budget.commitment` reserved) — this is
the "has central acted yet?" signal. **`done`** = central manually closes the request
(open-ended: many allocations may link back, so the system cannot know when it is complete);
closing notifies the requester with a Todo.
_Avoid_: posted (that is the transfer's term), fulfilled (use `done`)

**Reopening (คืนสู่ร่าง)**:
Putting a request back to `draft`. The requester may take back their own request while it is
merely `submitted`; from every other state — including one already decided or fulfilled —
reopening is a **Budget Manager's** act and theirs alone. Deliberately unguarded beyond
that: a manager reopening a fulfilled request is assumed to know the allocations already made
still point at it, and to settle those separately. Distinct from **cancelling**, which is
refused outright once central has acted.
_Avoid_: reset (English-only; say reopening), undo (nothing is unwound)
