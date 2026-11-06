# A budget commitment is a source, and the loan stores its commitment

Status: accepted (2026-11-05 feedback review). Amends ADR-0025 and ADR-0029: the loan
still never reserves, but it now records which commitment it draws on.

## Context & Decision

The finance office wants loans to hang off the ใบจองงบประมาณ (BC) first. A BC could not
tell how much had been borrowed against it or list its loans: the loan reached the
commitment only through its source, recomputed on every read, and nothing stored the link.

- **A BC is a Source Reference.** `advance_payment_budget_commitment` adds
  `budget.commitment` to `reference` and seeds a loan type for it. The borrower types the
  BC number like an AR/PR number.
- **Only a BC no live source holds.** A BC cited directly must not be drawn on by a live
  (not cancelled/rejected) source of another kind — today an AR or PR. When one exists
  the loan must cite it, so the agreement names the matter it borrows for. A BC held only
  by a project or procurement plan counts as having none. This is a blocking Borrowing
  rule (ADR-0030), not a lookup filter.
- **`budget_commitment_id` is stored.** It is the reference itself when that is a BC,
  otherwise the source's own commitment. It follows the source while the loan is a
  draft and is re-read and fixed at submit.
- **Borrowed amount (ยอดยืมแล้ว)** on the BC is the sum of its submitted, not cancelled
  loans. Drafts do not count. Borrowing headroom = BC amount − borrowed amount. The BC
  shows both and a สัญญายืมเงิน button when it has any loan. The figures are computed
  as the system; the list opens under the reader's own rights.

## Considered options

- *Keep AR/PR as the only sources and just store the commitment.* Rejected: a
  standalone reservation (budget ADR-0010) still could not back a loan.
- *BC replaces AR/PR.* Rejected: the AR/PR explains what the money is for.
- *Let a BC that an AR/PR holds be cited directly too.* Rejected by the office: the
  loan must name the matter when a document for it exists.
- *Commitment follows its source for the loan's whole life.* Rejected: a re-pointed
  source would move a submitted loan's debt to another commitment silently.
- *Count drafts in the borrowed amount.* Rejected: an abandoned draft would eat the
  headroom.

## Consequences

- Two drafts can each pass submit against the same headroom. The second is caught at
  Verify, where the rule runs again.
- The new column is filled by Odoo for every existing loan on `-u`, from its source's
  current commitment.
