# The loan officer may submit on the borrower's behalf; restricted loan types limit who may start a loan

Status: accepted (2026-10-29 design session; not yet built; pre-production, no migration/version bump). Amends ADR-0005.

## Context & Decision

ADR-0005 let only the borrower (or an admin) submit. Loans without a source are now back-office work for the loan officer (ADR-0029), who also needs to move a request along when the borrower cannot do it in time.

**A loan officer may submit any loan on its borrower's behalf**, whatever its type. The borrower can still submit it personally. The record keeps who submitted, and the chatter notes a submission made on the borrower's behalf.

**The borrower's signature follows the submitter.** The printed contract fills in the borrower's digitised signature only when the borrower submitted personally. Otherwise the block is left blank to sign by hand, like the ใบรับเงิน. Without this, a digitised signature would appear on a debt its owner never confirmed.

**Restricted loan types** (`advance_payment_loan_type_group`, an extension): a loan type may name groups, and only their members may choose it when drafting. The choice is enforced by the picker and again on the server, for RPC and import. A type with no groups is open to everyone. Its data restricts ค่าใช้จ่ายอื่นใด (the type with no source) to the loan officer. This limits who may *start* such a loan, not who may see one. The borrower, endorser, director and approver still open it normally.

## Considered options

- *On-behalf submission for restricted types only.* Rejected in favour of the simpler rule "the loan officer may submit any loan".
- *Hiding restricted types with a record rule.* Rejected: a borrower or endorser opening a loan of that type would hit an AccessError, because the form reads the type (e.g. its source model).

## Consequences

- One officer may draft, submit and verify the same loan. If duties must be separated, add it as a borrowing rule (ADR-0030), not as code.
- The unit finance tier (`group_advance_payment_user`) still drafts on behalf of the borrower but does not submit.
