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
carry the funding source; central chooses that when fulfilling.
_Avoid_: budget request (ambiguous with พ.1 purchase request), transfer

**Requesting Unit (หน่วยงานผู้ขอรับการสนับสนุน)**:
The unit asking for support, identified on the request by its **`department` dimension**
(`department_analytic_id`) — the financial-dimension language of the budget side. Its
Operating Unit is secondary (access/visibility only) and is stamped from the requester's
default OU, later used as the **Beneficiary Unit** if the request is fulfilled by Reserve.
_Avoid_: beneficiary (that is the OU role on the reservation), applicant

**Fulfilment Method (วิธีจัดสรร — โอน / จอง)**:
How an approved request is satisfied. **Transfer (โอน)** moves pool into the requester's
own `department` dimension (a `budget.transfer`; the requester then owns and spends it
freely). **Reserve (จอง)** creates a standalone ใบจองงบประมาณ (`budget.commitment`) with
the requester as **Beneficiary Unit**, keeping central's dimension on the slip; the
requester draws it down through its own พ.1/disbursement. Central always chooses the
funding source and dimensions; on Transfer the target department is the requester's, on
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

**Support Officer (เจ้าหน้าที่ส่วนกลาง, `group_budget_support_officer`)**:
A notify-only role: members receive a Todo (`mail.activity`) when a request is approved so
they know to fulfil it. The group grants read on the request (so the Todo opens) and
nothing more — approving and fulfilling are the Budget Manager's. Membership is the
"settings" for who gets pinged.
_Avoid_: manager, approver (those are `budget.group_budget_manager`)

**State lifecycle**:
`draft → submitted → approved → in_progress → done`, plus `cancelled` / `rejected` (and,
with the e-Saraban bridge, `sent` / `returned`). **`approved`** = approved in principle,
central has not yet acted. **`in_progress`** = central has fulfilled at least one
allocation (a linked `budget.transfer` posted or `budget.commitment` reserved) — this is
the "has central acted yet?" signal. **`done`** = central manually closes the request
(open-ended: many allocations may link back, so the system cannot know when it is complete);
closing notifies the requester with a Todo.
_Avoid_: posted (that is the transfer's term), fulfilled (use `done`)
