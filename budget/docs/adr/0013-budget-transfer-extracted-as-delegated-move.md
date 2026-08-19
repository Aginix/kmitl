# Budget transfer extracted to its own module as a 1:1 delegated budget.move

The budget-transfer feature (`budget.transfer`, its workflow, views, emails, sequence, menus) is split out of core `budget` into a new `budget_transfer` module, so `budget` stays the pure budget-accounting ledger (appropriation / move / commitment). In the new module `budget.transfer` is re-modelled as a **1:1 delegated `budget.move`** — `_inherits = {'budget.move': 'move_id'}`, the `account.payment` ↔ `account.move` pattern — and the separate `budget.transfer.line` model is **dissolved into `budget.move.line`**: a transfer authors the move's own lines directly, so there is one line model, not two.

## Context

`budget.transfer` was always documented as "a balanced `budget.move` of type `entry`" (glossary: *Budget Transfer*; ADR-0009), yet it lived inside core `budget` as a standalone model that *created* a `budget.move` on post and kept a parallel `budget.transfer.line`. Two goals drove this change: (1) keep core `budget` free of the transfer feature, and (2) make the transfer literally *be* a budget move via delegation, the way a payment is a journal entry.

## Decision

- **Module split.** All transfer code/data (`budget.transfer`, reject wizard, views, `budget_transfer_email_templates`, `seq_budget_transfer`, the โอนงบประมาณ menu subtree, transfer access rows, tests) moves to `budget_transfer` (depends on `budget`).
- **Delegation (1:1).** `budget.transfer` `_inherits = {'budget.move': 'move_id'}`. Accounting-header fields (`date`, `company_id`, `currency_id`, `account_fiscal_year_id`, `ref`, `budget_type`, `department_analytic_id`, `source_analytic_id`, `move_type` forced `entry`, `line_ids`) are the move's — no duplicate columns. Transfer-specific fields stay local: `name` (BTR/ sequence, distinct from the move's BM/ number), the six-state approval `state`, `reason`, `user_id` (Requested by), `approver_id`, `approval_date`, `rejection_reason`.
- **The move exists from draft.** Delegation requires `move_id` non-null, so the `budget.move` is created up front (draft, empty) at transfer creation — as a draft payment already owns a draft journal entry. Its lines are written and the move posted only at `action_post` (ADR-0009: "posting writes one balanced entry move"). A reverse `transfer_ids` on `budget.move` (defined in `budget_transfer`, not core) lets the ledger list filter draft transfer-moves out cosmetically; code-level sums are untouched.
- **One line model.** `budget.transfer.line` is dropped; the transfer edits `budget.move.line` through the delegated `line_ids`. All transfer-authoring behaviour is added to `budget.move.line` **from `budget_transfer` via `_inherit`, leaving the core line lean**: a `transfer_direction` helper, a positive `amount` helper mapping to debit (TO) / credit (FROM), per-line `available_budget` / `budget_sufficient` computed **only when `move_type != 'appropriation'`**, and the moved constraints (duplicate line, supplementary XOR, tag-matches-account). Header source/department inheritance is free — `budget.move.line.source_analytic_id` is already `related` to the move header.
- **FROM/TO stays two boxes.** Two filtered One2many (compute + inverse, tagged by `transfer_direction` via context) render over the delegated move lines, so the two-box UX survives without giving the core line a `transfer_id` FK — the line keeps one parent (the move).
- **Install + migration.** `budget_transfer` is `auto_install=True` (its only dependency, `budget`, is already installed in production), so it joins the same upgrade run as the `budget` version bump. A `budget` pre-migration (16.0.2.0.0) reassigns every transfer `ir_model_data` row from module `budget` to `budget_transfer` **before** `budget`'s `_process_end` would delete them (unlinking `ir.model` drops the table), and drops the now-orphan `budget_move.transfer_id` column. Transfer records are ≈0 in production, so no per-record backfill.
- **Core guarded.** `budget_dashboard._recent_movements` gates its `budget.transfer` lookup on `"budget.transfer" in self.env`; the overview OWL card degrades to an empty list. Core `budget` therefore installs and runs without `budget_transfer`.

## Considered options

- **Plain `Many2one move_id`, move created on post (today's behaviour, just relocated).** Rejected: a link, not the `account.payment` delegation the split was asked to mirror; header fields stay duplicated.
- **Keep `budget.transfer.line` as a separate authoring model synced to `budget.move.line`.** Rejected: two line models for one set of lines; `account.payment` deliberately has none. Folding gives a single source of truth.
- **Give `budget.move.line` a `transfer_id` FK for the two-box UX.** Rejected: drags a transfer concern onto the core line and gives the line two parents; filtered One2many over the delegated `line_ids` achieve the same UX cleanly.
- **A separate `budget_transfer/CONTEXT.md`.** Rejected: transfer vocabulary is inseparable from the pool/tag/current-budget language already in `budget/CONTEXT.md`; `budget_transfer` is a structural sub-module of the Budget context, not a new one.

## Consequences

- **Revises the *mechanism*, not the *policy*, of ADR-0009 and ADR-0012.** The transfer is still a pure move that reserves/releases nothing, still requires the four core dimensions, still forbids cross-source, still treats `kmitl_project` / `procurement_plan` as mutually-exclusive Pool Tags. Only the *carrier* changes: the line those ADRs call `budget.transfer.line` is now `budget.move.line`.
- Every draft/submitted/approved transfer now owns a draft `budget.move`; the cosmetic list filter keeps these out of the day-to-day ledger view.
- `budget.tests.test_budget_transfer` moves to `budget_transfer` and is rewritten to author `budget.move.line` (through the transfer) instead of `budget.transfer.line`.
- `budget_operating_unit` (and `_access_all`) must depend on `budget_transfer` and re-point `budget.model_budget_transfer` / `budget.view_budget_transfer_*` refs; the `budget.transfer.line` record rule is dropped (its model is gone — the lines fall under the `budget.move.line` rules).
