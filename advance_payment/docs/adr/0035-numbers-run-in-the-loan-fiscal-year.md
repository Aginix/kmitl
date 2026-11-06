# Both numbers run in the loan's fiscal year, taken from its commitment

Status: accepted (2026-11-06 UAT feedback). Amends ADR-0001's numbering; the ADV and APC sequences are per fiscal year, not per calendar year.

## Context & Decision

ADV (เลขที่คำขอ) and APC (เลขที่สัญญายืมเงิน) used `%(y_be)s` on a plain sequence: the year was today's calendar year and the counter never restarted. Finance numbers its documents by fiscal year (Oct–Sep), so a loan submitted in November 2026 read `ADV/69/…` where the budget side says 2570.

- The loan carries **`account_fiscal_year_id`** (read-only). It is the **Budget Commitment's** fiscal year when the loan has one (`advance_payment_budget_commitment` fills it, with system rights), otherwise the year of the submit date. It is set when the ADV number is issued and never moves afterwards.
- **APC uses the loan's own fiscal year**, not the year of the Effective Date. A loan submitted in September and paid in October keeps the year of the commitment that funds it. Loans submitted before this change get their year at the first number they still need, from the commitment or their submit date.
- Both sequences use `use_date_range` and `%(year_be)s` (four digits, like BC and PR): `ADV/2570/0001`, `APC/2570/0001`, restarting each fiscal year. The date range picks the counter but `%(year_be)s` reads `ir_sequence_date`, so both are pinned to the fiscal year's end date.

## Considered options

- *Fiscal year from the submit date only.* Rejected: a loan on a commitment of another year would be numbered outside the year of the money.
- *APC from the Effective Date.* Rejected: ADV and APC of one loan could land in different years.
- *Block submit without a commitment.* Rejected: back-office loans have no source (ADR-0029, ADR-0031).

## Consequences

- Numbers made before this change keep their two-digit calendar-year form. The formats differ, so the new counters start at 0001 without clashing; the sequences are `noupdate`, so a migration switches them.
- A fiscal year must exist for the date; without one the number falls back to today's year.
