# Project owners see computed Project Budget Movements, not the budget ledger

UAT feedback asked that a project's owners be able to follow every budget movement of
their project — across OUs, because Funding Units in other faculties transfer money in
and the project's coordinators must know how it is spent. We answer that with **Project
Budget Movements**: a read-only SQL-view model (`kmitl.project.budget.move.line`, in
`kmitl_project_budget_movement`, an extension of `kmitl_project_budget_transfer` and
`kmitl_project_coordinator`) with one row per `budget.move.line` on the project's
dimension — allocations, transfers in/out (including in-flight ones), budget entries and
ตัดงบ — each with its Movement Kind, Movement Status, Funding Unit (transfers) and
source document (ตัดงบ). Its own record rules mirror `kmitl.project`'s: every Project
Owner (หัวหน้าโครงการ, coordinator, creator) from any OU, plus project officers. It
replaces the ledger stat button for everyone with a single "การเคลื่อนไหวงบ" button;
budget viewers drill into the real `budget.move` through a field only they can see. We
deliberately **do not** grant project users any ACL or record rule on `budget.move` /
`budget.move.line`.

## Considered Options

- **Open the ledger to project users (read, own-project lines, bypassing OU)** —
  rejected. Global `ir.rule`s are AND-ed, so bypassing OU means OR-ing an "own project"
  clause into `budget_operating_unit`'s global rules, whose `domain_force` is already
  rewritten by `budget_operating_unit_access_all` (two modules writing one domain). It
  also needs a new group rule on `budget.move.line` plus a compensating `(1=1)` rule for
  Budget Viewers, and widens a budget visibility boundary we had already declined to
  loosen elsewhere. It still would not show the Funding Unit, which lives on the FROM
  line the user must not see.
- **An inflow-only Funding Summary beside the ledger button** — the first cut; rejected
  after UAT: two buttons for one question, and coordinators also need the spending
  (ตัดงบ) side.
- **Show reservations (จองงบ/ผูกพัน) as rows** — rejected: they are not movements, have
  their own button, and would double-count against the ตัดงบ that draws them down.
- **Inherit visibility by overriding `_search` / `check_access_rule` to "readable
  project"** — rejected: many entry points to cover, and it would also inherit
  purchasing staff's read-all-projects rule, exposing every project's spending to them.

## Consequences

- Because the view is our own model, it sidesteps budget's OU rules by construction — no
  budget rule is edited.
- `kmitl_project_coordinator` becomes a hard dependency, so the single button only
  exists where coordinators do; without it `kmitl_project` keeps its budget-viewer-only
  ledger button.
- Rows in another fiscal year (e.g. เงินกันเหลื่อมปี) are shown as ต่างปีงบประมาณ and,
  like off-target rows, never count toward the Project Budget.
- If a later requirement truly needs ledger drill-down for non-budget users, it reopens
  the global OU rule question — revisit this ADR rather than adding ACLs piecemeal.
