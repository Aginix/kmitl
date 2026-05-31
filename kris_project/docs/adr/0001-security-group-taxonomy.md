# KRIS Project security group taxonomy

KRIS owns all project data; Project Managers (academics, `manager_id`) only view their own projects, while KRIS staff create and manage everything. The bottom tier is therefore read-only, not self-service. We use **`viewer` / `officer` / `manager`** instead of the usual KMITL `user` / `manager` pair:

- `group_kris_project_viewer` — Project Manager, read-only, scoped `manager_id.user_id == user`
- `group_kris_project_officer` — KRIS Officer, full CRUD on all projects
- `group_kris_project_manager` — KRIS Admin, CRUD + configuration
- `group_kris_project_ou_viewer` — OU Executive, read-only within own Operating Unit *(future, deferred)*

## Considered Options

- **Repurpose `group_kris_project_user` as KRIS Officer (CRUD all)** — rejected: it would silently escalate existing `user`-group members from own-records to all-records on upgrade. Keeping `officer`/`manager` with their current meaning and replacing the `user` slot with a read-only `viewer` is a privilege *reduction* (always safe).
- **`leader` for the read-only role** — rejected in favour of `viewer`, matching the sibling `budget` module's `group_budget_viewer`. "Project Manager" stays the data-attribute term (`manager_id`), mirroring Odoo's own `project.project.user_id` = "Project Manager" coexisting with `group_project_manager`.

## Consequences

- `officer` is grounded in KMITL convention (`advance_payment`, `disbursement`, `stock_request` use `_officer` for the "staff processes all records" tier), not just Odoo's `salesman` precedent.
- Module is pre-production, so the old `group_kris_project_user` is dropped outright — no migration script.
- Single-company deployment: the existing multi-company gap on child models (installment/receipt/allocation lack company scoping) is left unaddressed by design.
