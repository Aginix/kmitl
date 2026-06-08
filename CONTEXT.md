# Procurement Assignment

How responsible procurement officers (เจ้าหน้าที่พัสดุ) are assigned to the three core procurement documents, so each officer can see the work assigned to them.

## Language

**PR (Purchase Request)**:
The `purchase.request` document — a request to buy/hire (ใบขอซื้อ/ขอจ้าง).

**PA (Purchase Approval)**:
The `purchase.request.approval` document — the approval step between a PR and a PO. The procurement flow is PR → PA → PO.
_Avoid_: Purchase Agreement, Work Acceptance (WA is a separate document, ตรวจรับ).

**PO (Purchase Order)**:
The `purchase.order` document — an order to buy/hire (ใบสั่งซื้อ/สั่งจ้าง).

**Assigned Officer**:
The procurement officer (เจ้าหน้าที่พัสดุ) responsible for handling a document's work. Stored in the `assigned_to` field. A PA has no officer of its own — it derives from its parent PR's officer.
_Avoid_: Responsible (that's the PR creator, `user_id`), Buyer (PO `user_id`), Approver (the PA manager who signs off, a different role), Purchase Representative.
