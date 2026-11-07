# Plan details stay editable; the preparer can pull a plan back or delete it while it has no money

A plan created by hand waits at รอจัดสรรงบประมาณ (`to_verify`) — often for weeks — until งานแผน funds it. Until now submitting locked everything and only a plan manager could reset it, so a unit that found a mistake had nowhere to go (prod 2026-11-07: 19 of 30 hand-made plans stuck there, none with money). Plans born from a budget appropriation are funded and reserved at once and were never affected. User feedback of 2026-11-07, see [UX journey review](../ux-journey-review.md).

- **Details stay editable** until the plan is closed or deleted: ชื่อรายการ, จำนวน, หน่วย, Plan Amount (`total_price`), โน้ต and Installments. They never move money — the reservation is sized to Plan Budget, not Plan Amount ([ADR-0003](./0003-plan-reserves-received-not-plan-amount.md)).
- **Fiscal year, dimensions and รหัสงบ** still lock on Submit; changing them needs a reset to draft. Changing the fiscal year of a numbered plan clears its number so the next Submit renumbers it — refused once the plan has a Ledger Footprint.
- **Pull back:** any plan user may reset a `to_verify` plan that holds no Held Money. Resetting a plan that holds money, a `verified` plan or a soft-deleted one stays a plan-manager act (amends [ADR-0002](./0002-no-per-plan-approval-annual-plan-is-published-unit.md)).
- **Delete:** the creator or Preparer may delete their numbered plan while it has no Ledger Footprint; otherwise deleting a numbered plan stays a plan-manager act ([ADR-0005](./0005-plan-close-and-deletion-follow-project.md)).
- **จองงบ** shows only to budget users, and only once the plan is fully funded.
