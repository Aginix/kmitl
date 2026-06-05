# Context Map

This is a multi-module Odoo monorepo. Each custom module is its own bounded context, documented by a `CONTEXT.md` (glossary) and an optional `docs/adr/` (architecture decisions) inside the module folder.

This map is seeded lazily — modules are listed here as they get a `CONTEXT.md`, not upfront.

## Contexts

- [KRIS Project](./kris_project/CONTEXT.md) — revenue tracking for projects run under the KRIS unit (operating unit `99`); external academic-service and research work channelled through KRIS.
- [Budget](./budget/CONTEXT.md) — appropriation, reservation and disbursement tracking; appropriated pool (`budget.move`) consumed through a reserve→obligate→consume commitment pipeline (`budget.commitment`).
- [Procurement Plan](./procurement_plan/CONTEXT.md) — annual procurement planning; each plan is created from an appropriation, reserves its budget at that moment, and is realised through one purchase request + installment disbursements.
- [KMITL Project](./kmitl_project/CONTEXT.md) — institutional project/activity planning (โครงการ/กิจกรรม); a project draws from a *floating* project-type budget pool, reserves its full budget when confirmed, then spends like a procurement plan.
- [Accounting Reports](./accounting_kmitl_reports/CONTEXT.md) — financial-statement reports (Trial Balance, P&L, Balance Sheet, Cash Flow) over the GL (`account.move.line`), filterable by the KMITL accounting dimensions.
- [KMITL User Provisioning](./kmitl_user_provisioning/CONTEXT.md) — gates un-provisioned internal users (no `hr.employee`, no functional group, not admin) to a full-screen "contact admin" landing page on login, without stripping groups.

## Relationships

- **Budget → Procurement Plan**: posting a `budget.appropriation` line creates a `procurement.plan` and reserves its `budget.commitment` for the full amount (ADR-0005).
- **Procurement Plan → Budget**: the plan's single purchase request and its installment disbursement requests draw that one shared commitment down (obligate+consume per งวด) (ADR-0004, ADR-0006).
- **Budget → KMITL Project**: posting an appropriation on an `is_project` budget code leaves the pool *floating* — it does **not** auto-create a project or reserve (contrast Procurement Plan). A `kmitl.project` reserves its `budget.commitment` for the full `budget_amount` when confirmed (`draft→new`) (ADR-0007).
- **KMITL Project → Budget**: the project's purchase requests (พ.1) and disbursements draw that one shared commitment down (obligate+consume); a project may hold many PRs, capped at the commitment (ADR-0007).
