# Context Map

This is a multi-module Odoo monorepo. Each custom module is its own bounded context, documented by a `CONTEXT.md` (glossary) and an optional `docs/adr/` (architecture decisions) inside the module folder.

This map is seeded lazily — modules are listed here as they get a `CONTEXT.md`, not upfront.

## Contexts

- [KRIS Project](./kris_project/CONTEXT.md) — revenue tracking for projects run under the KRIS unit (operating unit `99`); external academic-service and research work channelled through KRIS.
- [Budget](./budget/CONTEXT.md) — appropriation, reservation and disbursement tracking; appropriated pool (`budget.move`) consumed through a reserve→obligate→consume commitment pipeline (`budget.commitment`).
