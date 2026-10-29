# Borrowing rules are exception rules; only integrity guards stay in code

Status: accepted (2026-10-29 design session; not yet built; pre-production, no migration/version bump). Amends ADR-0024.

## Context & Decision

ADR-0024 moved the submit-time rules into `advance_payment_exception`. It kept a few hard guards in code, including the one-active-agreement rule. Borrowing policy keeps changing: which sources qualify, whether a PR may back one loan or several, how much may be borrowed. Each change that lives in code needs a release. Production use also showed that rigid locks make daily work hard.

**Every borrowing *policy* is an `exception.rule`.** Administrators can switch a rule on, change it or drop it from the Exception Rules menu. All of them are blocking and are checked at submit and again at Verify.

| Rule | Module | Shipped |
|---|---|---|
| One active agreement per borrower (ADR-0001) | `advance_payment_exception` | active |
| Source must be approved | each source bridge | active |
| PR must have payment type เงินยืม | `purchase_request_advance_payment` | active |
| A PR backs a single loan (ADR-0026) | `purchase_request_advance_payment` | **inactive** |
| Loan fits the Borrowing headroom | `advance_payment_budget_commitment` | active |
| Source's commitment is reserved / partly used | `advance_payment_budget_commitment` | active |

**Integrity guards stay in code.** These are the loan type matching its source's document kind (`_check_reference_matches_loan_type`) and a bank account before Verify. They protect data shape rather than policy. Switching one off would only let malformed records in.

## Why

- Policy belongs to the institute, so administrators should own it without a deploy.
- A rule set inactive keeps a past decision one click away. The single-loan PR rule is the first example.

## Consequences

- A rule runs with the rights of whoever submits or verifies, and the borrower usually cannot read the source. Each rule therefore reads a technical flag that is computed with system rights, as `exceeds_ar_headroom` already does, and never a raw path into AR/PR/commitment.
- The one-active rule is no longer enforced when `advance_payment_exception` is absent. The module is `auto_install`, so this happens only if someone removes it on purpose.
- An administrator can switch off a regulation. That is intended. The audit trail is the rule's own record.
