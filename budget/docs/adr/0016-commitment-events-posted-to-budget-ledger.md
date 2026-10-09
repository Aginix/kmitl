# Commitment events are posted to the budget ledger (`budget.move.line` is the one source of budget figures)

Every budget figure used to come from two models: Current (a) from
`budget.move.line`, and Used (e), the bands b/c/d and the totals on a ใบจอง from
`budget.commitment.line`. Every report, `kmitl.project` and the availability
engine had to add the two up, and money transferred into a project **after** it
had started spending stayed stranded, because `_auto_resync_commitment` could
only cancel-and-re-reserve while nothing had been obligated or consumed.

We now run the commitment as a **sub-ledger posted to a general ledger**, the way
government budget accounting runs encumbrances: **every event on a
`budget.commitment` posts a `budget.move`**, and every figure is read from
`budget.move.line`. The `budget.commitment` stays a document; its lines become
the **event log** (commands), never a source of numbers. Implemented in core
`budget` itself — the old figures summed from `budget.commitment.line` are
replaced, not overridden — with one seam every writer goes through; the
transfer top-up/release lives in `budget_transfer`.

## Decisions

1. **Sub-ledger → GL (Q1).** Each commitment event (`budget.commitment.line`)
   posts its own `budget.move` (`commitment_id`, `commitment_line_id`,
   `res_model`/`res_id` of the source document). The commitment is still the
   document users act on.
2. **Encumbrance liquidation (Q2).** A ledger line belongs to one *bucket*
   (`budget.move.line.move_type`):

   | Event | Ledger lines |
   |---|---|
   | จองงบ (reserve X) | `reserve −X` |
   | ผูกพัน (obligate X) | `reserve +X`, `obligate −X` |
   | ตัดงบ (consume X) | `obligate +X`, `consume −X` — when nothing is obligated, the reserve is released instead: `reserve +X`, `consume −X` |
   | ส่งคืนเงินเหลือจ่าย (return X) | `reserve +X` |

   A disbursement request therefore posts **one consume event** (no
   obligate): with nothing obligated it liquidates the reserve directly, so
   band c stays 0 by construction instead of by an obligate that the consume
   cancels in the same instant.

   Remaining (f) at any coordinate = **Σ balance of posted lines**; the bands are
   Σ balance per bucket: b = −Σreserve, c = −Σobligate, d = −Σconsume, and
   e = b + c + d. On the commitment: `available_to_obligate` = b,
   `available_to_consume` = c, `total_consumed` = d, `total_obligated` = c + d,
   `total_reserved` = b + c + d.
3. **Pool tags are pinned symmetrically (Q3).** `kmitl_project` /
   `procurement_plan` are matched on both the Current and the Used side; the
   `include_pool_tags=False` usage-side escape and the reserve-time tag strip are
   retired. Production holds no legacy project slip reserved straight from the
   floating pool, so nothing depends on the asymmetry.
4. **Line bucket ≠ move event (Q4).** `budget.move.line.move_type` becomes a
   stored compute (`readonly=False`) defaulting to the move's type; a liquidation
   line overrides it. `budget.move.move_type` gains `reserve` / `obligate`. The
   move header says *what happened*, the line says *which bucket moved*.
5. **Transfers top a reservation up automatically (Q5).** When a transfer's TO
   line lands on the exact coordinate (budget code + every dimension + fiscal
   year) of an active reservation that owns the line's pool tag, a `reserve −X`
   line is added to **the same move**, and the reservation's cap rises by X. A
   FROM line out of that coordinate releases `reserve +X` (never more than
   `available_to_obligate`; beyond that the transfer is blocked). This replaces
   `kmitl.project._auto_resync_commitment`, which could not act once spending
   had started.
6. **Undoing a transfer undoes its top-up; cancelling a reservation never touches
   a transfer (Q6).** Resetting a posted transfer removes its top-up/release lines
   (blocked when the reservation no longer has the topped-up amount free).
   Cancelling a reservation cancels its own moves but posts a **new** release move
   for top-ups living inside a transfer's move. A transfer's balance check counts
   only its FROM/TO (`entry`) lines. The sub-ledger link is per line
   (`budget.commitment.line.budget_move_line_id`), since one transfer move may
   carry events of several reservations.
7. **Commitment figures are read from the GL (Q7).** `total_*`,
   `available_*`, `_check_commitment_limits` and `_sync_state` read
   `budget.move.line` through the stored `commitment_id`.
8. **Commitment lines are commands, not numbers (Q8, path A).** Nothing sums
   `budget.commitment.line`; looking up "has this document already obligated?"
   also reads the GL. Posted lines stay immutable. This keeps the door open to
   retire the model later (path B).
9. **One write seam in core (Q9).** `budget.commitment._post_budget_event`,
   `_cancel_budget_events` and `_has_budget_event`; every writer (mixins,
   controller service, wizards, disbursement, project, plan) calls them instead
   of `budget.commitment.line.create`.
10. **No new module (Q10).** Core `budget` carries the posting, the GL reads,
    the back-fill and the reconciliation report; `budget_transfer` carries the
    top-up/release; the existing `kmitl_project_budget_transfer` /
    `procurement_plan_budget_transfer` bridges name the reservation that owns
    each pool tag. `kmitl.project._auto_resync_commitment` is removed. (First
    built as a separate `budget_ledger` module overriding core; folded in before
    release so no figure is computed two ways.)
11. **Same BM/ sequence; back-fill reports, never aborts (Q11).** Event moves use
    the existing `budget.move` sequence. The back-fill runs as the `budget`
    upgrade's post-migration: it posts the history in date order per reservation
    (re-using each existing consume move and adding its liquidation lines),
    checks the invariants, logs every mismatch and keeps upgrading. A
    reconciliation menu lists what does not match.

Assumptions taken without a separate question: the move's fiscal year is always
the commitment's; a `done` reservation with money left still counts as reserved
until its leftover is returned; event moves are posted with `sudo()` and stamped
with the commitment's operating unit; project users still do not see the ledger
(kmitl_project ADR-0007).

## Considered options

- **Keep both models and sum them everywhere** — rejected: it is the status quo;
  every new report re-learns the two-source formula and the stranded-top-up bug
  cannot be fixed without a GL posting anyway.
- **Path B now — drop `budget.commitment.line`** — deferred: a large migration
  across every consumer. Path A (lines = commands) gets the single source of
  numbers today and makes B a mechanical follow-up.
- **Waterfall in the GL (post reserve, obligate and consume as gross lines and
  subtract in reports)** — rejected: Σ balance would no longer be Remaining, and
  every report would keep re-deriving the bands.
- **Resync by cancel-and-re-reserve** — rejected: it cannot run once anything is
  obligated or consumed, which is exactly when a top-up is needed.

## Consequences

- `budget.controller` reads one Σ balance at the control node instead of
  `current − used`; the Used side no longer queries `budget.commitment.line`.
- The dashboard, overview, `budget_report` and every drill-down read
  `budget.move.line`; a drill list now totals its bucket exactly.
- The old consume-only `budget.move` per consume line is replaced by the event
  move; back-filled consume moves keep their number and gain liquidation lines.
- **Amends** [ADR-0001](./0001-obligate-consume-separate-primitives.md) (the
  waterfall becomes liquidation in the GL),
  [ADR-0005](./0005-unified-availability-engine-control-node.md) (`used` is no
  longer a separate sum, and the pool tags are no longer asymmetric),
  [ADR-0007](./0007-project-floating-budget-deferred-reserve.md) and
  [kmitl_project ADR-0006](../../../kmitl_project/docs/adr/0006-project-allocation-before-reserve.md)
  (resync → automatic top-up).
