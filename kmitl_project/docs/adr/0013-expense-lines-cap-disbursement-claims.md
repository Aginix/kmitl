# Expense lines of the Project Budget Plan cap ใบขอเบิก claims

> **Supersedes** the "not reconciled against the Project Budget" consequence of [ADR-0002](./0002-budget-plan-amount-is-manual.md) and the matching wording in CONTEXT.md.

A ใบขอเบิก raised under a project was capped only by the project total (`budget_amount`). The Project Budget Plan (`project.budget.line`) said what the money was for, but nothing held a claim to it, so a project could spend its whole budget on one planned expense.

## Decisions

1. **The claim unit is an expense line.** A `disbursement.request.line` names one expense line of its DR's project (`kmitl_project_budget_line_id`). Several DR lines may name the same expense line.
2. **Claimed Amount** on a line = Σ `price_total` of the DR lines that name it, on DRs not in `draft` or `cancel`. The project-level cap (`_project_disbursement_claimed_total`) now also leaves out other drafts. `_get_project_claims` (the Floating Return guard) is unchanged. The claim is computed through a hook, `project.budget.line._get_claimed_amounts`, so a พ.1 path can add to it later.
3. **Expense Control (`expense_control`) is per project.** When on, a DR line without an expense line, or one that takes its line over its amount, is refused at submit by blocking exception rules. When off, only the project-level cap applies. A line of another project, or an income line, is refused either way.
4. **On for new projects, off for existing ones** (pre-migration of `kmitl_project` 16.0.3.1.0). Project Owners and planning staff edit the switch while the form is editable or in a Revision Draft; the planning Manager may edit it at any time.
5. **Σ expense lines ≤ Project Budget** is checked, blocking, for every project at ยืนยันงบประมาณ, and again at every Project Revision (ADR-0014).
6. **Only ใบขอเบิก count.** The ค่าวัสดุ path (พ.1 → พจ.1 → ตรวจรับ) is parked. A DR may name any expense line, whatever its ประเภทงบ.

## Considered options

- **Pick the expense line on the DR header.** Rejected: one DR often pays several kinds of expense (อาหาร, ที่พัก, ค่าตอบแทน).
- **Count draft DRs as claims.** Rejected: a forgotten draft would block every other requester. The submit check locks the expense line row, so two DRs submitted at once cannot both pass on the same remaining amount.
- **Make the control global.** Rejected: shell projects done outside the system (name + Project Number, direct DR) have no plan to claim against.

## Consequences

- The plan is now binding once approved, so changing it needs a Project Revision (ADR-0014).
- DR users who are not project users get read access to expense lines (ACL + record rule in `kmitl_project_disbursement`), so the line picker works for them.
