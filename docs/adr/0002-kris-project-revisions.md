# KRIS projects are revised via `base_revision`; old revisions are archived, not cancelled

When a project's contract terms change after it is closed or abandoned, an officer creates a new
**revision** of the `kris.project` from the `done` or `cancel` state. We consume OCA's
`base_revision` mixin, so revisions are numbered `KRIS0001 → KRIS0001-01`, the old↔new chain is
maintained automatically, and a "Revisions" smart button surfaces previous versions. Creating a
revision is an officer action (`group_kris_project_officer`), like Confirm/Done/Cancel.

**The old revision is archived (`active = False`) with its state preserved** — a finished project
keeps reading "Done", not "Cancel". This deliberately diverges from `sale_order_revision`, whose
`_prepare_revision_data` forces the old order to `cancel`. We keep the default mixin behavior
because an old revision records a contract that genuinely *was* completed (with real revenue
รายรับ attached); forcing it to `cancel` would misrepresent history and bypass `action_cancel`'s
own logic (e.g. the `warn_cancel_with_receipts` guard). The forward link `current_revision_id`
already marks it as superseded.

A revision keeps the **same `project_name`** — only the Project Number distinguishes versions — so
we feed `project_name` into the copy defaults to suppress the `"(copy)"` suffix that the manual
Duplicate action adds.

## Considered options

- **Force the old revision to `cancel`** (mirror `sale_order_revision` exactly) — rejected: loses
  the truthful end-state of completed projects and side-steps the cancel-time warnings.
- **Add a distinct `superseded` state** — rejected: a new lifecycle value to migrate and teach,
  when `active = False` + `current_revision_id` already expresses "superseded".

## Consequences

- `kris.project` becomes archivable (the mixin adds `active`). Old revisions drop out of default
  list/search views and are reached per-project via the Revisions smart button (`active_test: 0`).
- Revenue is **not** carried to the new revision (`receipt_ids` stays `copy=False`); it belongs to
  the version that earned it. Allocations (การจัดสรร) and installments (งวดงาน) are copied, with the
  installment↔allocation breakdown re-mapped by the existing `copy()` logic.
- The uniqueness constraint is company-scoped: `unique(unrevisioned_name, revision_number,
  company_id)`. The revision baseline (`unrevisioned_name`) is seeded for existing rows on
  **upgrade** by a post-migration script — `post_init_hook` only fires on a fresh install, which
  this already-deployed module never gets — and the version is bumped to `16.0.1.6.0` so the
  migration runs.
