==========================================
KMITL Advance Payment — e-Saraban Approval
==========================================

This module routes the approval step of an Advance Payment agreement
(สัญญายืมเงิน) through e-Saraban (สารบรรณ) instead of a single manual click.

It reuses the base module's ``to_approve`` state as the circulating state —
no new state is added to ``advance.payment``. The loan officer
(เจ้าหน้าที่งานเงินยืม) raises a หนังสือ ("สร้างหนังสือ") from ``to_approve``;
the base manual "อนุมัติ" button is hidden once this module is installed.

Outcome mapping
================

- **Completed** (ลงนามครบ): calls the base ``action_approve()`` — creates the
  disbursement payment and moves the loan to ``waiting_transfer``.
- **Returned** (ตีกลับ): the loan goes back to ``to_verify`` for revision.
- **Rejected** (ปฏิเสธ, terminal): the loan is cancelled with the approver's
  reason.
- **Cancelled** (ยกเลิกการส่ง) / **Recalled** (ดึงกลับ): the loan stays at
  ``to_approve``, ready to be re-sent.

See ``advance_payment/docs/adr/0011-approval-via-e-saraban.md`` for the full
rationale.

Configuration
=============

The seed route (``route_template_advance_payment``) targets a single,
holderless ``sarabun.position`` (``position_advance_payment_approver``).
Before go-live, assign the real เจ้าหน้าที่งานเงินยืม as its holder under
*Sarabun ▸ Configuration ▸ Positions*.

An org-routed multi-tier approval chain, if required later, can be added
purely through additional Sarabun route configuration — no further code
change to this module is expected.

Usage
=====

- The loan officer opens an agreement at ``รออนุมัติ`` (``to_approve``) and
  clicks "สร้างหนังสือ" to raise the หนังสือ.
- The หนังสือ routes to the approving position; its outcome drives the loan
  forward per the mapping above.

Credits
=======

Authors
~~~~~~~

* Aginix Technologies
