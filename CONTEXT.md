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
The procurement officer (เจ้าหน้าที่พัสดุ) responsible for handling a document's work. Stored in the `assigned_to` field. A PA has no officer of its own — it derives from its parent PR's officer.
_Avoid_: Responsible (that's the PR creator, `user_id`), Buyer (PO `user_id`), Approver (the PA manager who signs off, a different role), Purchase Representative.

**God Mode (PA edit while `to_approve` / `approved`)**:
An elevated, narrow edit surface on the พจ.1 (PA) while the record is in state `to_approve` or `approved` (never `rejected` / `cancelled`). Members of the security group `purchase_request_approval_godmode.group_pa_godmode` may amend six PA header fields (`partner_id`, `procurement_type_id`, `procurement_method_id`, `payment_type`, `vat_included`, `tax_id`) and three line fields (`product_qty`, `price_unit`, `name`) on `purchase.request.approval.line` **without transitioning the PA state**. Adding/removing lines is not allowed; `product_id`, `product_uom_id`, `title`, `description`, and audit columns (`verified_by`, `approved_by`, `date_verified`, `date_approved`, `assigned_to`) stay locked. An `@api.constrains` rail enforces `sum(open PAs.amount_total) ≤ budget_commitment.amount` — covering the KMITL Project shared-commitment case. God-Mode writes are **silent**: no chatter entry, no field tracking, no follower notification is emitted (for either direct edits or workflow buttons the god-mode user presses). When a god-mode edit touches a field visible in the พจ.1 PDF, the stored `<pa.name>.pdf` `ir.attachment` is unlinked and re-rendered so Sarabun's export/print serves the corrected document. Downstream PO/DR/bill artefacts are **not** re-derived — God Mode is a surgical PA correction, not a re-issue. Sarabun sync of God-Mode edits is owned by a separate branch which detects changes by diffing the `vals` dict inside its own `write()` override. See [ADR-0006](docs/adr/0006-pa-godmode-edit.md).
_Avoid_: treating God Mode as a re-approval, a cancel-and-reissue, or a way to add/remove line items; assuming `title`/`description` are editable in God Mode (they are not).
