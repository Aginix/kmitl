# ADR-0007: Requesting Unit is a separate field, not the budget ส่วนงาน dimension

## Status

Accepted

## Context

`department_analytic_id` (ส่วนงาน) already exists on `approval.request`, but
only as a computed/inverse window onto `analytic_distribution` — the budget
dimension the reservation is charged against. It sits inside the
budget-officer group, is readonly on the requester form, and only gets a
value once someone picks a budget code from the chart (or the request draws
an existing reservation, or a project draw-down overwrites it). A requester
never sees it, and the verifier at รอตรวจสอบ/จองงบ has no way to tell which
unit is actually asking, before a code has even been picked.

Reusing `department_analytic_id` for "the unit the requester belongs to"
would require it to hold a value the requester enters up front — but the
budget officer's picker, a `budget_selection_mode` switch, and a project
draw-down all write over it later (`_onchange_budget_selection_mode` clears
it, `apply_reservation_selection`/`_action_draw_from_reservation` set it from
the picker/commitment). Any value the requester typed would be silently lost
the moment budget selection runs.

## Decision

`requesting_department_id`, a plain stored `Many2one` to
`account.analytic.account` (domain `root_plan_id.code = 'departments'`), is
added as its own field — outside `analytic_distribution` entirely. Neither
`_onchange_category_id` nor `_onchange_budget_selection_mode` touch it, so
nothing the budget side does can wipe it. It is required and editable while
`is_plan_editable`, defaults to the requesting user's most recently used
unit, and is backfilled on existing requests from their reserved
ส่วนงาน dimension (the closest available approximation for old data).

The two fields are allowed to diverge and no constraint compares them — a
project-funded request, for instance, may be charged to the project's own
ส่วนงาน while the requester still belongs to a different unit.

## Consequences

- Two ส่วนงาน-like fields now exist on the same document:
  `requesting_department_id` (who is asking, stated up front) and
  `department_analytic_id` (what is charged, chosen at reservation). Anyone
  reading the model needs to know which is which — see the glossary entry.
- The requester form, list, search, PDF header and Sarabun subject all read
  `requesting_department_id` (falling back to the budget dimension only
  where no requesting unit yet exists on old data), so a request is
  identifiable by unit before any budget selection happens.
- No reconciliation or validation between the two fields; they are allowed
  to disagree indefinitely.

## Alternatives considered

- **Make `department_analytic_id` requester-editable up front, and skip
  writing it later when already set**: rejected — the budget dimension must
  stay the officer's/picker's/draw-down's authoritative output; special-casing
  "don't overwrite if already set" would make the reservation flow's write-back
  conditional and harder to reason about, for a field whose entire job is to
  mirror what was actually reserved.
- **Derive requesting unit from `owner_id`'s HR department instead of a
  separate field**: rejected — the requester's HR department is already shown
  via the PDF's สังกัด narrative (`owner_id.department_id`) and is not always
  the unit the expense should be filed under (e.g. central staff filing on
  behalf of a faculty).
