# Project budget is allocated into its own dimension before it reserves

A `kmitl.project` no longer reserves **directly** against a *floating* project pool at
confirmation. It now passes a **Project Allocation (ปรับเข้าแผน)** step: after the author
submits the project to งานแผน, planning staff **transfer budget into the project's own
`kmitl_project` dimension** (a `budget.transfer` whose destination carries the project's
analytic dim + the four base dimensions). Only once that money sits at the project's
dimension can the project reserve its `budget.commitment`. The reservation therefore draws
a pool that has been **specifically funded at the project's dimension** — not the floating
pool directly. This supersedes the reserve model of [budget ADR-0007](../../../budget/docs/adr/0007-project-floating-budget-deferred-reserve.md)
(floating budget survives, but as the *source* of the allocation transfer) and reshapes the
front of the [approval-gated lifecycle](./0005-approval-gated-lifecycle-esaraban.md).

## The reshaped flow

```
draft ─(ส่งเข้าแผน)→ to_verify ─(งานแผนจัดสรร: budget.transfer, external)⟳ to_verify ─(จองงบ + wizard)→ to_send ─(สร้างหนังสือ)→ sent ─(ลงนาม)→ in_progress
```

- **draft** — fully editable *including* ปีงบ; **disposable** (no analytic, no running number
  yet). This is what makes end-of-year drafting of *next* year's projects and duplicating the
  ~60% recurring annual projects work: a copy can be freely retargeted to the next ปีงบ.
- **draft → to_verify ("ส่งเข้าแผน / ยืนยัน")** — runs `detect_exceptions()`, then **mints the
  Project Number (`key`), creates the analytic account (`code = key`), freezes ปีงบ, and locks
  the budget-target group**. A confirm dialog states what locks. The `to_verify` label becomes
  **"รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ"**.
- **to_verify (waiting)** — planning staff perform the **Project Allocation** (an external
  `budget.transfer` into the project's dimension). The project's computed `budget_amount` rises
  above 0; the จองงบ button is gated on `budget_amount > 0`.
- **to_verify → to_send ("จองงบประมาณ")** — a confirm **wizard** shows the รหัสงบ, the four
  มิติ + the มิติโครงการ, and the จำนวนเงิน (= the *actual* allocated amount); on confirm the
  project reserves one `budget.commitment` for `budget_amount`, with an availability check that
  **includes the `kmitl_project` dimension**.
- **to_send onward** — the e-Saraban approval front is **unchanged** (ADR-0005). The หนังสือ
  still issues after the reservation, so it shows the money already set aside.

## Decisions

1. **Mint at ส่งเข้าแผน — not at create, not at จองงบ.** The analytic account, `key`, ปีงบ-freeze
   and budget-target lock all fire together at `draft→to_verify`. Earlier (at create) would
   freeze ปีงบ and litter the dimension list with analytics for abandoned/duplicated drafts;
   later (at จองงบ, as ADR-0005 had it) would leave the planner allocating against an unnumbered,
   same-named analytic (recurring projects share a name) and against an unfrozen ปีงบ.
2. **`budget_amount` becomes computed-live** = Current Budget (a) at the project's dimension —
   the sum of every `budget.move.line` whose `analytic_distribution` carries the project's
   `kmitl_project` dim. The author no longer types it; the project's **ask** lives in the
   Project Budget Plan (`budget_expense_total`, ADR-0002). Being an (a)-side figure it is stable
   after reserve/obligate/consume. It reflects reality and re-values automatically as งานแผน
   transfers in/out.
3. **Reserve availability includes the project dimension.** The check's `analytic_data` payload
   gains `kmitl_project_analytic_id` — today it carries only the account + four base dims, while
   the commitment it creates already *records* the project dim, so this simply closes an existing
   asymmetry. It is the *natural gate*: before allocation the money sits at `{4 dims, project=False}`,
   so a `{4 dims + project}` check finds nothing and reserve fails — "จองได้ก็ต่อเมื่อจัดสรรแล้ว"
   falls out for free. **The availability engine (`budget.controller`) needs no change** (verified):
   once the project tag is in the check's `dims`, `_control_scope` puts a *positive* leaf on it, so
   **both** the appropriation side (`_sum_current`) and the usage side (`_sum_used`) scope to that
   project's own tag — each project's availability is isolated to its own allocated slice and sibling
   projects sharing the four base dims cannot cross-deplete. (`_sum_used`'s `include_pool_tags=False`
   only relaxes the *absent*-tag pin for untagged/floating checks; it never drops the positive project
   leaf.) **Load-bearing invariant:** the appropriation (the transfer's TO) and the reserve check must
   *both* carry the project dim — tagging only one side breaks isolation.
4. **Only ปีงบ is sticky; the rest of the budget-target stays editable until จองงบ.** `ปีงบ`
   (`account_fiscal_year_id`) freezes for good once `key` is minted, because the running number
   encodes it. `budget_account_id` + the four dims stay editable through the **pre-reserve
   authoring band** (`draft` / `to_verify` / `returned`) and pin only once the budget is reserved
   (`to_verify → to_send`), so the author can still correct a wrong รหัสงบ/มิติ after ส่งเข้าแผน —
   the realistic window is "waiting in `to_verify` for งานแผน to โอนงบ." **Trade-off:** if the
   author retargets *after* งานแผน has already allocated against the old coordinate, the allocation
   strands there and จองงบ fails the availability check (`budget_amount` itself is safe — it keys on
   the sticky project dim only). This is a soft, recoverable `UserError`, not data loss; งานแผน
   re-allocates or the author reverts the code. Every **narrative** field stays editable throughout.
5. **Creator-driven, wizard-gated reserve.** The project responsible (its creator) clicks จองงบ;
   the confirm wizard is the last check before money is committed. Finance/planning-unit roles
   ("เจ้าหน้าที่งานการเงิน/งานแผน : หน่วยงาน") that may *also* reserve are deferred.
6. **kmitl_project never touches the allocation.** The Project Allocation transfer is external
   (its project-dimension support is built in branch `budget-transfer-multi-dimension`); its money
   persists at the project dim across reject/cancel/reset. On cancel/reject the project posts a
   chatter note asking งานแผน to reverse the transfer if the money should be reclaimed. A
   reset-to-draft keeps the allocation, so re-submitting reuses it with no re-transfer.

## Why

- **Real KMITL process.** Budget is not a floating envelope a project simply draws — งานแผน
  actively **จัดสรร/ปรับเข้าแผน** by moving money onto the specific project, and only then is the
  project "funded". Modelling the allocation as a first-class transfer into the project's own
  dimension makes the ledger say exactly that.
- **One number, always true.** A computed `budget_amount` can never drift from what was actually
  allocated (the recurring-project copy-paste of last year's figure stops being a source of
  error), and budget cuts/increases flow through with no rework.
- **Draft must stay cheap.** The duplicate-and-retarget workflow for recurring projects only works
  if a draft carries no number, no analytic and no frozen ปีงบ. Deferring all of that to the
  explicit ส่งเข้าแผน hand-off keeps drafts disposable.
- **Reserve-before-หนังสือ is retained** (ADR-0005): securing the money before the ขออนุมัติ
  หนังสือ lets the approval show it is already set aside.

## Consequences

- **Supersedes budget ADR-0007's reserve model.** The project no longer reserves the floating pool
  directly; floating budget becomes the *source* of a Project Allocation, and the reserve draws the
  project-dim-earmarked slice. ADR-0007's downstream model stands: one shared `budget.commitment`
  for the full `budget_amount`, drawn down by the project's purchase requests and disbursements,
  capped at `budget_amount`.
- **Revises the mint trigger of ADR-0001 / ADR-0005.** `key` + analytic move to `draft→to_verify`
  (they were at `to_verify→to_send` per ADR-0005, and `draft→new` originally). ADR-0001's ปีงบ
  stamping/freeze rides along; the sticky-for-good rule covers **ปีงบ alone** (the rest of the
  budget-target pins later, at จองงบ).
- **Revises the field-lock model of ADR-0005.** The blanket `READONLY_STATES` is replaced by a
  two-group rule: **narrative** (editable throughout) vs **budget-target** (`budget_account_id` +
  the four dims editable in the pre-reserve band `draft`/`to_verify`/`returned`, pinned once
  reserved; ปีงบ sticky from the first ส่งเข้าแผน). `budget_amount` leaves the editable set
  entirely — it is computed.
- **The commitment auto-re-syncs** to `budget_amount` while no obligate/consume exists (งานแผน tops
  up or cuts before spending); once spending has started, adjustments go through the
  return-unused / manual top-up path so a cut can never fall below what is already ผูกพัน/เบิกจ่าย.
- **e-Saraban (`kmitl_project_sarabun`) is untouched.** All changes live at or before `to_verify`.
- **UI**: while `budget_amount = 0` the form shows **"ยังไม่ได้รับการจัดสรรงบประมาณ"** with a note
  that the figure follows the actual ปรับแผน, instead of a bare 0.
- **The availability engine is unchanged** — verified against `budget/models/budget_controller.py`.
  Its set-based `_control_scope` already isolates a project's `current` and `used` to the project's
  own tag once that tag is in the check; the only edit is on the project side, adding
  `kmitl_project_analytic_id` to the `_reserve_project_commitment` availability payload. The engine's
  `_POOL_TAG_COLUMNS` / `include_pool_tags` machinery — built for ADR-0007's *untagged* floating pool —
  keeps working for any legacy floating check and does not interfere with a tagged project check.
- **budget.transfer needs a `kmitl_project` dimension on its lines** to author the allocation —
  **out of scope here**, delivered by branch `budget-transfer-multi-dimension`. This branch touches
  only the project side. (Its TO line — the tagged appropriation — is the other half of the
  load-bearing invariant above.)
- **Status: designed, not built** (branch `niamey`, docs-first). When built, expect changes to
  `action_confirm` / `action_reserve_budget`, the `budget_amount` field (→ computed), the
  `_reserve_project_commitment` availability payload (+ project dim), `READONLY_STATES`, a new จองงบ
  confirm wizard, and the `docs/kmitl-project-status-workflow.drawio` diagram.
