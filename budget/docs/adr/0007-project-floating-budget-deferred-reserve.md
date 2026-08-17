# Project budget floats until its project reserves it

For a *project-type* budget code (`budget.account.is_project`), posting the source `budget.appropriation` does **not** reserve and does **not** auto-create any downstream record. The money sits as **floating budget (เงินลอย)** — appropriated pool carrying the four dimensions but no `kmitl_project` dimension. The reservation (`budget.commitment`, the full `budget_amount`) fires later, when a `kmitl.project` drawing on that pool reserves it. From the reserve point onward the project is spent like a procurement plan: one shared commitment drawn down by its purchase requests and disbursements.

> **Reserve trigger revised** by [kmitl_project ADR-0005](../../../kmitl_project/docs/adr/0005-approval-gated-lifecycle-esaraban.md): reservation moved from the old `draft→new` Confirm to the `to_verify→to_send` "จองงบประมาณ" step of the project's e-Saraban approval. The floating-budget model in this ADR is otherwise unchanged.

> **Model revised** by [ADR-0012](./0012-tagged-sub-pool-allocation-via-transfer.md): the floating (untagged, four-dimension) pool described here is now the **pre-allocation** stage. Once a project exists, its floating envelope may be tagged into a five-dimension **tagged sub-pool** by a `budget.transfer` (ปรับเข้าแผน), and — going forward — the project reserves against that sub-pool rather than the floating pool (the tag-strip in `_availability_distribution` is dropped). Year-start appropriation still floats; what changes is that the `kmitl_project` dimension may now ride the *appropriation* side (via transfer), converging the project model with the tagged procurement_plan model. That reservation migration is deferred to its own phase.

This deliberately diverges from [ADR-0005](./0005-reserve-on-appropriation-posting.md) (which reserves a procurement plan the instant its appropriation posts) and relaxes the one-active-PR rule of [ADR-0006](./0006-plan-driven-pr-created-from-plan.md): a project may hold **many** purchase requests against its single commitment, capped at the commitment amount.

## Why

- Real KMITL process: project budget is appropriated to a fund/department/activity envelope first ("เงินลอย"), then specific projects are written against it and reserve only once confirmed. Unlike a one-line procurement plan, the concrete project (and its `kmitl_project` dimension) does not exist at appropriation time, so there is nothing to reserve against then.
- ADR-0005's "never sit appropriated-but-unreserved" principle is intentionally *not* applied to project codes — floating **is** the intended resting state until a project claims the money.

## Consequences

- `is_project` and `procurement_plan` are mutually exclusive on a budget code (`@api.constrains`), so a project code can never enter the procurement-plan auto-create/reserve path.
- The budget availability check at project `new` runs against the floating pool (respecting `budget.allow_negative`).
- A project's `project_type` is chosen first and filters `budget_account_id` to matching `is_project` codes; the `project_type` selection is kept identical across `kmitl.project` and `budget.account`.
- A project is completed **manually** — unlike a procurement plan (auto-`done` when its commitment is fully consumed), budget exhaustion does not complete a project (completion tracks deliverables, not money).
- A project carries no procurement method; each of its purchase requests picks its own. "Same as procurement" means the *process* (create-from-source, prefill, shared commitment), not an identical field set.
- A project-driven พ.1 is pre-filled **server-side** (in `_link_to_project`) with the project's budget account, fiscal year, **full `analytic_distribution` — the four financial dimensions *plus* the project's own `kmitl_project` dimension** — and the shared commitment, and those fields are locked; spend on the พ.1 is therefore attributed back to the project and can never diverge from the reservation. (Context defaults + onchange still prefill the live form; the server-side write is the guarantee, since the dimension fields are computed from `analytic_distribution` and readonly.)
- A project's purchase requests are capped at its `budget_amount`: creation is gated on the remaining headroom and `action_reserve_budget` rejects a พ.1 whose running total would exceed it; the `budget.commitment` ledger remains the ultimate backstop at disbursement.
