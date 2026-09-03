# Governance: creator-only submission, and bank-account control by finance

Status: proposed (2026-07 review; UAT-only)

## Context & Decision

**Creator-only.** The borrower must create and submit their **own** loan — no borrowing on behalf of someone else (legal liability, external-audit transparency). `requested_by` is always the current user and cannot be reassigned; only the borrower may submit. The previous manager-submit-on-behalf path and its `strict_submit` config are **removed**. A `base.group_system` admin keeps an escape hatch (create/submit on behalf) for exceptional/data cases.

> Superseded field names: ADR-0010 relaxes creator-only for a `user`-tier drafter; ADR-0014 retypes `requested_by` into `employee_id` (the borrower) + `user_id` (the drafter, "ผู้จัดทำ") and revives a `strict_submit`-like toggle as Strict mode, scoped to draft-on-behalf only (not submission, which stays creator-only via `_check_submit_permission`).

**Bank-account control.** The borrower selects their own `bank_id` at creation (`draft`) and attaches a book-bank image as evidence, but **cannot change it once submitted**. After submission the loan-responsible finance officer is the only one who may correct `bank_id` (up to before the transfer), to prevent transfer errors.

## Why

- The borrower must be the one who commits to the loan — required for external-audit transparency and legal liability.
- Bank-detail mistakes cause failed / mis-directed transfers; routing post-submit edits through finance (who check against the evidence) removes that risk while still letting the borrower enter their own account first.

## Consequences

- Removes `strict_submit` (config parameter + settings UI) and the manager-on-behalf submit path; the existing "manager can submit any" test is replaced by a creator-only test plus an admin-exception test.
- `requested_by` field permission tightened — no longer editable by the manager group.
- ADR-0014 renames this field to `employee_id` (`hr.employee`) and moves the creator-only comparison to `employee_id.user_id` vs. the new `user_id` field.
- `bank_id` is borrower-editable only in `draft`; editable by the finance officer in later states up to `waiting_transfer`; the borrower's book-bank attachment remains the evidence.
- ADR-0015 makes `bank_id` default itself to the borrower's first `res.partner.bank` whenever `employee_id` changes, so the borrower never picks it by hand; the officer's correction window above is what keeps that safe.
