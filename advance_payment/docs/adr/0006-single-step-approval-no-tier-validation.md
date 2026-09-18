# Approval at `to_approve` is a single manager step; tier validation is dropped

Status: accepted (supersedes the tier-validation parts of ADR-0001; UAT-only)

## Context & Decision

ADR-0001 assumed `to_approve` would run the OCA `base_tier_validation` Endorse → Approve chain via an `advance_payment_tier_validation` bridge. That bridge is **removed**. `to_approve → waiting_transfer` is now a **single sign-off**: the อนุมัติ button on the form, restricted to `group_advance_payment_manager`, calling `action_approve()`. There is no `rejected` state — a request that does not pass goes back to `draft` (ส่งกลับแก้ไข, `action_reset_to_draft`) or to `cancel` (ยกเลิกสัญญา).

> ADR-0016 adds a named `approver_id`; ADR-0017 narrows `action_approve` itself off `group_advance_payment_manager` onto a dedicated `group_advance_payment_loan_approver` (the assigned approver, or an admin) — "restricted to `group_advance_payment_manager`" above is no longer current.

The multi-tier chain routed by org unit (Faculty: Dean → Deputy Rector; สนอ.: ผอ.กองคลัง → Deputy Rector) is **deferred**, not rejected on the merits.

## Why

- No confirmed requirement for the org-routed two-tier chain in this round; the tier definitions that shipped with the bridge were placeholders (both tiers pointed at `base.user_admin`).
- `base_tier_validation` is actively incompatible with the redesigned lifecycle. Its `get_view()` OR-s `[("review_ids", "!=", [])]` into the `readonly` modifier of **every** field node not listed in `_get_all_validation_exceptions()`, and `_allow_to_remove_reviews()` only unlinks reviews when the record moves back into `_state_from` or to `_cancel_state`. Reviews therefore persist from `to_approve` for the rest of the record's life, freezing the whole form — the borrower could never fill the expense report in `in_progress` (ADR-0003), the officer could never set `return_due_date` after approval (ADR-0004) or correct `bank_id` before the transfer (ADR-0005). Keeping the bridge would mean maintaining a per-field whitelist, or overriding `_get_tier_validation_readonly_domain()` to scope the freeze to `_state_from`, for an approval chain nobody asked for yet.
- One less module and one less external dependency on the critical approval path.

## Consequences

- `advance_payment_tier_validation` is deleted (models, `tier_definition.xml` placeholder data, view override). `agx_approval_advance_payment` now depends on `advance_payment` directly.
- The `rejected` state value disappears with the bridge's `selection_add`. Any DB where the bridge was installed must **uninstall it** before this lands, otherwise its stale `ir.ui.view` records keep xpath-ing `validation_status` / `rejected` onto the form and break form rendering.
- `_propagate_rejection_to_reference()` (defined by the bridge) is gone; `agx_approval_advance_payment` now cancels the source approval request from `_action_do_cancel()` instead, mirroring how `advance_payment_disbursement` rejects a source purchase request on cancel.
- If the org-routed chain is required later, re-introduce the bridge **with** a `_get_tier_validation_readonly_domain()` override that appends `("state", "in", self._state_from)`, and re-request validation on `action_verify` while also calling `restart_validation()` from `action_recall()`.
- **Approval hands the money over; it does not advance it.** `action_approve` creates the outbound `account.payment` and leaves it a finance-office draft (`finance_state = 'draft'`, `account.payment.state = 'draft'`). Confirming it for the bank is the finance office's own press — `finance_kmitl`'s `action_confirm_for_bank()`, which freezes the money side, numbers the ใบสำคัญจ่าย and is what makes a voucher eligible for an e-payment file — and it requires a paying account (หัวจ่าย) this module has no business choosing. `advance_payment/models/account_payment.py`'s `action_post` override closes the loop back to `action_start()` once the transfer is booked. The same applies to the inbound half in `advance.payment.return.line.action_approve`.
  - This was written as `payments.action_submit()` on both halves — a method **no module in the repo defines**. `finance_state` is the finance office's status and `account.payment.state` is Odoo's own draft/posted/cancel; there is no "submitted" payment state, so the call raised `AttributeError` the first time anybody actually pressed อนุมัติ. Both halves had been tested for their guards only, which is why it survived. The tests now run both for real.
