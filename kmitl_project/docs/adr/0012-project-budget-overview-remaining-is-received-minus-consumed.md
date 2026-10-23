# One Project Budget Overview page; Project Budget Remaining = received − consumed

A project's money was spread over five places: the งบลอย buttons in the header open
a dialog, the "การเคลื่อนไหวงบ" stat button opens a separate list, a "Budget Commitment"
button opens a raw `budget.commitment` list (unreadable for project users), the figures
sit in a group on the strategic-plan tab, and the purchase-request/disbursement buttons
sit beside them. Users moved money in one place and looked for the result in another.
We add a **Project Budget Overview (บัญชีโครงการ)** in a new extension module,
`kmitl_project_budget_overview`: one stat button opens a read-only page of the project that
shows its figures, warnings, the money actions open to the viewer and its Project Budget
Movements, all in one place.

## Decisions

1. **Budget only.** The page covers what passes through the budget engine. Whether a
   spending document has been paid is that document's status, not a movement. It is
   called บัญชีโครงการ because users understand that name best, even though "บัญชี" is
   not the GL here. In code and docs it is the Project Budget Overview: in Odoo,
   "account" reads as accounting.
2. **Three figures:** ได้รับจัดสรร (Project Budget) − เบิกจ่ายแล้ว = **คงเหลือ**, laid
   out as the formula. The reservation is not shown as a figure: on real data it only
   restates the state (0 before approval, the whole Project Budget while in progress,
   since allocations top the reservation up, and 0 once closing returns it), and
   between received and consumed it suggested คงเหลือ came from it. Budget viewers
   open the reservation itself. Warnings appear only when they apply: a transfer still in progress, money
   received but not reserved (a top-up after spending started, ADR-0009), a missing
   reservation, leftover money held after closing, and off-target rows. Obligated (always
   0, budget ADR-0017) and the พ.1 planning headroom are not shown.
3. **Project Budget Remaining is redefined as received − consumed** (it was reserved −
   consumed). The stat button always shows คงเหลือ, and the old formula read 0 until the
   project was approved and 0 again after closing, while money was still sitting at the
   project. Changed in `kmitl_project` itself so the form, the portal and the page share
   one meaning.
4. **Consumed is read from the ledger at the project's coordinate**: posted ตัดงบ lines
   on the project's รหัสงบ + four dimensions + project dimension in its fiscal year, the
   same coordinate `budget_amount` sums. This is not the commitments' `total_consumed`.
   As a result, **the posted rows of the movement list add up to คงเหลือ**, and the page
   shows that sum under the list. It also counts a Budget Manager's direct consumption
   (budget ADR-0019), which no commitment carries.
5. **One list, one tab.** Most projects have a single inflow (the งบลอย allocation), so
   splitting inflows from ตัดงบ only adds a click. The full searchable list stays one link
   away.
6. **Money actions sit on the page.** จัดสรรงบประมาณ (งบลอย) also stays in the project
   header, because users have just learnt it there. โอนคืนงบลอย lives only on the page,
   next to the figures it changes. Both open the same wizards.
7. **The page is a second form view of `kmitl.project`** with a small OWL summary widget,
   not a client action, so lists, buttons and the reload after a wizard closes are
   standard. The figures leave the project form, which keeps the coordinate and the
   estimate.

## Considered options

- **Keep remaining = reserved − consumed and add a second figure.** Rejected: two
  "คงเหลือ" on two screens is the confusion this page is meant to remove.
- **Consumed from the commitments.** Rejected: it misses direct consumption and loses a
  cancelled commitment's history, so the list and the figures would stop reconciling.
- **Tabs for inflows / ตัดงบ / all.** Rejected for the reason in decision 5.
- **A full OWL client action.** Deferred: it means rebuilding the list, search and reload
  by hand, more than a first version needs.

## Consequences

- Money received after spending started now counts in คงเหลือ although it cannot be
  spent until it is reserved. The page flags it.
- Rows in another fiscal year (เงินกันเหลื่อมปี) are still listed but not summarised.
  The carry-over design is open.
