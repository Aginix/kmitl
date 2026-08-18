# A central locked Template drives a three-layer master-data model

> **Refined by [ADR-0004](./0004-unit-chosen-activities-template-fund-activity-composition.md) and [ADR-0005](./0005-budget-lines-owned-by-template-duplicate-per-year.md):** Activities are no longer pinned centrally — each ส่วนงาน **chooses its own**; the Template holds two compositions (Fund→Budget Lines, Activity→Funds) and now **owns the Budget Lines too** (ADR-0005), so a new fiscal year is a *duplicate* of the whole Template. Still holding: the per-(source × fiscal year) Template, FY-versioning, and the Required Department config.

The expense plan must let every ส่วนงาน enter monthly แผน figures against a grid whose **funds, budget lines and their groupings are identical across units**, so central planning (กองแผน) can consolidate and compare. We model the master data in three layers rather than as one flat set of plan lines:

1. **Budget Line (`รายการงบ`) catalog** — a label + Category (one of the five expense roots) + an `expr` that curates the budget.account codes whose consume feeds the column. The `expr` lives here, defined once per column.
2. **Template** — central and locked, one per (แหล่งเงิน × ปีงบประมาณ): the set of Activities in scope and, under each, the (Fund, Budget Line) pairs that must be planned. Shared by all ส่วนงาน.
3. **Plan Document** — a ส่วนงาน's instance of a Template; holds only the 12-month Plan figures. Activity and Fund come from the Template row; Actual is derived, so the document stores no dimensions of its own beyond ส่วนงาน + (แหล่งเงิน, ปีงบ).

## Considered options

- **Unit-authored free lines** (each ส่วนงาน adds its own `(activity, fund, budget line)` rows). Rejected: rows would differ per unit, so central could not consolidate or compare — the opposite of the "ล็อกจากส่วนกลาง" requirement.
- **The whole `(activity, fund, budget line)` tuple as the master record, with `expr` on each.** Rejected: the catalog explodes to activity × fund × line and the same `expr` is duplicated across every activity/fund sharing a budget line. Keeping `expr` on the Budget Line and referencing it from Template rows removes the duplication.

## Consequences

- A ส่วนงาน that does not run an in-scope Activity simply leaves those cells **blank / zero** — every unit sees the same rows because the grid *is* the shared Template. Accepted deliberately as the price of a consolidatable grid.
- Actuals are **auto-scoped**: a Plan Document line inherits Activity + Fund from its Template row, and the Actual query adds the document's ส่วนงาน + แหล่งเงิน + ปีงบ + month — so the `expr` only needs to name budget codes, never dimensions.
- Templates are **fiscal-year-versioned** (part of the key), so a new year's structural change never rewrites last year's plan.
- A separate **Required Department** config records which ส่วนงาน owe a Plan Document (who-must-plan tracking + document generation); it does not affect the grid.
- The Template being locked centrally means a structural edit after units have started filling amounts is a governance action, not an everyday edit — the state model on the Template must reflect that.
