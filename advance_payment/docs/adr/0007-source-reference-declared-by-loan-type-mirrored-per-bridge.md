# The source reference is declared by the loan type and mirrored per bridge

Status: accepted (2026-07; UAT-only)

## Context & Decision

`l10n_th_gov_purchase_guarantee` derives everything from its `reference`: `reference_model` is computed+stored from it, typed mirrors (`requisition_id`, `purchase_id`) are computed+stored+indexed with `ondelete="restrict"`, and `_check_reference_status()` refuses a source document in the wrong state. advance_payment had the opposite arrangement — `reference_model` was free-text master data on `advance.payment.loan.type` — and it was **unreachable**: `loan_type_id` carried `domain="[('reference_model', '=', False)]"`, so the only loan type declaring a reference model could never be picked.

We keep **both directions**, with distinct responsibilities:

- **`loan_type_id.reference_model` = the requirement.** A `Selection` (no longer free text) whose options mirror the `advance.payment.reference` selection, so master data cannot name a model the field cannot hold. The exclusion domain on `loan_type_id` is removed.
- **`advance.payment.reference_model` = the fact.** Computed+stored from `reference`, guarantee-style, so it is searchable and usable in exception-rule domains.
- **Typed mirrors live in the bridges.** `purchase_request_advance_payment.purchase_request_id` and `agx_approval_advance_payment.approval_request_id`, both computed from `reference` via a `_compute_reference` override, `store=True index=True ondelete="restrict" compute_sudo=False`. `_rec_names_search` is extended per bridge so a loan is findable by its source document number.

Enforcement is split by failure mode: a **model mismatch** between the two is a hard `ValidationError` (`_check_reference_matches_loan_type`); a **missing** document for a type that requires one is a blocking `exception.rule` at submit (`excep_missing_reference`), matching how the module already handles missing bank account and analytic dimensions.

## Why

- Keeping the requirement on the loan type is what makes the *absence* of a reference detectable — a purely derived `reference_model` cannot express "this type must have one". Loans, unlike guarantees, are frequently standalone.
- Making it a `Selection` sourced from the field's own selection removes a silent-failure mode: a typo (`purchase_request` for `purchase.request`) used to disable the requirement with no error.
- A blocking exception rather than a `ValidationError` for the missing case keeps a half-built draft editable; a hard constraint would block the borrower mid-entry.
- `_check_reference_status()` is called from `_onchange_reference` and from the constraint **only while the agreement is in `draft`**, and the constraint is deliberately not triggered on `state`. Otherwise a reset-to-draft would fail whenever the source document had moved on with its own lifecycle — guarantee raises from inside its compute and has exactly that trap.

## Consequences

- `loan_type_id` now offers reference-backed types, so `is_reference_visible` / `_prepare_vals_from_reference` are reachable from the form for the first time. Each bridge implements `_prepare_vals_from_reference` to pull borrower, amount, reason and analytic distribution off the source — the mirror of the source-side `_prepare_advance_payment_vals` used by the "create loan from document" button. The two overlap by design; the create-time path cannot run onchanges.
- `_onchange_loan_type_id` now clears a reference the new type cannot accept, including when switching between two reference-backed types. `agx_approval_advance_payment` keeps its exception: an AR-backed loan uses `loan_type_other`, which declares no `reference_model`, so the reference must survive.
- `approval_request_id` stops being set by hand in `approval_request._prepare_advance_payment_vals` — `reference` is the single source of truth. Its FK changes from `set null` to `restrict`, and deleting a source PR/AR that backs a loan is now refused.
- `name_get` appends the source document to the number. This reads the reference, so a user who can see a loan but not its source document will get an AccessError on any list that renders it — acceptable today because both bridges only create loans for the source document's own requester.
- New stored computed columns (`advance.payment.reference_model`, `purchase_request_id`) are computed for existing rows on upgrade. `approval_request_id` is an existing column and is **not** recomputed — its values were already written from the same source, so they match.
