# Units choose activities; the Template composes Fund→Budget Lines and Activity→Funds

ADR-0001 pinned the whole (activity, fund, budget line) grid centrally and shared it verbatim across every ส่วนงาน (the "option b" central template). In practice activities vary far more per unit than funds or budget lines do, so a single pinned activity set forced most units to carry many empty-activity rows and could not express a unit's own activity mix. We therefore split *what is central* from *what the unit decides*:

- The **Template** no longer stores (activity, fund, budget line) rows. It holds **two compositions**:
  - **Fund → Budget Lines** (`budget.expense.template.fund`): which รายการงบ sit under each กองทุน.
  - **Activity → Funds** (`budget.expense.template.activity`): which กองทุน apply under each ด้าน/แผนงาน. Its `fund_ids` reference the Template's own configured funds.
- A **Plan Document** carries the ส่วนงาน's **chosen activities** (`template_activity_ids`, a subset of the Template's activities). The grid is derived live: *chosen activity → its funds → each fund's budget lines*.
- Plan amounts key by the **dimension tuple** (Activity, Fund, Budget Line, month), revising ADR-0002's Template-row-id keying.

## Considered options

- **Central-pinned full grid (ADR-0001, option b).** Rejected on feedback: too rigid — a shared activity list does not fit units with different activity mixes, and it inflates every document with zero rows.
- **Fully unit-authored funds and budget lines too.** Rejected: funds and budget lines (and their groupings) must stay identical across units for consolidation; only the activity axis is genuinely unit-specific.

## Consequences

- **Soft-hide falls out of tuple keying** (ADR-0002): de-selecting an activity — or the Template dropping a fund/budget line — hides those cells but keeps their amounts, which reappear on re-selection. No stored row-id or `active` flag is needed.
- **Consolidation still works**: funds and budget lines are shared, so central can sum a budget line across units; only the activity breakdown differs per unit.
- **Ordering dependency**: a fund must be configured (`budget.expense.template.fund`) before it can be attached to an activity, so the Template form defines funds first, then activities (`fund_ids` is domain-scoped to `parent.id`, so the Template is saved between the two steps).
- The unit selects activities both on the Plan Document form and via an add/remove control inside the OWL grid; both write `template_activity_ids`.
