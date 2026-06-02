# Obligate and consume are separate ledger primitives

`budget.commitment` records reserve / obligate / consume as separate `budget.commitment.line` entries (`move_type`), and **obligate and consume are independent primitives applied at different times**. This supports the procurement-plan flow: a plan is reserved in full on approval, then obligated per installment (งวดงาน, at contract signing) and consumed later (actual payment/posting).

The PO / disbursement flow deliberately fires obligate + consume together in one step. That is why the dashboard's **"ผูกพัน (c)" column is ~0 for PO-driven commitments** while it carries a real standing balance for procurement plans — both paths call the same two primitives, they just time them differently.

## Consequences

- `(c)` being 0 for a PO-driven commitment is expected, not a bug.
- Splitting the disbursement flow so obligate (contract) and consume (payment) can occur at different times is a Phase 2 change; the primitive split lands first.
