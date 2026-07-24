# Procurement Assignment

How responsible procurement officers (เจ้าหน้าที่พัสดุ) are assigned to the three core procurement documents, so each officer can see the work assigned to them.

## Language

**PR (Purchase Request, พ.1)**:
The `purchase.request` document — ใบขอให้จัดหา, a unit's request to procure, approved by the หัวหน้าส่วนงาน (department head). It is the *ask*; it does not itself authorise buying.

**PA (Purchase Approval, พจ.1)**:
The `purchase.request.approval` document — ขออนุมัติจัดซื้อจัดจ้าง, the separate step that authorises actually buying, raised after the PR is approved. Its data is *copied* from the PR but may legitimately diverge (vendor, tax, procurement type can be re-edited on the PA) and it has its own approver — so PA is a **separate model, deliberately never merged into PR**. It carries its **own copied columns + line model** (ADR-0004) so those edits never mutate the PR. The procurement flow is PR → PA → PO.
_Avoid_: Purchase Agreement; Work Acceptance (WA is a separate document, ตรวจรับ); treating PA as a mere view/report of the PR.

**PO (Purchase Order)**:
The `purchase.order` document — an order to buy/hire (ใบสั่งซื้อ/สั่งจ้าง).

**Procurement Mode (โหมดจัดหา)**:
A flag chosen on the PR for who sources vendor and price: *ให้พัสดุจัดหา* (the procurement officer sources them — the requester leaves vendor/VAT blank, and they are filled later on the PA) or *ผู้ขอระบุเอง* (the requester specifies vendor + VAT up front). It replaces the old amount-based vendor-required rule; budget is never mandatory at PR creation regardless of mode.
_Avoid_: deriving "must specify a vendor" from an amount threshold.

**Assigned Officer**:
The procurement officer (เจ้าหน้าที่พัสดุ) responsible for handling a document's work. **Each of PR, PA, and PO carries its own independent Assigned Officer** — PA does *not* derive from its parent PR; PA-stage work is typically claimed by a new officer when it moves into the buying stage, and unassigning on one document never affects the other. Stored in `assigned_to` on PR and PO; stored in `pa_assigned_to` on PA (because PA's `assigned_to` is the [[Approver]]).
_Avoid_: Responsible (that's the PR creator, `user_id`), Buyer (PO `user_id`), Approver (the PA manager who signs off, a different role), Purchase Representative.

**Approver** (PA):
The manager (`group_purchase_request_manager`) who signs off the พจ.1. Stored in `purchase.request.approval.assigned_to`. Distinct from the [[Assigned Officer]] — an Approver *authorises* the buying; an Assigned Officer *does the work*.
_Avoid_: Assigned Officer; confusing this with `pa_assigned_to`.
