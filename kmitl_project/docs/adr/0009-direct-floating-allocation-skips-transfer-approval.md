# A Direct Floating Allocation posts at once, without the transfer approval

> **Extended by [ADR-0011](./0011-project-deletion-replaces-cancel.md):** the reverse move, Floating Return (โอนคืนงบลอย), sends money back to an Inflow Source; this module was merged into `kmitl_project_budget_transfer`.

In practice, when Floating Budget (เงินลอย) is already sitting at a project's own
coordinate — its รหัสงบ + four dimensions, or the coarser pool covering them — งานแผน
simply moves it onto the project; nobody asks for approval to do so. The system only
offered the full Budget Transfer route (draft → ยืนยัน → หนังสือขออนุมัติโอนงบประมาณ in
e-Saraban → posted, budget ADR-0014), which made a routine bookkeeping step wait on a
signature. We add a **Direct Floating Allocation** in a new extension module,
`kmitl_project_floating_allocation`: a "จัดสรรงบประมาณ (งบลอย)" button on the project
opens a bank-app-style wizard (from the pool → to the project → review → slip) that
creates a real `budget.transfer` and posts it immediately.

## Decisions

- **A real Budget Transfer, posted on confirm.** The wizard builds a `budget.transfer`
  (FROM the pool's coordinate, TO the project's coordinate + `kmitl_project` dim)
  flagged `is_floating_allocation` and linked to the project, runs the ordinary
  `action_submit` (every structural check, the exception rules, availability, the
  pool-nesting guard), then posts it as superuser — skipping only the approve step and
  the e-Saraban letter. It keeps its BTR number, its Funding Unit and its place in the
  Project Budget Movements, and a Budget Manager can still reset it like any other
  transfer.
- **The source is never chosen.** The FROM line is the single pool the availability
  engine resolves as covering the project's coordinate (pools never nest, budget
  ADR-0016), so a direct allocation can only move money that was already meant for this
  coordinate. When no pool covers it, the wizard says so and the ordinary transfer
  remains the route.
- **Any Budget User may do it**, in every state from `to_verify` to `in_progress`, as
  often as needed (top-ups). The amount is typed by hand and capped at the pool's
  available.
- **The reservation follows the existing rule.** Posting fires the `budget.move` hook
  that re-syncs the project's commitment while nothing is obligated/consumed; once
  spending has started, a top-up lands at the project's dimension but is not reserved
  (the wizard warns).

## Considered options

- **Write a raw `budget.move` entry** — rejected: no BTR number, no Funding Unit, shown
  as บันทึกงบประมาณ instead of รับโอนเข้า, and a second way to move money between
  buckets.
- **Create the transfer but stop at `submitted` for a Budget Manager** — rejected: it
  still needs a second person for a move the unit does not approve in practice.
- **Restrict to Budget Managers, or a dedicated group** — rejected by the business:
  every Budget User already keys transfers, and the pool-covering rule is the real
  safeguard.
- **Also extend the reservation when a top-up arrives after spending** — rejected for
  now: it would diverge from how an ordinary transfer into the project behaves.

## Consequences

- **Deliberately bypasses budget ADR-0014** for this one, narrow case; every other
  transfer keeps the e-Saraban approval. The flag on the transfer makes these auditable.
- The move is reversible only through the transfer's own (Budget Manager) reset.
- A top-up after spending has started stays outside the commitment until a manual
  reservation adjustment exists.
