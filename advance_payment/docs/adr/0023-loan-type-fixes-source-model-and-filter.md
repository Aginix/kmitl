# The loan type alone fixes the source model and filters the documents offered

Status: accepted (2026-10 UAT feedback; pre-production, no migration/version bump). Supersedes parts of ADR-0007.

## Context & Decision

ADR-0007 kept the generic `reference` widget on the form. It showed a model selector next to the record picker, and the `allow_manual_reference` setting let a borrower attach a document to a loan type that declared no model. `agx_approval_advance_payment` relied on that: an AR-backed loan used `loan_type_other`, which declares no model, and the bridge carved out exceptions so the reference survived. UAT found this confusing. Borrowers picked the model by hand, and the type said nothing about which document to expect.

**The loan type alone decides.**

- The generic `reference` widget leaves the form (it stays as an invisible anchor). Each bridge shows its own typed Many2one picker (`approval_request_id`, `purchase_request_id`) when the type's `reference_model` is that bridge's model. A Reference widget with the model selector hidden is not an option: it reads `ir.model`, which regular users cannot read.
- A type with no `reference_model` means **no reference**. `allow_manual_reference` (setting and config parameter) and the AR bridge's `loan_type_other` carve-outs are removed. `is_reference_visible` is simply `bool(loan_type_id.reference_model)`.
- **Reference filter (`reference_domain`)**: the loan type also carries a domain over its model, edited with the domain editor. It may use `employee_id`, `partner_id`, `user_id` (all the borrower's), `uid` and `company_id`. It is evaluated server-side by `_get_reference_picker_domain()`, which each bridge ANDs with its mandatory baseline (AR: approved and the borrower is a participant; PR: approved). The result feeds the picker as `reference_picker_domain`, and `_check_reference_status()` re-checks the attached document against it while the loan is in draft, so RPC and import face the same filter.
- **Core drops its `purchase_request` dependency.** The `purchase.request` selection value, its picker and `loan_type_procurement.reference_model` move into `purchase_request_advance_payment`. The `loan_type_procurement` xmlid stays in core, so existing loans keep their type.

## Why

- One decision in one place: an admin configures the type, the borrower only picks a document.
- The filter belongs to master data because it is policy ("only my department's requests", "only this year's"), and it changes without a code deploy.
- Server-side evaluation is needed because the variables (`partner_id` of the borrower, not of the user) are not available to the client, and because the draft check must apply the same domain the picker showed.
- With core no longer depending on `purchase_request`, Source Reference now matches what CONTEXT.md always claimed: the core never depends on its source models.

## Consequences

- A type that used to rely on `allow_manual_reference` must now declare its model. The AR bridge's own `loan_type_approval_request` already does.
- `loan_type_procurement` declares no model until `purchase_request_advance_payment` is installed, and is then a plain standalone type.
- An invalid `reference_domain` fails loudly (in the picker and in the draft check), not silently.
