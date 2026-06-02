# Budget Monitoring Dashboard — Design

Read-only dashboard for auditing budget execution per budget account, across the full account hierarchy. **Expense budgets only** (revenue is out of scope; the commitment pipeline is expense-only).

## Scope & access

- **Fiscal year**: required, single selection. Every figure is scoped to it.
- **Access**: automatic via the Operating Unit (OU) global record rules on `budget.move`/`budget.commitment`. The dashboard must **not** `sudo()`. Central-planning staff see all OUs.
- **Financial-dimension filters** (optional, not security): ส่วนงาน / แหล่งเงิน / กองทุน / กิจกรรม. These narrow which moves/commitments are summed; they are *not* row axes.

## Entry & navigation

1. Pick fiscal year (+ optional dimension filters).
2. Pick a top-level (root) `budget.account` — the budget category to inspect.
3. Drill into its subtree.

## Row axis & roll-up

- Rows = the chosen root's `budget.account` subtree (hierarchical).
- **Pure roll-up**: every cell of a parent = sum over itself + all descendants (via `parent_path`). A leaf with no appropriation of its own can show negative remaining; that is read at the level where the appropriation lives.
- Default: hide branches with no activity in the selected fiscal year (keep ancestor rows for context); toggle to show the full chart.

## Columns

| # | Column | Definition | Source / filter |
|---|--------|-----------|-----------------|
| 1 | งบต้นปี | initial allocation | `Σ budget.move.line.balance`, `move_type=appropriation` AND `appropriation_type=initial`, move **posted** |
| ± | ปรับปรุง/โอน | `(a) − (1)` | computed (supplementary appropriations + net transfers) |
| a | **งบปัจจุบัน** | net pool | `Σ balance`, `move_type ∈ (appropriation, entry)`, move **posted** (incl. transfers, excl. consume) |
| 3 | ขอใช้ทั้งหมด | approved cap | `Σ budget.commitment.amount`, commitment **active** (reserved/partial/done) |
| b | จอง | `reserved − obligated` | `budget.commitment.line` posted, active commitment |
| c | ผูกพัน | `obligated − consumed` | `budget.commitment.line` posted, active commitment |
| d | เบิกจ่าย | `consumed` | `budget.commitment.line` posted, active commitment |
| e | รวม | `b + c + d` (= total_reserved) | computed |
| f | **คงเหลือ** | `(a) − (e)` | computed |

States: budget.move **posted** only; commitment **active** only; lines **posted** only. Draft + cancel excluded everywhere.

## Aggregation strategy

Do **not** reuse `budget.controller` per-combination matching (N+1, for single checks only). Instead, set-based:

1. `read_group` `budget.move.line` by `account_id` → (1)/(a) (split initial by `appropriation_type`).
2. `read_group` `budget.commitment` by `account_id` → (3) cap.
3. `read_group` `budget.commitment.line` by `account_id, move_type` → b/c/d. *(Requires the OU rule on `budget.commitment.line` — see Phase 1.)*
4. Map onto the subtree and roll up to ancestors once via `parent_path`.

## Tech

- OWL client action + an `@api.model` method returning the hierarchical grid (extends `budget_tree.py`).
- Click a figure → drill to the underlying `budget.commitment.line` / source documents (audit).
- Start on-the-fly (read_group); add a materialized summary only if it proves slow.

## Out of scope

- Revenue budgets.
- The `budget_appropriation` / `procurement_plan_budget` (appropriation-based) paradigm.

## Related model work

See `docs/adr/0001..0003` and the implementation phases:
- **Phase 1** — model correctness (appropriation_type default, draft-guard, net-floor, state transitions, OU rule on commitment.line).
- **Phase 2** — obligate/consume primitives, disbursement refactor, procurement_plan reserve + per-installment wiring, mixin consolidation.
- **Phase 3** — dashboard backend method + OWL component.
