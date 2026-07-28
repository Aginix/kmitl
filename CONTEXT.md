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

**God Mode (PA post-approval edit)**:
An elevated, narrow edit surface on the พจ.1 (PA) once it has reached `approved`. Members of the security group `purchase_request_approval_godmode.group_pa_godmode` may amend eight PA header fields (`title`, `description`, `partner_id`, `procurement_type_id`, `procurement_method_id`, `payment_type`, `vat_included`, `tax_id`) and two line fields (`product_qty`, `price_unit`) **without transitioning the PA out of `approved`**. Adding/removing lines and touching `product_id` / `product_uom_id` / audit columns (`verified_by`, `approved_by`, `date_verified`, `date_approved`, `assigned_to`) is not allowed. An `@api.constrains` rail enforces `sum(approved PAs.amount_total) ≤ budget_commitment.amount` for the underlying commitment, covering the KMITL Project shared-commitment case. Downstream PO/DR/bill artefacts are **not** re-derived — God Mode is a surgical PA correction, not a re-issue. Sarabun sync of God-Mode edits is owned by a separate branch which detects them via PA `write()` override + `tracking=True` on the unlocked fields. See [ADR-0006](docs/adr/0006-pa-godmode-edit.md).
_Avoid_: treating God Mode as a re-approval, a cancel-and-reissue, or a way to add/remove line items.
