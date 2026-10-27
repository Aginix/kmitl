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
rich-text justification (เหตุผล/ความจำเป็น), the **รหัสงบประมาณ** (`budget.account`) it
wants the money on, and supporting attachments. It does **not** name the pool the money comes
out of; central picks that when fulfilling. The รหัสงบประมาณ pre-fills the fulfilment
document's account (the transfer's destination line / the commitment), which central may
still change there.
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
is issued — the request's own approval is the authority; the generated transfer posts the
moment central confirms it (ยืนยัน), with no second approver and no สร้างหนังสือ, and carries
the request's เลขที่หนังสือ; the commitment is reserved directly. The request
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
act; the Buddy is who gets told, and who the unit can chase. They are also the one who
checks the request on its way out (see การตรวจสอบของ Buddy), so naming one is not a
formality: it decides who holds the request between the unit and the อธิการบดี. The unit
may hand it to a different Buddy right up until the check is done; an explicit pick is
never silently reverted, even if the request bounces back to draft.
_Avoid_: support officer (there is no separate role — it is the Buddy), manager, approver

**การตรวจสอบของ Buddy (ตรวจสอบ / ส่งกลับแก้ไข)**:
The step between the unit finishing its request and the request going out for approval.
The unit confirms, and the request is then the Buddy's to read: they either **ยืนยันตรวจสอบ**,
which releases it, or **ส่งกลับแก้ไข** with a reason, which returns it to the unit to fix —
the request keeps its number either way. Nobody else can do either, and nothing downstream
(no หนังสือ, no approval) can start until the Buddy has released it, so "the Buddy checks
it" is a fact about the document rather than a request for a favour.
_Avoid_: approve (the Buddy does not decide the money — the อธิการบดี does), review

**State lifecycle**:
`draft → to_verify → submitted → approved → in_progress → done`, plus `rejected`
(and the legacy `cancelled` — there is no Cancel any more, see Deleting) (and, with the e-Saraban bridge, `sent` / `returned`). **`to_verify`** = the unit
is finished, the Buddy has not read it yet. **`submitted`** = released by the Buddy and
ready for a หนังสือ. **`approved`** = approved in principle,
central has not yet acted. **`in_progress`** = central has fulfilled at least one
allocation (a linked `budget.transfer` posted or `budget.commitment` reserved) — this is
the "has central acted yet?" signal. **`done`** = central manually closes the request
(open-ended: many allocations may link back, so the system cannot know when it is complete);
closing notifies the requester with a Todo.
_Avoid_: posted (that is the transfer's term), fulfilled (use `done`)

**Reopening (คืนสู่ร่าง)**:
Putting a request back to `draft`. The requester may take back their own request while it is
still undecided (`to_verify`, `submitted`, and with e-Saraban `returned`); from every other state — including one already decided or fulfilled —
reopening is a **Budget Manager's** act and theirs alone. Deliberately unguarded beyond
that: a manager reopening a fulfilled request is assumed to know the allocations already made
still point at it, and to settle those separately.
_Avoid_: reset (English-only; say reopening), undo (nothing is unwound)

**Deleting (ลบ)**:
Replaces cancelling. The requester (or a Budget Manager) deletes a request they no longer
want — only once it is back in `draft`, never one with a transfer/commitment against it, and
(with e-Saraban) never while a หนังสือ is still live.

**Title (ชื่อเรื่อง)**:
What the request is about, in the unit's words — required to submit, and the เรื่อง of the
หนังสือ the e-Saraban bridge issues.

**Buddy editing**:
While the request sits in `to_verify` the named Buddy may correct it directly instead of
sending it back. The Buddy follows the request and its หนังสือ.

**วันที่ส่งคำขอ (`date`)**:
Stamped by the system when the requester confirms (the latest confirm, if it came back and was
re-sent) — not typed in. The e-Saraban bridge adds **เลขที่หนังสือ / วันที่หนังสือ**, the
หนังสือ's own number and date, stamped together when it is numbered (or typed in together for a
request approved on paper).
