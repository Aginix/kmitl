# Obligate and consume are separate ledger primitives

> **Amended by [ADR-0016](./0016-commitment-events-posted-to-budget-ledger.md):** the waterfall is now posted to the budget ledger as encumbrance liquidation — an obligate posts `reserve +X / obligate −X`, a consume posts `obligate +X / consume −X` — and the bands are read as Σ balance per bucket of `budget.move.line`. A disbursement request now posts a single consume event that liquidates the reserve directly (no obligate).

`budget.commitment` records reserve / obligate / consume as separate `budget.commitment.line` entries (`move_type`). The ledger **supports** posting obligate and consume independently at different times — but that is a capability, not how the current flows behave.

In practice **both** KMITL flows fire obligate + consume **together** in one step: the PO / disbursement flow, and the procurement-plan flow (which obligates+consumes per งวด at each disbursement request — see the clarification below). That is why the dashboard's **"ผูกพัน (c)" column is ~0** for both — both call the same two primitives at the same moment.

> **Clarification (2026-06, per direct user requirement):** the procurement-plan disbursement does obligate **and** consume together, equal to the submitted amount (ส่งเบิกเท่าไร ผูกพัน+ตัดงบเท่านั้น). It does **not** obligate-at-contract and consume-later. So `(c)` is ~0 for procurement plans too; the not-yet-disbursed remainder of a reserved plan sits in `(b)` reserved.

## Consequences

- `(c)` being ~0 is expected for **both** PO-driven and procurement-plan commitments, not a bug.
- Splitting obligate (at ส่งเบิก/submit) from consume (at approve) was considered for the procurement-plan flow but **rejected per user requirement**: budget is obligated+consumed together at the disbursement request.
