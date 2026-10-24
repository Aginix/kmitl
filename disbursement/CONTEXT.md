# Disbursement

> **Being replaced by the station model — see `disbursement_wc/CONTEXT.md` and
> `disbursement_wc/docs/adr/0001-*`.** The DR's own state is reduced to ฉบับร่าง →
> ยืนยัน → ลงนาม → in_progress → เสร็จสิ้น (+ ยกเลิก); the middle is carried by
> **สถานี** and the money by **ขั้นการชำระ**. The entries below on Verify, the
> two-approver step, `approval_state`, Reject and the Approver queue describe the
> workflow being retired and are not yet rewritten. Payee, Payee type, Source document,
> Fiscal year, Budget control, Stand-alone request and Signature block still hold.

The disbursement request (DR, ใบขอเบิก) and the workflow it passes through:
`draft → submitted → signed → verified → approved`, after which the accounting /
finance bridges raise bills and payments. At `verified` the request must clear a
**two-approver step** before it is approved — and, under **budget control**,
the budget is consumed.

## Language

**Disbursement Request** (DR, ใบขอเบิก):
The document requesting a disbursement. Always pays a name list (multi-partner);
one line per payee, all of one **payee type**. Tracked as `disbursement.request`.
_Avoid_: Payment (that is the downstream document), Voucher.

**Payee** (ผู้รับเงิน):
The partner a request line pays. Payees exist only on the lines — the request
itself has no partner — and each needs a bank account before the request is
submitted, unless it is paid in cash (an exception manager then lets it through).
A requester manages a payee's accounts from the draft request itself — adds
one or corrects one, never removes one (`disbursement_partner_bank`); every
change is logged on the payee's chatter with its old and new values.
_Avoid_: Partner of the request, Vendor (only some payees are vendors).

**Payee type** (ประเภทผู้รับเงิน):
The one partner type (บริษัท / บุคลากรภายใน / นักศึกษา / อื่น ๆ) every payee on a
request belongs to, chosen on the request. A source document paying several
types becomes one request per type.
_Avoid_: Partner type single/multi (the retired header switch).

**Source document** (เอกสารต้นทาง):
The document a request was raised from — a purchase order, a purchase request
approval, an approval request — held by the bridge that raised it and printed as
อ้างอิง. A stand-alone request has none.
_Avoid_: Reference, Ref (the retired free-text and generic-link fields).

**Fiscal year** (ปีงบประมาณ):
The year a request books to, chosen on the request (it defaults to the year of
its date) and the year in its number `DR/<yy>/…`. Under budget control it
leads: only that year's commitments can be linked, and changing the year drops
the linked commitment.
_Avoid_: Date range (the year is no longer derived from the date).

**Budget control** (การควบคุมงบประมาณ):
A request charged to a budget code (รหัสงบประมาณค่าใช้จ่าย) and consumed on the
Rector-delegated approval, reversed on cancel — either through a linked reserved
budget commitment (ใบจองงบประมาณ) or, for a **direct claim**, straight from the
budget pool. Optional — provided by `disbursement_budget` (see ADR 0003).
_Avoid_: Budget check (that is the availability check inside the budget module).

**Direct claim** (ตั้งเบิกตรง):
A request raised on the strength of a memo (หนังสือบันทึกข้อความ) produced outside
the system. It skips e-Saraban — the external memo already holds the head of
department's signature — and goes straight from submit to `signed`. A budget
reservation is optional: with one it is consumed like any request; without one
it carries its own dimensions and budget code and, under budget control, is
consumed directly from the pool on the Rector-delegated approval (see ADR 0005;
opt-in via `disbursement_direct_claim`).
Any payment type may be a direct claim; only users granted the ตั้งเบิกตรง right
may raise one.
_Avoid_: จ่ายตรง / Direct paid (that is the **payment type** — paid straight to
the payee rather than as an advance or a prepayment), Stand-alone request (a
request without budget control at all).

**Memo number** (เลขที่หนังสือ):
The number of the official memo (หนังสือบันทึกข้อความ) authorising the request.
Typed in by hand on a direct claim; on any other request it is the number
e-Saraban issues to the request's หนังสือ, filled in the moment it is issued.
_Avoid_: Ref / Reference (the retired free-text field, ADR 0004), Number (that
is the request's own `DR/<yy>/…`).

**Taxable** (มีภาษี):
Whether the request's lines carry taxes at all — VAT and withholding tax alike.
A request paid to a company (บริษัท) is always taxable; an advance or a
prepayment starts out not taxable. A request that is not taxable has no taxes
on any line.
_Avoid_: VAT flag (it covers withholding tax too).

**Stand-alone request** (ใบขอเบิกแบบอิสระ):
A DR raised without budget control and without a source document — only the
request itself, its payees and its financial dimensions.
_Avoid_: Manual DR, Free DR.

**Verify** (ตรวจสอบ):
The disbursement officer's check that moves a signed request to `verified`
(**Validate** button). Distinct from *approve* — the officer checks, the
approvers authorise. The acting officer is recorded in `verifier_id`, which is
whoever pressed the button — not `assigned_to`, who was merely *assigned* the
verification and may be someone else once takeover is allowed.
_Avoid_: Review, Approve, Assigned officer.

**Finance Director approval** (การอนุมัติของ ผอ.กองคลัง):
The **first** of the two required approvals, performed by the Finance Division
Director. Recorded in `finance_approver_id`. Belongs to
`disbursement.group_disbursement_finance_director`. Touches no budget.
_Avoid_: Manager approval, Verify.

**Rector-delegated approval** (การอนุมัติของผู้ได้รับมอบอำนาจอธิการบดี):
The **second/final** approval, performed by the approver holding the Rector's
delegated authority. Recorded in `rector_approver_id`. Belongs to
`disbursement.group_disbursement_rector_delegate`. This approval — and only this
one — consumes the budget, when the request is under **budget control**.
_Avoid_: Director approval (ambiguous), Second approval (state it by role).

**Reject** (ตีกลับ):
Either approver's action, during their turn, that returns the pending approval
with a reason. The request stays at `verified`; `approval_state` becomes
`rejected` and a Todo goes to the requester. Re-sent for approval with
**Request Approval Again**.
_Avoid_: Return to verification (a separate flow that bounces to `signed`),
Cancel (terminal).

**`approval_state`**:
The two-approver sub-workflow, kept separate from the request's real `state`
(which stays `verified` throughout): `none → pending_finance → pending_rector →
approved` / `rejected`. Separate from `state` so the accounting / finance
bridges and the return flow, which key off `state`, are untouched.
_Avoid_: workflow_state (that is the accounting module's name), status.

**Two-approver step**:
The requirement that every DR — regardless of amount — is approved by the
Finance Director then the Rector-delegated approver, in that order, before it
reaches `approved`. Each pending approval is surfaced to its approver group as
an execution Todo in the shared notification center.
_Avoid_: Tier validation (deliberately not used — see ADR 0001), dual sign-off.

**Approver queue** (เมนูผู้อนุมัติ):
The approver's work screen under the Approver (ผู้อนุมัติ) menu. Split by role
into two queues — **Awaiting Finance Director** (รอ ผอ.กองคลัง, DRs at
`pending_finance`) and **Awaiting Rector Delegate** (รอผู้รับมอบอำนาจ, DRs at
`pending_rector`) — each showing only the requests at that approver's turn. The
**Approved** (อนุมัติแล้ว) list is a permanent history of every request the
Finance Director and/or the Rector-delegated approver has approved (keyed off the
approver stamps, so it stays visible through the bill/payment stages), with
filters. Separate from the requester's "Disbursement Requests" list and the
officer's "Verification" (หมวดตรวจ) list.
_Avoid_: Inbox (that is the Todo notification center), a single merged queue.

**Head-of-department approval** (การลงนามของหัวหน้าส่วนงาน):
The signature that moves a submitted request to `signed`, performed by the head
of the requesting unit. Obtained through e-Saraban when `disbursement_sarabun` is
installed, so it is the one signature the DR does not stamp itself and the one
rendered by Saraban's own endorsement block.
_Avoid_: ผู้อนุมัติเบิกจ่าย (reserved for the post-bill payment authoriser — a
different authority whose signature prints on the same page), Approve (the head
signs; the two-approver step authorises).

**Signature block** (บล็อกลายเซ็น):
The grid of signatures at the tail of the printed ใบขอเบิก — one cell per step
taken, three per line, each showing the signer's ลายเซ็น, ชื่อ, ตำแหน่ง and วันที่.
Self-limiting: a step that has not happened prints nothing. Each cell is a frozen
snapshot taken at the moment of signing, so later HR edits never rewrite a signed
request (see ADR 0002). Saraban's own block prints above it.
_Avoid_: Approval history (that is the chatter and the approver stamps), เกษียน
trail (Saraban's audit trail, which is not printed).

**Printed request** (ใบขอเบิกพิมพ์):
The standalone ใบขอเบิก PDF in the Print menu, signature block included. It lives
in `disbursement_pdf`, not in the core, and leaves the Print menu once
`disbursement_sarabun` is installed: the หนังสือ is then the official document
(ADR 0006).
_Avoid_: Portal / Preview (the `/my/disbursement` portal that framed it is gone).

**Document preview** (ตัวอย่างเอกสาร):
An on-screen, watermarked rendering of the หนังสือ a request would send to
e-Saraban, opened from the form before Submit to Sarabun. Not an official
document: it has no number and no signatures, and nothing is saved. Once the
หนังสือ exists the same button opens the หนังสือ's own preview (ADR 0007).
_Avoid_: Printed request (that is the ใบขอเบิก, not the หนังสือ), Draft หนังสือ (a
real, saved `sarabun.document` in state `draft`).
