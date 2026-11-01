# Path B — retiring `budget.commitment.line` (deferred)

Status: **deferred** (decided 2026-10-10, after PR #1473). Revisit only if keeping the
event log next to the ledger causes real problems — the numbers already come from the
ledger alone (path A, [ADR-0017](./adr/0017-commitment-events-posted-to-budget-ledger.md)).

## What path B means

Drop `budget.commitment.line` and let the **`budget.move` be the event**: one event = one
move carrying `commitment_id`, the source document (`res_model` / `res_id`), the event
type and `is_return`. A chatter message / log note may describe an event for people, but
it **cannot replace the model** — the code searches, undoes and computes with it:

- per-source lookup: `_budget_event_lines`, `_has_budget_event`, `_cancel_budget_events`
  (a disbursement request's idempotent approve and its own cancel on a shared slip);
- liquidation rules read the event behind a ledger line: `_ledger_code_held` filters on
  `commitment_line_id.move_type` / `res_model` (has this document obligated? what is its
  open obligation? what did its consumes liquidate?);
- undo per event: cancelling an event cancels its move, or reverses its lines when they
  live inside a transfer's move (`_post_ledger_reversal`, `_unwind_pool_reservations`);
- draft staging: reserve lines (several codes for ถัวจ่าย) exist before anything is posted
  (`_pending_reserve_lines`, `_check_reserve_availability`, `_check_cross_charge`);
- ถัวจ่าย code order (ADR-0018, `_ledger_codes`).

## Design questions to settle first (they size everything else)

1. **Draft reserve lines.** Single code → the header. ถัวจ่าย (several codes/amounts) needs
   a small planned-allocation table — effectively a line model in another form.
2. **Top-ups inside a transfer's move.** One transfer move can carry events of several
   reservations. Either give each top-up/release its own move (reverses ADR-0017 Q5
   "same move") or keep event identity on the ledger line.
3. **Where ADR-0018's code order lives** once reserve lines are gone.

## Footprint (measured 2026-10-10 on the PR #1473 branch)

About 30 files in 11 modules, excluding tests — the same order as PR #1473 itself:

| Area | Files | Size |
|---|---|---|
| Core `budget` | `budget_commitment.py`, `budget_commitment_line.py` (679 lines of posting/liquidation logic to move onto `budget.move`), `budget_move.py`, `budget_move_line.py`, `budget_commitment_mixin.py`, `budget_mixin.py`, `budget_controller.py`, `budget_ledger_reconcile.py` | large |
| `budget` wizards / views / ACL | line wizard, return wizard, `budget_commitment_views.xml`, wizard view, `ir.model.access.csv` | medium |
| `budget_transfer` | `budget_transfer.py`, `budget_commitment.py` | medium — blocked on question 2 |
| Hosts on the event seam | `disbursement`, `kmitl_project`, `procurement_plan_budget`, `purchase_request_budget` | small if `_post_budget_event` / `_has_budget_event` / `_cancel_budget_events` keep their signatures |
| Access | `budget_operating_unit` (model + rule), `budget_operating_unit_access_all`, ACL rows in `agx_approval`, `purchase_request_budget` | small, but upgrade order matters |
| Report | `budget_commitment_pdf` | small |
| Migration | new | large and risky (production is live) |
| Tests | `test_budget_ledger`, `test_budget_commitment` mostly rewritten | large |

## Migration traps

- Convert every event shape: own move, top-up inside a transfer move, cancelled, draft
  reserve lines of draft slips, events whose back-fill failed.
- `agx_approval` and `purchase_request_budget` ship ACL rows on
  `budget.model_budget_commitment_line`: removing the model needs those rows gone in the
  same upgrade, in the right module order, or `-u` fails.
- Rehearse on a copy of the production database; the reconciliation report
  (กระทบยอดบัญชีงบประมาณ) must stay empty.

## What it buys

Less duplication (code, dimensions and amount held on both the event and its ledger
lines) and one model fewer. It does **not** change any figure — those are single-sourced
from the ledger already.
