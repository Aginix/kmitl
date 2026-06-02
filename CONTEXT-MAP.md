# Context Map

This is a multi-module Odoo monorepo. Each custom module is its own bounded context, documented by a `CONTEXT.md` (glossary) and an optional `docs/adr/` (architecture decisions) inside the module folder.

This map is seeded lazily — modules are listed here as they get a `CONTEXT.md`, not upfront.

## Contexts

- [KRIS Project](./kris_project/CONTEXT.md) — revenue tracking for projects run under the KRIS unit (operating unit `99`); external academic-service and research work channelled through KRIS.
- [Budget](./budget/CONTEXT.md) — appropriation, reservation and disbursement tracking; appropriated pool (`budget.move`) consumed through a reserve→obligate→consume commitment pipeline (`budget.commitment`).
- [Procurement Plan](./procurement_plan/CONTEXT.md) — annual procurement planning; each plan is created from an appropriation, reserves its budget at that moment, and is realised through one purchase request + installment disbursements.

## Relationships

- **Budget → Procurement Plan**: posting a `budget.appropriation` line creates a `procurement.plan` and reserves its `budget.commitment` for the full amount (ADR-0005).
- **Procurement Plan → Budget**: the plan's single purchase request and its installment disbursement requests draw that one shared commitment down (obligate+consume per งวด) (ADR-0004, ADR-0006).
