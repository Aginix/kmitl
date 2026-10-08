# Project authors see a computed Funding Summary, not the budget ledger

UAT feedback asked that a project's manager and creator be able to open the
`budget.move` / `budget.move.line` records of their project — across OUs, because
Funding Units in other faculties transfer money in. What they actually need to know is
_which unit has sent how much against the Project Budget Estimate_. We answer that with
a **Funding Summary**: a read-only SQL-view model (`kmitl.project.funding`, in the new
bridge `kmitl_project_budget_transfer`) with one row per transfer line on the project's
dimension (counterpart ส่วนงาน, signed amount, status group), guarded by the same
own-project / officer rules as `kmitl.project` and opened from a smart button; the
project form gains computed _in progress_ and _shortfall_ figures beside the Estimate.
We deliberately **do not** grant project users any ACL or record rule on `budget.move` /
`budget.move.line`; the ledger stat button stays restricted to
`budget.group_budget_viewer`.

## Considered Options

- **Open the ledger to project users (read, own-project lines, bypassing OU)** —
  rejected. Global `ir.rule`s are AND-ed, so bypassing OU means OR-ing an "own project"
  clause into `budget_operating_unit`'s global rules, whose `domain_force` is already
  rewritten by `budget_operating_unit_access_all` (two modules writing one domain). It
  also needs a new group rule on `budget.move.line` plus a compensating `(1=1)` rule for
  Budget Viewers, and widens a budget visibility boundary we had already declined to
  loosen elsewhere. It still would not show the Funding Unit, which lives on the FROM
  line the user must not see.
- **A `compute_sudo` Html table on the project form** — simpler (no model/ACL), but
  rejected in favour of a smart button opening a separate, groupable list.
- **Show only the move header's OU / ส่วนงาน** — rejected: the OU is whoever keyed the
  transfer (often งานแผน) and the header ส่วนงาน is only a line default, so neither
  reliably names the Funding Unit.

## Consequences

- Because the view is our own model, it sidesteps budget's OU rules by construction — no
  budget rule is edited.
- Project users never need budget rights; everything they see about incoming money comes
  through the summary.
- If a later requirement truly needs ledger drill-down for non-budget users, it reopens
  the global OU rule question — revisit this ADR rather than adding ACLs piecemeal.
