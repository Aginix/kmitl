# A budget reversal (กลับรายการ) is an editable draft budget move, not a counter-transfer

A Budget Transfer or a manually keyed adjustment that was posted in error could only be
undone by **Reset to Draft**, which un-posts the original and leaves no trace of either
the mistake or its correction in the Budget Ledger. The `budget_reversal` module (with the
`budget_transfer_reversal` bridge) adds **กลับรายการ**:
a new budget move that offsets the original, which stays posted.

## Decisions

1. **A plain draft `budget.move`, not a new Budget Transfer.** กลับรายการ creates a draft
   move with the original's pool lines negated (`reversed_move_id` points back). It then
   follows the ordinary budget-move workflow (review → post). It is not a counter-BTR, so
   there is no Buddy Verification and no e-Saraban letter. A reversal corrects a mistake;
   it is not a new decision to move money.
2. **Freely editable.** The draft is only prefilled. The user may change amounts, lines or
   coordinates, so a partial reversal is just a smaller one, and an original may be reversed
   several times. It reads **กลับรายการแล้ว** once the original plus its posted reversals
   net to zero per coordinate (budget code × bucket × dimensions), and
   **กลับรายการบางส่วน** before that. The original's state stays `posted`; there is no new
   state, so the transfer workflow modules (sarabun, verify, exception) are untouched.
3. **Pool control on post.** Posting is refused when the money a reversal takes back from a
   control node exceeds that node's Available (summed per node, as for a direct consumption,
   ADR-0019; skipped under `budget.allow_negative`). Money already reserved there must be
   returned (คืนจอง) or the reservation cancelled first. For the same reason a transfer's
   reservation top-up lines are not copied: returning the reservation undoes them.
4. **Same rights as any manual budget move.** A Budget User may create and post a reversal.
   Resetting a *posted* transfer stays Manager-only, as before.
5. **Reset stays, but not alongside a reversal.** Reset to Draft is kept as an option. It is
   refused on an original while any of its reversals is not cancelled, because that would
   undo the same money twice. A reversal is never itself reversed: reset or cancel it
   instead.
6. **Fiscal year locked.** The reversal keeps the original's fiscal year (the pool it
   offsets). Its date defaults to today, clamped into that year.
7. **Scope.** Covered: posted appropriation/entry budget moves, and Budget Transfers (from
   the BTR form, through `budget_transfer_reversal`). Excluded: commitment-event moves
   (undone by cancelling the event, ADR-0017). The `budget.appropriation` document itself
   gets no กลับรายการ.

## Considered options

- **Reverse with a new BTR, FROM/TO swapped, through the normal approval.** Rejected:
  correcting an error would need a second Buddy check and a second signed letter, and an
  appropriation (no transfer) could not be reversed that way at all.
- **Post the reversal at once, locked to the exact negation.** Rejected: the users wanted to
  review the draft and to reverse in part.
- **Allow the reversal to drive the pool negative, with a warning.** Rejected: it would break
  pool control. Reserved money is released by the reservation's own return.
- **A `reversed` state on the transfer and the move.** Rejected: partial reversal makes it
  ambiguous, and new states collide with the modules that extend the transfer states.
