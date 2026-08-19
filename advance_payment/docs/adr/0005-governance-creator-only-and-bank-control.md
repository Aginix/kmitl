# Governance: creator-only submission, and bank-account control by finance

Status: proposed (2026-07 review; UAT-only)

## Context & Decision

**Creator-only.** The borrower must create and submit their **own** loan — no borrowing on behalf of someone else (legal liability, external-audit transparency). `requested_by` is always the current user and cannot be reassigned; only the borrower may submit. The previous manager-submit-on-behalf path and its `strict_submit` config are **removed**. A `base.group_system` admin keeps an escape hatch (create/submit on behalf) for exceptional/data cases.

**Bank-account control.** The borrower selects their own `bank_id` at creation (`draft`) and attaches a book-bank image as evidence, but **cannot change it once submitted**. After submission the loan-responsible finance officer is the only one who may correct `bank_id` (up to before the transfer), to prevent transfer errors.

## Why

- The borrower must be the one who commits to the loan — required for external-audit transparency and legal liability.
- Bank-detail mistakes cause failed / mis-directed transfers; routing post-submit edits through finance (who check against the evidence) removes that risk while still letting the borrower enter their own account first.

## Consequences

- Removes `strict_submit` (config parameter + settings UI) and the manager-on-behalf submit path; the existing "manager can submit any" test is replaced by a creator-only test plus an admin-exception test.
- `requested_by` field permission tightened — no longer editable by the manager group.
- `bank_id` is borrower-editable only in `draft`; editable by the finance officer in later states up to `waiting_transfer`; the borrower's book-bank attachment remains the evidence.
