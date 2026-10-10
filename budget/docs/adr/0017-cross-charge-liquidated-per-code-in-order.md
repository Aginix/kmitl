# A ถัวจ่าย reservation is liquidated per budget code, primary code first

A ถัวจ่าย (cross-charge) reservation holds several budget codes with the same
dimensions: the primary code on the header, then the other reserved codes. Until now
every event after the reserve — ผูกพัน, ตัดงบ, ส่งคืนเงินเหลือจ่าย — posted on the first
reserve line's code only (ADR-0009). The reservation's totals were right, but the
per-code figures were not. A code could show a negative จองเงิน (b), and a return freed
money at the primary code while the other codes stayed reserved for ever.

Now the budget ledger (ADR-0016) **splits each event over the reservation's codes in
order**:

| Event                             | Order                                              | Each code takes up to                                                                     |
| --------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| ผูกพัน (obligate)                 | primary first, then the order the codes were added | its unobligated reserve (b)                                                               |
| ตัดงบ (consume)                   | primary first                                      | the source document's obligation on that code, or its b when the source obligated nothing |
| ส่งคืนเงินเหลือจ่าย (return)      | last code first                                    | its b                                                                                     |
| de-obligation (negative obligate) | last code first                                    | what the source has obligated on that code                                                |
| refund (negative consume)         | primary first                                      | what the source has consumed on that code                                                 |

Each share posts its own pair of ledger lines on its code (for example
`consume −t / reserve +t` on code B), inside the event's single `budget.move`. Whatever
no code can take stays on the primary code, so the reservation-wide limits still block
an overdraw. A reservation with one code posts exactly as before.

A refund (คืนเงิน, a negative consume) is credited to the primary code, which is the
code the user chose on the header. It moves on to the next codes only when it exceeds
what the primary code consumed, so no code's consumed figure goes negative.

A transfer release (ADR-0016, Q5) out of a reservation's coordinate may release only
what **that code** still holds unobligated.

## Considered options

- **Pro rata over the reserved amounts** — rejected: every disbursement would touch
  every code, and rounding would leave residues per code.
- **The consuming document names the code** — rejected for now: no consumer form has a
  per-code picker (the ถัวงบ picker on consumer documents is still parked), and the
  order rule needs no user input.

## Consequences

- **Amends** [ADR-0009](./0009-return-leftover-reserved-budget.md): the return is still
  one event, but its ledger lines are split per code.
- The back-fill splits a historical ถัวจ่าย consume the same way. It re-cuts the old
  single consume line into the primary code's share and adds lines for the other codes,
  so the old move keeps its number.
- The core event target (`_get_budget_event_target`, the first reserve line) is
  unchanged. The event records the nominal code, and the ledger lines carry the split.
