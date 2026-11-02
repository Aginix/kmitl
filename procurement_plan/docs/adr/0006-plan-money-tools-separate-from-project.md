# Plan money tools are built inside the plan modules, not shared with KMITL Project

Direct Floating Allocation, Floating Return, Held Money, the Plan Budget Overview (บัญชีแผน) and Plan Budget Movements reuse KMITL Project's **semantics** (kmitl_project ADR-0007, 0009, 0011, 0012) but are **implemented separately** inside the procurement_plan family — wizards in `procurement_plan_budget_transfer`, a movements SQL view and an overview page in new plan modules. Extracting a shared mixin would mean refactoring live kmitl_project code and coupling two production families' release cycles for logic that is small and dimension-specific; duplication is the cheaper risk. Decisions D6 and D8 of the 2026-10-24 review.

## Considered Options

- Shared abstract mixin used by both families — rejected: touches production kmitl_project code and ties both upgrades together.

## Consequences

- Overview figures come from the budget ledger at the plan's dimension: received / consumed / remaining = received − consumed, shown against วงเงินตามแผน.
- The public portal's "เบิกจ่ายจริง" switches from the analytic account balance to the same consumed-at-plan-dimension figure; the per-งวด actual (procurement_plan_disbursement) stays as installment tracking.
- A fix to one family's version of these tools must be checked against the other by hand.
