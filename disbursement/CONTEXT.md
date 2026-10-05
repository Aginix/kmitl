# Disbursement

The disbursement request (DR, ใบขอเบิก) and the slip's own lifecycle:
`draft → submitted → signed → in_progress → done` (or `cancel`). Once the head of the
requesting unit has signed, the request is handed to the central offices'
**work stations** (`disbursement_wst`), which walk it through verification, approval,
billing and payment while it is `in_progress`. Core owns only the requester's side and
the capabilities the stations drive; it names no station.

## Language

**Disbursement Request** (DR, ใบขอเบิก):
The document requesting a disbursement. Always pays a name list (multi-partner);
one line per payee. Tracked as `disbursement.request`.
_Avoid_: Payment (that is the downstream document), Voucher.

**Verify** (ตรวจสอบ):
The disbursement officer's check on a signed request, performed at the `verify`
work station (`disbursement_wst_verify`). Distinct from *approve* — the officer
checks, the approvers authorise. The acting officer is the step's `acted_by_id` — not
`assigned_to`, who was merely *assigned* the verification and may be someone else once
takeover is allowed.
_Avoid_: Review, Approve, Assigned officer.

**Under verification** (`under_verification`):
Where the verification officer may return the request to the requester or its source
document for correction. Core says only `signed`; the verify station widens it to
"in progress at the `verify` station".

**Return to verification** (ตีกลับไปตรวจสอบ):
Whoever holds the request at a later station sends it back to the verification
officer with a reason. The route is walked again from its first station; the budget
obligation is kept and a re-approval does not cut it twice.
_Avoid_: Reject (there is no separate reject), Cancel (terminal).

**Head-of-department approval** (การลงนามของหัวหน้าส่วนงาน):
The signature that moves a submitted request to `signed`, performed by the head
of the requesting unit. Obtained through e-Saraban when `disbursement_sarabun` is
installed, so it is the one signature the DR does not stamp itself and the one
rendered by Saraban's own endorsement block. It is not a work station.
_Avoid_: ผู้อนุมัติเบิกจ่าย (reserved for the post-bill payment authoriser — a
different authority whose signature prints on the same page).

**Work station / route / step**:
See `disbursement_wst/CONTEXT.md`. The two approvals, the Finance Director's and the
Rector-delegated approver's (the latter alone obligates and consumes the budget), are
stations (`disbursement_wst_approve_finance`, `disbursement_wst_approve_rector`), as
are the work queues and the signature block printed on the ใบขอเบิก.

**Signature block** (บล็อกลายเซ็น):
The grid of signatures at the tail of the printed ใบขอเบิก — one cell per signing
station passed, three per line, each showing the signer's ลายเซ็น, ชื่อ, ตำแหน่ง and วันที่.
Self-limiting: a station that has not been passed prints nothing. Each cell is a frozen
snapshot taken at the moment of acting, so later HR edits never rewrite a signed
request (see ADR 0002; the rows are now `disbursement.step` records in
`disbursement_wst`). Saraban's own block prints above it.
_Avoid_: Approval history (that is the chatter and the steps), เกษียน trail (Saraban's
audit trail, which is not printed).
