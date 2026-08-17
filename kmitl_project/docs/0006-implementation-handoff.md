# Hand-off — Implement ADR-0006 (Project Allocation before reserve)

**Status:** designed, docs-first — **not built**. This is the implementation brief for a developer.
**Read first:** [`docs/adr/0006-project-allocation-before-reserve.md`](./adr/0006-project-allocation-before-reserve.md)
(the *why*) and the glossary entries in [`../CONTEXT.md`](../CONTEXT.md) — *Project Allocation*,
*Project Budget*, *Project Number*.
**Branch:** `niamey`. Line references below are against the current tree and were code-verified.

---

## 1. What you are building, in one paragraph

Today a `kmitl.project` reserves its budget **directly** from a *floating* pool at the จองงบ step,
minting its number + analytic + commitment all at once. Change it so that: (a) the analytic account
+ Project Number + ปีงบ-freeze happen earlier, at **ส่งเข้าแผน** (`draft→to_verify`); (b) งานแผน then
transfers budget **into the project's own `kmitl_project` dimension** (this is done in a *different*
branch — see §3); (c) the project's `budget_amount` becomes a **computed live** mirror of that
allocated money; and (d) จองงบ reserves that project-dimensioned money, gated by an availability
check that now **includes the project dimension**, behind a **confirm wizard**.

---

## 2. Scope

**In scope (this branch, `kmitl.project` side only):**
- Move the mint (analytic + `key` + ปีงบ-freeze + budget-target lock) to `action_confirm`.
- `budget_amount` → computed from `budget.move.line` at the project's dimension.
- Add the project dim to the reserve availability payload.
- Two-group readonly (narrative editable / budget-target sticky) replacing blanket `READONLY_STATES`.
- จองงบ confirm wizard + button gating + "ยังไม่ได้รับการจัดสรรงบประมาณ" display.
- Commitment auto-re-sync when `budget_amount` moves (pre-spending).

**Out of scope — DO NOT TOUCH:**
- **`budget.transfer` / `budget.transfer.line`** — the ability to put the `kmitl_project` dimension on
  a transfer line is delivered by branch **`budget-transfer-multi-dimension`**. Do not add a project
  picker there.
- **`budget.controller`** — verified to need **no change** (see §6). The engine already isolates a
  project's availability once the project tag is in the check.
- **`kmitl_project_sarabun`** (e-Saraban) — everything here is at or before `to_send`; the approval
  front is unchanged.

---

## 3. Cross-branch dependency & the load-bearing invariant

The reserve availability check and the computed `budget_amount` both read money **tagged with the
project's `kmitl_project` dimension**. That tag is written by the งานแผน allocation transfer, which is
built in `budget-transfer-multi-dimension`. So:

> **Invariant:** the allocation (transfer TO line) **and** the reserve check must *both* carry the
> project dim. Tagging only one side breaks availability isolation.

End-to-end testing needs **both branches** installed. Confirm early that `budget.move.line` has a
stored `kmitl_project_analytic_id` column (the controller's `_DIM_COLUMNS`,
`budget_controller.py:49-56`, already relies on it) and that a posted allocation transfer populates it.

---

## 4. Current → Target (state machine)

Lifecycle states are unchanged (`draft → to_verify → to_send → sent → in_progress → complete`,
+ `returned/rejected/cancel`). What changes is **what happens on the transitions** and **what is
editable**:

| Transition / state | Today | Target |
|---|---|---|
| `draft→to_verify` (button) | exception check → write state | + **mint** analytic + `key`, freeze ปีงบ, lock budget-target. Rename label/button, add confirm dialog |
| `to_verify` (resting) | "รอตรวจสอบ / จองงบประมาณ" | "**รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ**"; งานแผน allocates (external); จองงบ button gated on `budget_amount>0` |
| `to_verify→to_send` (button) | mint + reserve directly from floating | **confirm wizard** → reserve from the project-dimensioned pool (availability payload +project dim) |
| `budget_amount` | hand-typed Float | **computed** = Current Budget (a) at project dim |
| editable fields | blanket lock outside draft/returned | narrative editable throughout; budget-target sticky once `key` exists |

---

## 5. Implementation tasks (ordered)

### T1 — Move the mint to `action_confirm` (draft→to_verify)
- **Today:** `action_reserve_budget` (`kmitl_project.py:582-593`) → `_reserve_project_commitment`
  (`:876-945`) → `_ensure_analytic_account` (`:843-859`) → `_ensure_project_number` (`:812-825`).
- **Do:** call `self._ensure_analytic_account()` inside the **base** `action_confirm`
  (`kmitl_project.py:573-580`), *after* the state guard, so `key` + analytic are minted at
  `draft→to_verify`. Remove that call from `_reserve_project_commitment` (it becomes reserve-only).
- **Gotcha — exception ordering:** `action_confirm` is overridden in
  `kmitl_project_exception.py:34-37` (`detect_exceptions()` → popup, else `super().action_confirm()`).
  Because the mint sits in the *base* `action_confirm`, it only runs after exceptions pass. Keep it
  that way — never mint a number for a project that fails the strategic-plan check.
- **Idempotency:** `_ensure_project_number` already early-returns if `key` set (`:820-821`); safe on
  re-confirm after reset.

### T2 — Freeze ปีงบ + lock the budget-target group from the first ส่งเข้าแผน
- **Today:** only `account_fiscal_year_id` is guarded, and only via the `write()` guard
  (`kmitl_project.py:827-841`, "cannot change once `key` exists"). Everything else uses
  `EDITABLE_STATES`/`READONLY_STATES` (`:26-41`).
- **Do:** make **`budget_account_id`** (`:441-448`), the four analytic convenience fields
  (`activity/department/fund/source_analytic_id`, `:476-520`) and `account_fiscal_year_id` **sticky =
  readonly once `key` is set** (not merely once out of draft — must survive reset-to-draft).
  - UI: add a computed boolean e.g. `budget_target_locked = bool(key)` and drive these fields'
    readonly via `attrs` on it.
  - Server guard: extend the `write()` guard at `:827-841` to reject changes to the whole
    budget-target group (not just ปีงบ) once `key` exists.
- **Narrative fields:** drop them out of the blanket lock — keep editable through draft→sent/returned.
  (Decide with PO whether to lock narrative at `in_progress`/`complete`; today a few are locked only at
  `complete` — `introduction:57-62`, `methodology_ids:205-212`, `methodology_detail:214-220`.)

### T3 — `budget_amount` → computed live = Current Budget (a) at the project dimension
- **Today:** `fields.Float(..., help="งบประมาณที่ได้รับจัดสรร")` at `:450-457`, editable in
  `EDITABLE_STATES`.
- **Do:** convert to `compute="_compute_budget_amount"`, `store=True`, `readonly=True`. Compute =
  Σ `balance` of **posted** `budget.move.line` of `move_type in (appropriation, entry)` for this
  company + `account_fiscal_year_id` **where `kmitl_project_analytic_id == self.analytic_account_id`**.
  - The project tag is unique to the project, so filtering on it alone isolates the slice (no need to
    also pin the four base dims). Use `read_group` on `budget.move.line` — mirror the domain the
    controller uses (`budget_controller.py:174-180` `_appropriation_domain` + `_APPROPRIATION_MOVE_TYPES`
    at `:43`). This is (a), so it stays stable after reserve/consume (verified: `_sum_current` reads
    only move lines, never the commitment pipeline).
  - Reads 0 before allocation (no analytic yet in draft → 0; no tagged money yet in `to_verify` → 0).
- **Reactivity — the trickiest part.** A stored computed field cannot auto-depend on `budget.move.line`
  (no direct relation from the project). Recommended: add `_inherit = "budget.move"` **inside
  kmitl_project** (same technique as `budget/models/budget_transfer.py`, which already does
  `_inherit="budget.move"`), and on post/unpost/write, collect the affected `kmitl_project_analytic_id`s
  from the move's lines and (a) recompute those projects' `budget_amount`, (b) call the auto-re-sync
  (T6) for those past reserve & pre-spending. This does **not** touch `budget.transfer`.
  - Simpler fallback if reactivity proves heavy: make `budget_amount` **non-stored** computed (always
    fresh on read) and trigger re-sync from a manual "อัปเดตยอดจัดสรร" action + at จองงบ. Note the
    trade-off: non-stored can't be searched/grouped/sorted (the department dashboard may want it).
- **Downstream that already reads `budget_amount`:** `_compute_budget_remaining` (`:699-714`), the
  PR-cap logic (kmitl_project_purchase_request, ADR-0007), and `_reserve_project_commitment` amount —
  all keep working, now against the real allocated figure.

### T4 — Reserve availability payload gains the project dim
- **Today:** `_reserve_project_commitment` builds `analytic_data` with `account_id` + the four base
  dims only (`kmitl_project.py:891-897`) and calls `check_budget_availability` (`:904-909`). The
  commitment it creates already *carries* the project dim in `analytic_distribution` (`:910-940`) —
  so today's check is asymmetric.
- **Do:** add `"kmitl_project_analytic_id": self.analytic_account_id.id` to `analytic_data`. The
  key name must be exactly `kmitl_project_analytic_id` — `get_available_budget` iterates
  `_DIM_COLUMNS.values()` and reads `analytic_data.get(column)` (`budget_controller.py:95-115`).
- This is the gate: pre-allocation the money is at `{4 dims, project=False}`, so a `{4 dims + project}`
  check finds nothing and raises. No extra "is-allocated?" flag needed.

### T5 — จองงบ confirm wizard + button gating + zero-allocation display
- **Wizard:** new `TransientModel` (e.g. `kmitl.project.reserve.confirm`) with readonly display of
  รหัสงบ (`budget_account_id`), the 4 มิติ + มิติโครงการ, and `budget_amount` (= actual allocated).
  `action_reserve_budget` (`:582-593`) opens it (`act_window`, `target:new`) instead of reserving
  inline; the wizard's confirm button calls the real reserve + state write.
- **Gate:** button `invisible` when `budget_amount <= 0`; also re-assert server-side in
  `action_reserve_budget` (defensive — availability raises anyway).
- **Zero display:** while `budget_amount == 0` show **"ยังไม่ได้รับการจัดสรรงบประมาณ"** + a note that
  the figure follows the actual ปรับแผน (a view banner with `attrs` invisible on `budget_amount != 0`,
  or a small computed display field).

### T6 — Commitment auto-re-sync (bounded)
- **Today:** `_resync_project_commitment` (`:971-991`) re-reserves when `budget_amount`/dims changed,
  only pre-spending. It is currently reached from the `returned` edit path.
- **Do:** trigger it from the T3 `budget.move` post-hook so a งานแผน top-up/cut re-aligns the
  commitment **while no obligate/consume exists**. Once spending has started, do **not** auto-adjust —
  leave it to return-unused / manual top-up so a cut can never fall below what is ผูกพัน/เบิกจ่าย
  (the guard in `_release_project_commitment:947-969` already protects the spent case).

### T7 — Labels & copy
- `to_verify` label → **"รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ"** (`state` field `:157-176`).
- Confirm button rename "ยืนยัน" → **"ส่งเข้าแผน / ขอจัดสรรงบประมาณ"** + confirm dialog: *"เมื่อส่งเข้าแผน
  ระบบจะออกเลขที่รันโครงการ + ล็อกปีงบและรหัสงบ (รายละเอียดโครงการยังแก้ได้ตลอด)"*.

---

## 6. Why `budget.controller` needs no change (don't "fix" it)

Verified against `budget/models/budget_controller.py`. `_control_scope` (`:267-282`) adds a **positive
leaf for every dimension present in the check's `dims`** — including `kmitl_project` once T4 adds it.
So **both** `_sum_current` (`:284-289`, appropriation) and `_sum_used` (`:291-308`, reserves) scope to
*this* project's tag → availability is isolated to the project's own allocated slice; two projects
sharing the four base dims cannot cross-deplete. `_sum_used`'s `include_pool_tags=False` (`:304`) only
relaxes the *absent*-tag pin for **untagged/floating** checks (legacy ADR-0007 path); it never drops
the positive project leaf. Leave all of this alone.

---

## 7. Migration risk (flag to PO before building)

`budget_amount` becoming computed means **existing projects reserved under the old floating model**
(their appropriation is *untagged*) would compute to **0** at their project dim. Options to decide:
1. Keep the stored manual value as a fallback when no tagged appropriation exists, or
2. Back-fill a tagged appropriation/allocation for existing projects, or
3. Accept it (if the ADR-0005 lifecycle is still UAT-only with no real project data — confirm).

Also confirm the `kmitl_project_analytic_id` column exists on `budget.move.line` in the target DB.

---

## 8. Test checklist (extend `tests/test_project_budget_reserve.py`)

- [ ] `draft→to_verify` mints `key` + analytic + freezes ปีงบ; a fresh draft has none of these and ปีงบ
      is editable (duplicate-and-retarget works).
- [ ] `budget_amount == 0` in draft and in `to_verify` before any allocation; จองงบ blocked.
- [ ] After a posted allocation transfer at `{4 dims + project}`, `budget_amount` = allocated;
      จองงบ succeeds and reserves that amount.
- [ ] Reserve **fails** if attempted with no tagged allocation (availability raises).
- [ ] **Isolation:** two projects sharing the four base dims, each allocated separately, do not reduce
      each other's availability.
- [ ] After ส่งเข้าแผน then reset-to-draft: **ปีงบ** stays readonly (sticky once `key`); `budget_account_id`/4 dims
      are editable again in `draft`/`to_verify`/`returned` and pin only once reserved; narrative still editable.
- [ ] Top-up transfer while pre-spending → `budget_amount` rises and the commitment auto-re-syncs;
      after obligate/consume it does not auto-shrink.
- [ ] Wizard shows correct รหัสงบ/มิติ/จำนวนเงิน; confirm reserves, cancel does nothing.
- [ ] e-Saraban path (`to_send→sent→in_progress` + returned/rejected) unchanged.

---

## 9. Open decisions for dev/PO
- `budget_amount` reactivity: **stored + `budget.move` post-hook** (recommended) vs **non-stored computed**.
- Narrative editability at `in_progress`/`complete` (lock or keep).
- Migration option (§7).
- No version bump while pre-deployment (per project convention); bump if this ships to the live modules.
