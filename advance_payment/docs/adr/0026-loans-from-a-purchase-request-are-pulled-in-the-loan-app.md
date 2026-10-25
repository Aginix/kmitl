# Loans against a purchase request are created only in the loan app

Status: accepted (2026-10 UAT feedback; pre-production, no migration/version bump). Amends ADR-0007; brings the purchase request in line with `agx_approval` ADR-0003.

## Context & Decision

A purchase request had a **สร้างสัญญาเงินยืม** button (`action_create_advance_payment`) that created the loan from the PR and stored it in `purchase.request.advance_payment_id`. ADR-0023 also gave the loan form a `purchase_request_id` picker, so there were two ways in. Only the button wrote `advance_payment_id`, so a loan made with the picker was invisible to the PR. `advance_payment_disbursement` keeps the PR's ใบขออนุมัติจัดซื้อ button hidden until `advance_payment_id` is `in_progress`, so that PR could never move on.

**Borrowing is pulled, not pushed**, as for approval requests. The button, `action_create_advance_payment` and `_prepare_advance_payment_vals` are removed. The borrower opens a loan in the loan app and picks the request.

- `purchase.request.advance_payment_id` is now **computed** (stored) from the loans whose `purchase_request_id` points at the request: the one that is not cancelled. Its consumers (`advance_payment_disbursement`) are unchanged.
- One request backs **one live loan**: `_check_one_loan_per_purchase_request` refuses a second one that is not cancelled. Cancelling the loan frees the request.
- The picker offers only approved requests with `payment_type = advance` and no live loan of their own. `_check_reference_status` re-checks the payment type, as the button did.

## Consequences

- **Anyone may borrow against a request**, not only its requester: someone else may borrow for the purchase. The button's requester-only check is not carried over, and picking a request no longer sets the borrower to its requester — it fills only the amount and the reason. A narrower rule can still go in the loan type's Reference filter (ADR-0023) if one is ever needed.
- **Cancelling a loan leaves the request alone.** `advance_payment_disbursement` used to reject the purchase request when its loan was cancelled; that override is removed. The request may still go ahead another way (e.g. สำรองจ่าย), and it is free for a new loan.
- On a database with loans made by the button (UAT), `advance_payment_id` keeps its stored value until a loan of that request changes, so a request whose loan was cancelled still points at it. Recompute once after deploying: `env.add_to_compute(env['purchase.request']._fields['advance_payment_id'], env['purchase.request'].search([('advance_payment_id', '!=', False)]))` then `env['purchase.request'].flush_model()` in an Odoo shell. Production never had the module.
- The PR's สัญญาเงินยืม smart button counts the loan as the reader (`advance_payment_count`, `depends_context("uid")`). A PR approver or buyer who may not read the loan sees no button, rather than a button that opens an AccessError.
