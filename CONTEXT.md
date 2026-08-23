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

**ตีกลับ/แก้ไข (PA-to-PR return, keep-number)**:
A negative-path lifecycle transition from พจ.1 (PA) `draft` back to พ.1 (PR) `to_submit` for revision, initiated by the PA manager via the "ตีกลับ/แก้ไข" button (wizard collects only a mandatory reason). Effect: PA parks in `pending_pr` (name/number **preserved** for reuse), PR's active sarabun is **soft-voided** (see below), PR moves to `to_submit` (budget commitment intact), and the user is redirected to the PR form. When the same PR's sarabun re-completes, `_transition_after_sarabun_approve` **re-syncs all copied PA fields from the (possibly edited) PR** and flips `pending_pr → draft`. Cross-model return (PA → PR), deliberately distinct from Sarabun-side ตีกลับ ([agx_sarabun ADR-0006](agx_sarabun/docs/adr/0006-recall-split-pullback-vs-cancel-send.md)) which stays inside `sarabun.document`. The full resync **contradicts [ADR-0004](docs/adr/0004-pa-owns-copied-data.md)'s "free to diverge" intent** on purpose — return = restart, not tweak. See [ADR-0007](docs/adr/0007-pa-return-for-revision.md).
_Avoid_: confusing with Sarabun ดึงกลับ / ตีกลับ (those don't cross model boundaries); assuming God-Mode edits on the PA survive a return (they don't — resync overwrites); assuming this cancels the PA (it doesn't — `name` is kept for reuse).

**`pending_pr` (PA state — waiting-for-PR-revision)**:
A PA lifecycle state indicating "parked, waiting for PR revision cycle to complete". Not in the drawio v2 model referenced by [ADR-0005](docs/adr/0005-post-sarabun-state-split.md) — a scoped extension for the ตีกลับ/แก้ไข negative path. The PA's `name` (registered พจ.1 number) is retained across the parking so the same document is reused when it flips back to `draft`. Hidden from the statusbar (`statusbar_visible` does not include it).
_Avoid_: confusing with `sarabun_returned` (that's a Sarabun-approver return via the PA's OWN sarabun cycle); confusing with `cancelled` (terminal); leaving the state key unqualified (`pending_pr` says explicitly "waiting on PR", distinguishing it from a bare `returned`).

**Soft-void sarabun (`state=cancelled` with the number kept)**:
Writing `sarabun.document.state = 'cancelled'` directly via `sudo` write, **without** calling `_void_register` — so the register number stays `used`, and the doc can later be revived by `_restart_chain + state=draft`. Used by `_cancel_request_sarabun` on the PA to park the PR's sarabun during a ตีกลับ/แก้ไข cycle. Semantically distinct from [agx_sarabun ADR-0006](agx_sarabun/docs/adr/0006-recall-split-pullback-vs-cancel-send.md)'s "cancelled = terminal + voided number"; a real `action_recall` cancel and a soft-void look identical at the `state` field. This is a known semantic quirk accepted for pragmatic UX — see [ADR-0007](docs/adr/0007-pa-return-for-revision.md).
_Avoid_: assuming `state=cancelled` on a sarabun implies its number is voided (check `register_number_id.state` if it matters); using this pattern outside the ตีกลับ/แก้ไข flow (real cancels go through `action_recall`).

## Known limitations (accepted, revisit later)

- **`_resume_returned_sarabun` picks the latest cancelled sarabun by `id`.** If a PR has multiple cancelled sarabun documents from unrelated histories (e.g., a real `action_recall` earlier in the record's life), the revive picks whichever has the highest id. Real-world rare because a real recall requires `not has_signed`, but the search is not tightened to identify only soft-voided ones. Acceptable today.
- **PA `draft` has no direct Cancel button.** After the ตีกลับ/แก้ไข wizard was simplified to keep-number only, cancelling a PA that is still in `draft` requires: click ตีกลับ/แก้ไข first (PA → `pending_pr`, PR → `to_submit`), then Cancel from the PR side. The PA stays orphaned in `pending_pr` unless an admin explicitly cleans it up. Acceptable today; a future iteration may auto-cascade PA `pending_pr` → `cancelled` when the PR cancels.
