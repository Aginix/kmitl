# Returning leftover reserved budget is one คืนจอง line that does not close the plan

When actual disbursement comes in under the reservation, the unspent remainder
(`total_reserved − total_consumed`) is returned to the pool through a manual
**ส่งคืนเงินเหลือจ่าย** action. Mechanically this is **คืนจอง**: a single
negative `reserve` `budget.commitment.line` flagged `is_return=True`, equal to
the whole leftover, taking the budget code and dimensions of the first posted
reserve line. It lowers `total_reserved`, which the availability engine reads
(`budget_controller._sum_used` sums reserve lines signed), so Available /
Remaining (f) rises and the money is reusable — **without cancelling the
commitment**. The action lives on `budget.commitment` (`action_return_leftover`)
and is mirrored as a shortcut on the disbursement request
(`action_return_leftover_budget`), both opening the same read-only confirmation
wizard (`budget.commitment.return.wizard`). Returning drives the commitment to
`done` but is posted under `skip_plan_autoclose`, so it deliberately does **not**
auto-close the owning procurement plan.

It is **คืนจอง**, never **คืนเงิน** (a negative `consume` refund of money already
disbursed) — see `budget/CONTEXT.md` (Return Unused Reservation).

## Why

- **One aggregate line, not per budget code.** The disbursement consume flow
  never splits per code — it posts obligate+consume onto the *first* reserve
  line's account/dimensions (`disbursement_request._prepare_budget_obligate_lines`).
  So there is no per-code "consumed" figure to subtract; the only well-defined
  leftover is the commitment total. A single negative line mirroring consume's
  own convention is therefore the only correct option, not merely the simplest.
  Cross-charge commitments inherit exactly the (already-imperfect) per-leaf
  attribution consume gives them — no new distortion, and the roll-up always
  reconciles.
- **Amount is the full remainder, read-only.** The user confirms; they do not
  type an amount. The figure is re-read from `available_to_obligate` at confirm
  time so a concurrent consume cannot let the return exceed the leftover. The
  `consumed ≤ reserved` invariant (B2) is the backstop — over-returning raises a
  ValidationError.
- **No `budget.move`.** Reserve/obligate lines never post a budget move; only
  consume does (the actual disbursement). A return releases an *earmark*, not
  money, so it stays purely budget-control and never touches the GL — posting a
  move would double-count.
- **Plan stays open.** Returning unspent budget is a financial action; closing
  the procurement plan is a procurement-process milestone. Coupling them (as the
  done-when-consumed path does, [ADR-0005](./0005-reserve-on-appropriation-posting.md))
  would let a budget return prematurely close a plan. The two concerns are kept
  separate: the plan stays `in_progress` and is closed manually.
- **Manual, no mid-installment guard (for now).** A procurement plan reserves
  the full `total_price` up front and consumes per งวด ([ADR-0004](./0004-procurement-plan-shared-commitment.md)),
  so a "leftover" is only real once no further งวด will draw on it. The system
  trusts the user to return only when done; it does not block a mid-plan return.

## Consequences

- A new boolean `budget.commitment.line.is_return` marks the return line. The
  line stays `move_type='reserve'` so every existing reserve aggregation,
  constraint (B1/B2) and the availability engine keep working unchanged; the flag
  is purely an explicit, future-proof marker (preferred over keying on
  `amount < 0`).
- The monitoring dashboard gains a final column **ส่งคืนเงินเหลือจ่าย** (g) =
  `−Σ amount` of `is_return` lines (shown positive). It is a memo: b/e/f are left
  on the signed reserve bucket, so posting a return drops จอง (b) / รวม (e) and
  raises คงเหลือ (f) on its own, while (g) records the amount sent back. The
  column drills into exactly the `is_return` lines.
- `skip_plan_autoclose` is a non-destructive context flag read by
  `procurement_plan`'s `_sync_state` override; only the return path sets it, so
  ordinary full-consumption still auto-closes the plan. Re-enabling auto-close on
  return later is a one-line change — nothing is removed.
- The return is reversible by re-reserving (a positive reserve line), subject to
  control-node availability at that time; the immutable ledger keeps the full
  audit trail.
