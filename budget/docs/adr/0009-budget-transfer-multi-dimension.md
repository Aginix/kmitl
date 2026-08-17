# Budget transfer is a pure multi-dimension budget move

A **budget transfer** (`budget.transfer` → balanced `budget.move` of type `entry`) shifts Current Budget between `(budget.account × analytic_distribution)` buckets. It is **driven by the line's full `analytic_distribution`** — all active analytic dimensions, including `kmitl_project` / `procurement_plan` — and its availability is evaluated through the unified control-node engine (`budget.controller.get_available`, ADR-0005), not the legacy four-hardcoded-field path.

**`budget.transfer` is a pure budget move.** Its only job is to move budget at the `(budget.account × analytic_distribution)` level: a FROM line credits its bucket, a balanced TO line debits its bucket, and posting writes one balanced entry move. It does **not** reserve, release, reduce, or create any `budget.commitment`, and it does not create any `procurement.plan` / `kmitl.project`. **Reserving or releasing budget is a separate, manual step** performed on the commitment/plan/project records themselves — decoupled from the transfer.

**Dimension policy:**

- **The four core dimensions are required on every line** — `departments` (ส่วนงาน), `sources` (แหล่งเงิน), `activities` (กิจกรรม), `funds` (กองทุน). Enforced in the line trees (`required="1"`) and re-checked at submit, so availability is always matched on every axis against the appropriation (an under-dimensioned line would read ฿0).
- **The two supplementary dimensions are optional and mutually exclusive** — a line may carry `kmitl_project` (โครงการ/กิจกรรม) **or** `procurement_plan` (แผนจัดซื้อจัดจ้าง), or neither, but never both (`_check_supplementary_dims_exclusive`). When present, the supplementary dimension is a **Pool Tag** and the line moves money in/out of a five-dimension **tagged sub-pool** — a tagged destination line *allocates* into it (ปรับเข้าแผน). A tag is valid only when it matches the line's `budget_account_id` type (`kmitl_project` ⇔ `is_project`, `procurement_plan` ⇔ procurement code). See [ADR-0012](./0012-tagged-sub-pool-allocation-via-transfer.md).
- `sources` **must be equal** on FROM and TO — cross-source mixing (เงินแผ่นดิน ≠ เงินรายได้) is a hard validation error. `budget.account`, `departments`, `activities`, `funds`, and the supplementary dimension may differ freely per line.
- Availability is evaluated from the line's **full `analytic_distribution`** (every present dimension) via `get_available`. A transfer must be balanced (ΣFROM = ΣTO) and every amount positive.

**Workflow:** `draft → submitted → approved → posted`, with `rejected` / `cancelled` and reset-to-draft. Guards: a *posted* transfer cannot be reset to draft (its move is in effect); approval enforces segregation of duties (approver ≠ requestor); a **Budget Manager or an admin** may submit / approve / reject / post — an admin may act on behalf of others and is exempt from the SoD check. Availability is re-checked at post; the engine is non-floored, so an over-committed bucket reads negative and blocks unless `budget.allow_negative`.

## Considered options

- **Transfer orchestrates reservations (release at post) + creates destination plans/projects + locks the FROM amount during the pending window.** Designed and initially built, then **removed on review**: `budget.transfer` should stay a pure budget move at the `analytic_distribution` / `budget.account` level, and reservation should be done manually and separately. Keeping the transfer free of commitment logic keeps its responsibility single and avoids coupling it to the plan/project lifecycles.
- **Legacy 4-dimension availability wrapper** — replaced by the control-node `get_available(budget_account, analytic_distribution, …)` so the transfer sees every active dimension.

## Consequences

- `budget.transfer.line` carries the full `analytic_distribution` (via convenience dimension fields that round-trip with the JSON) and reads `available_budget` from `get_available` at the line's own distribution. No commitment is created or touched anywhere in the transfer.
- To move budget that a plan/project has reserved, the user **first releases that reservation manually** (on the plan/project/commitment), which returns the money to its pool, and **then** runs a plain transfer. The transfer itself neither checks nor mutates reservations.
- To fund a new plan/project, the user creates and reserves it manually; the transfer only moves budget between `(account × dimensions)` buckets.
- Pre-existing `budget.transfer` correctness fixes are kept: no reset of a *posted* transfer, approver ≠ requestor, and controller errors surface instead of being swallowed.

## Removed (was in earlier drafts of this branch)

These were designed here and later cut so the transfer stays a pure move (reservation is manual):

- Release orchestration at post (`_release_bound_reservations` / `budget.commitment._release_for_transfer` and the ledger-state guards) and the bridge overrides (`_transfer_release_source` / `_transfer_partial_allowed`).
- Destination-bucket creation at post (`create_destination`, `_create_destination_record` / `_confirm_destination_record`, the `procurement_plan_budget` / `kmitl_project` transfer bridges).
- Pending-window submit lock (`_create_submit_locks` / `_cancel_submit_locks`, `budget.commitment.transfer_id`).
- The per-document partial-transfer config toggles (`budget.transfer_partial_plan` / `_project`).

## Deferred (not in this phase)

- `activities` / `funds` cross-transfer gating (policy config) — **TODO**.
