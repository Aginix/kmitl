# Routing engine is a dynamic chain on a single step entity

The old design copied a static `route.template` into immutable `routing.line` rows plus a separate `document.recipient` tracker activated one-at-a-time — the two tables drifted out of sync and the model could not express the ad-hoc เกษียนสั่งการ (annotate-and-direct) that real Thai correspondence runs on. We decided the Route is **living, mutable data on the Document**, modelled as a **single `sarabun.routing.step` entity** (target + verb + state + outcome) that authorised actors can insert, redirect, delegate, return or CC at runtime; `route.template` is demoted to a convenience that only *seeds* the steps. One entity removes the line↔recipient sync bugs and makes mid-flow insertion trivial.

## Considered Options

- **Static, template-bound flow** (old behaviour) — rejected: cannot model เกษียนสั่งการ; forces the "approval must be last" band-aid.
- **Purely dynamic** (next hop always decided at runtime) — rejected: no templating, weak governance/auditability.
- **Hybrid: dynamic chain as the base model, template as a seed** — chosen.
