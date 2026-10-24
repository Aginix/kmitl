# Procurement Plan — Disbursement

Makes a [Procurement Plan](../procurement_plan/CONTEXT.md) track its **actual**
disbursement against its **planned** installments. Tracking only — the plan
authors no disbursement of its own; the money still goes out through the
purchase order and its [Disbursement Request](../disbursement/CONTEXT.md).

## Language

**Installment ↔ Disbursement link (การผูกงวดกับใบขอเบิก)**:
The manual pointer from one งวด (`procurement.plan.payment`) to the single
`disbursement.request` that pays it. Authored on the plan's งวด line — never on
the disbursement request, which stays operational under the purchase order. One
งวด points to one DR; the picker only offers DRs that draw this plan's
reservation down.
_Avoid_: assignment, allocation

**Actual disbursed (เบิกจ่ายจริง)**:
The budget a งวด has really consumed = the linked DR's consumed amount, counted
only once that DR is **approved** (its Rector approval obligated and consumed
the plan's reservation). A linked-but-unapproved DR is *กำลังดำเนินการ* and
counts as zero. Per-งวด tracking only: the plan-level เบิกจ่ายจริง shown on the
plan and the public portal is the budget **consumed at the plan's dimension**
(see [Plan Budget Remaining](../procurement_plan/CONTEXT.md)), which also counts
consumption not linked to any งวด.
_Avoid_: paid, spent, planned amount (that is the งวด's own `amount`)
