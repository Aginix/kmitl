# Budget Lines are owned by the Template; a new fiscal year is a duplicate

ADR-0001/0004 kept the Budget Line (รายการงบ) as a **single global catalog** shared across all templates and years, referenced from `template.fund.budget_line_ids`. In practice the unit thinks in terms of "this year's template" and wants next year to be a copy it tweaks. A shared catalog couples years together and offers no clean "duplicate the whole thing and change the year".

So the **Template now owns everything**:
- `budget.expense.line` gains a required `template_id` (ondelete cascade); the Template exposes `line_ids` alongside `fund_ids` and `activity_ids`.
- **Duplicating a Template deep-copies** its lines, funds and activities, and **remaps the internal M2m links** — `fund.budget_line_ids` → the new lines, `activity.fund_ids` → the new funds — because Odoo's `copy()` does not remap Many2many pointers to copied siblings. The copy starts in `draft` with the year cleared and no plans.
- `fiscal_year_id` becomes **optional** (enforced only at publish) so a duplicated draft can exist before its new year is chosen.

## Considered options

- **Global catalog + per-year templates referencing it (ADR-0001).** Rejected on feedback: no one-click "duplicate per year", and shared lines couple years — editing a line for next year would silently change last year's report.
- **A duplicate wizard that asks for the target year.** Rejected for v1: heavier UI than "duplicate then edit the year field", which the standard Odoo Duplicate + a button already give.

## Consequences

- `expr` and category now live **per-template**, duplicated each year — intentional divergence-per-year, the whole point of the change.
- The standalone Budget Line menu/action is removed; budget lines are edited inside the Template form (page "รายการงบ").
- The unique `(fiscal_year_id, source_analytic_id, company_id)` constraint tolerates a duplicated draft because a NULL fiscal year is distinct in a Postgres unique index (multiple NULLs don't collide).
- Authoring order within the Template: define budget lines → save → map funds → save → map activities (the M2m pickers are scoped to the saved template's records).
