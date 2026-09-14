# Approval Document Checklist (เอกสารแนบที่ใช้ในการเบิกจ่าย)

Extension of `agx_approval`. Each **Approval Category (ประเภทคำขออนุมัติ)** needs a
different set of supporting documents to reimburse — ใบเสร็จ, สำเนาบัตรประชาชน,
ใบสำคัญรับเงิน. This module lets a category declare that set, materialises it on each
request as a checklist, and blocks the hand-off to finance while a *required* document
is still missing.

The documents belong to the **actual-expense stage**, not the plan stage: they are
attached while the request sits in `approved` (บันทึกค่าใช้จ่ายจริง) and are what makes
the request billable. Nothing in this module touches the plan, the budget reservation or
the e-Saraban routing — those all happen before any receipt exists.

Base `agx_approval` is left byte-identical; everything here is `_inherit` + view
inheritance.

## Language

**Disbursement Document Requirement (เอกสารแนบที่ใช้ในการเบิกจ่าย — ฝั่งตั้งค่า)**:
A document (`approval.category.disbursement.document`) a category declares that requests
of its kind must produce to be reimbursed, each marked **จำเป็น** or optional. Configured
inline per category, not a shared doctype master.
_Avoid_: file type (that's MIME), document template, plan attachment

**Disbursement Document Checklist (รายการเอกสารแนบที่ใช้ในการเบิกจ่าย — ฝั่งคำขอ)**:
The per-request materialised list (`approval.request.disbursement.document`) — a
**snapshot** of the category's requirements taken at category selection, structurally
fixed (the requester attaches files but cannot add/remove/rename/re-flag rows). A
required row is satisfied by ≥1 file. Filled in `approved`; missing required documents
hard-block `approved → to_disburse` (ส่งให้การเงินตรวจสอบ).
_Avoid_: live-linked requirement, plan attachment

**Other Attachments (เอกสารแนบอื่นๆ)**:
The untyped `attachment_ids` bucket on the request (base `agx_approval`) — plan-stage
files that fit no declared requirement. `agx_approval_disbursement`'s
"เอกสารแนบสำหรับการเบิก" (`disbursement_attachment_ids`) is its disbursement-stage
counterpart; the checklist sits beside it, typed.
_Avoid_: disbursement document checklist

## Decisions

- **Snapshot, not live link** — rows are copied from the category the way `line_ids` and
  `participant_ids` are, so a category edited months later cannot change what an
  in-flight request was asked for. Re-synced only when `category_id` itself changes, plus
  a one-shot top-up on entering `approved` for requests that predate this module.
  Requests already sitting in `approved` at install time never cross that write —
  `approved` is the actual-expense stage they linger longest in — so `post_init_hook`
  materialises their rows once, or the gate would pass silently on exactly the
  population the top-up was written for.
- **Explicit gate, not an `exception.rule`** — `detect_exceptions()` re-evaluates *every*
  rule of `approval.request`, including `excep_submit_date_outside_fy` (which compares
  **today** against ปีงบประมาณ). A request approved late in ปีงบ N and reimbursed after
  1 ต.ค. is entirely normal and would have been blocked for an unrelated reason. See
  `approval.request._check_disbursement_documents`.
- **Attachments are stamped onto their checklist row** — `many2many_binary` uploads with
  `res_id = 0` while the row is unsaved, and `ir.attachment.check()` then hides such a
  file from everyone but its uploader. `_adopt_orphan_attachments` re-points them so the
  ACL falls back to read access on the row, which the verifier and finance both have.
  That also moves the files out from under `approval_request_own_rule`, which only
  fences `res_model = approval.request` — so `security/security.xml` re-fences the row
  model with the same Own/User pair, or a self-service user could pull any requester's
  สำเนาบัตรประชาชน straight off `/web/content/<id>`.
