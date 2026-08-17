# Budget is allocated to a plan/project by tagging a transfer (five-dimension sub-pools)

Money on a project- or procurement-type budget code (`budget.account.is_project` / `procurement_plan`) lives in one of two shapes: a **four-dimension Floating Budget** (departments / sources / funds / activities, no Pool Tag) that has not yet been committed to any specific plan or project, and a **five-dimension tagged sub-pool** (those four dimensions **plus** a `kmitl_project` or `procurement_plan` Pool Tag) that belongs to one named plan/project. A `budget.transfer` line may carry the Pool Tag and move Current Budget **in or out of a tagged sub-pool**; a tagged *destination* line creates tagged appropriation — the operation the domain calls **ปรับเข้าแผน** (Budget Allocation to a plan/project). Availability stays the single gate (`budget.controller.get_available`, ADR-0005) and the transfer stays a **pure move** (it reserves/releases nothing, ADR-0009).

> **This revises [ADR-0007](./0007-project-floating-budget-deferred-reserve.md).** ADR-0007's rule — a project's money is untagged floating and the `kmitl_project` dimension appears *only* on the reservation — is now the **pre-allocation** stage. Year-start appropriation still floats (the project does not exist yet), but once a project/plan exists its floating envelope may be tagged into a five-dimension sub-pool by transfer, and — going forward — the plan/project reserves against **that sub-pool** rather than the floating pool. The procurement_plan path (ADR-0005, tagged at appropriation) and the project path thereby converge on one tagged-sub-pool model.

## Why

- ADR-0007 keeps a project's appropriation untagged because *"the concrete project (and its `kmitl_project` dimension) does not exist at appropriation time."* That reason holds only at year-start appropriation. **By transfer time the plan/project does exist**, so its money can — and, to be tracked per project, must — carry the Pool Tag. Allocation to a project is therefore a *transfer*, not an appropriation.
- The engine already nets a tagged reserve out of the four-dimension floating remainder (Pool Tag: the `current`/appropriation side pins absent tags to `False`, the `used` side leaves them unconstrained — ADR-0005). Extending the *same* tag onto the appropriation side makes the requirement — *"1,000,000 floating − 200,000 allocated to a project = 800,000 floating, and the 200,000 reachable only by naming the project dimension"* — fall straight out of the existing mechanism with **no new engine code**.
- Unifying the project money model with `procurement_plan` (both tagged at appropriation *and* reserve) removes the strip-tag special case and the "five-dimension reserve vs four-dimension appropriation → ฿0" class of mismatches.

## Policy

- **Two shapes of pool money**: four-dimension Floating Budget (untagged) and five-dimension tagged sub-pool (one Pool Tag). See glossary: *Floating Budget*, *Pool Tag*, *Budget Allocation to a plan/project*.
- **Transfer lines carry an optional Pool Tag**, mutually exclusive (`kmitl_project` **XOR** `procurement_plan`, never both). A tag is **valid only when it matches the line's `budget_account_id` type** — a `kmitl_project` tag only on an `is_project` code, a `procurement_plan` tag only on a procurement code (server-side validation, the complement of the conditional UI). The four core dimensions remain required on every line; the tag is a *complete* fifth dimension or absent — never partial (ระบุมิติให้ครบถ้วน).
- **A tagged FROM line draws the sub-pool; a tagged TO line funds/creates it** (ปรับเข้าแผน); an untagged line moves the floating/base four-dimension pool. Availability = `current − used` at the line's full `analytic_distribution`; money a plan/project has **reserved** reads ฿0 and is blocked — to move it the reservation is released first (ADR-0009, unchanged).
- **UI**: the destination/source line shows the project analytic field on `is_project` codes and the procurement field on procurement codes.

## Considered options

- **Keep project reservation on the floating pool while allowing tagged transfers (hybrid).** Rejected: a tagged sub-pool and a floating-pool reservation for the same project decouple — the allocation earmarks nothing the reservation honours, inviting an "allocated to P but P reserved from float anyway" double-track.
- **Tag project appropriation at year-start (like procurement_plan).** Rejected: the project does not exist then; ADR-0007's floating stage is the real KMITL process (appropriate an envelope, *then* write projects against it).

## Consequences

- The floating remainder **already** excludes money allocated to a project/plan (Pool Tag netting) — implemented and tested (`test_floating_pool_counts_tagged_owner_reserves`: 100k pool − 60k tagged reserve = 40k). This ADR documents the vocabulary and extends the same tag to the appropriation side via transfer.
- Reversing an allocation is a plain tag-in-hand transfer back to the floating pool (the sub-pool must be unreserved).
- Pre-existing pure-move guarantees hold: no commitment is created/touched by a transfer; reserved money is untouchable until manually released.

## Deferred (separate phase — its own ADR + data migration)

- **The end state is that a plan/project reserves against its own five-dimension tagged sub-pool** (five vs five), dropping the `_availability_distribution` tag-strip for `kmitl_project`. Decided here, **not** built here: until it lands, project reservation still runs against the floating pool.
- **A new lifecycle state on both `procurement_plan` and `kmitl_project`** — `draft → รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ` — that **mints the analytic account early** (so it exists *before* allocation) and then awaits the allocation transfer + reservation. Until this lands, a project's analytic account is minted lazily at reserve time, so allocation-via-transfer is end-to-end usable only for `procurement_plan` (whose analytic account already exists once its plan leaves draft); the project side ships as engine + UI + policy, completed by this phase.
- Back-filling existing project reservations/appropriations from the four-dimension floating pool to five-dimension tagged sub-pools.
