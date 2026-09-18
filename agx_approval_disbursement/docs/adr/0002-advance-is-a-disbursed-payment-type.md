# Advance is a disbursed payment type; one DR per payment type, chosen by wizard

Status: accepted (2026-09) — **supersedes** [agx_approval ADR-0002](../../../agx_approval/docs/adr/0002-payment-type-per-actual-row.md) §"Anti-double-pay" / "Billing → one DR (interim)" and the DR-side of [agx_approval ADR-0003](../../../agx_approval/docs/adr/0003-per-participant-borrowing-against-an-approved-request.md); the rest of both stands.

## Context & Decision

`agx_approval` ADR-0002 excluded `advance` (เงินยืม) rows from disbursement entirely — the money was already out as a loan, so billing it again looked like double payment. In practice, การเงิน still needs to **verify and evidence** the เงินยืม spend and **ตัดจ่ายงบประมาณ** for it through the same document trail as จ่ายตรง/สำรองจ่าย. So เงินยืม now goes through a Disbursement Request too, with `payment_type='advance'`.

Since one DR could previously only carry one `payment_type` header (direct/prepaid shared one DR as an interim per ADR-0002), and the requirement is now **1 ใบเบิก = 1 ประเภทการจ่ายเงิน**, `action_create_disbursement_request` becomes a **dispatcher**: it opens `disbursement.type.wizard`, offering only the payment types that (a) have at least one allocation row and (b) do not already have a non-cancelled DR. Confirming creates exactly one single-type, multi-partner DR. The header button stays visible (and `action_bill` fires once, on the first DR) until every disbursable type has a DR — tracked by the computed `has_pending_disbursement_type`.

## Consequences

- `_billable_allocations()` is replaced by `_allocations_of_type(payment_type)`; every payment type, including `advance`, can become DR lines.
- `_prepare_disbursement_request_vals` takes `payment_type` and stamps it on the DR header — no more hardcoded `direct`.
- `billing_status` is redefined purely in terms of pending types: `no` (no DR yet), `partial` (some pending types remain), `full` (none do) — independent of how far any individual DR has progressed through its own approval workflow.
- **Known risk:** an เงินยืม DR now produces its own payment-execution trail (bank transfer/voucher) alongside the original loan disbursement. Nothing in this change reconciles the two — the borrower's สัญญายืม and its clearing (`advance_payment` module) are untouched and may, if finance actually re-pays the DR, produce a duplicate cash movement. Guarding against that is explicitly out of scope here; it belongs to whatever eventually wires เงินยืม clearing to this DR.
- **`agx_approval_advance_payment` is deleted outright** (not deprecated) — its per-recipient `advance_payment_id` on the allocation row, borrowing-headroom fields, and AR↔advance.payment bridge are gone. `payment_type='advance'` remains selectable (defined in base `agx_approval`); only the bridge that linked it to a specific สัญญายืม is removed. A DB that has it installed must `-u`ninstall it first — pre-production, so no migration script is provided.
- `_voucher_groups` (งบหน้าใบสำคัญคู่จ่าย) still excludes `advance` — untouched, out of scope.
