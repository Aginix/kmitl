# Disbursement

The disbursement request (DR, ใบขอเบิก) and the workflow it passes through:
`draft → submitted → signed → verified → approved`, after which the accounting /
finance bridges raise bills and payments. At `verified` the request must clear a
**two-approver step** before it is approved and the budget is committed.

## Language

**Disbursement Request** (DR, ใบขอเบิก):
The document requesting a disbursement. Always pays a name list (multi-partner);
one line per payee. Tracked as `disbursement.request`.
_Avoid_: Payment (that is the downstream document), Voucher.

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
one — obligates and consumes the budget.
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
