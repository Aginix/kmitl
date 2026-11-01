# Approval ↔ Disbursement Bridge

Links an **Approval Request** to the **Disbursement Requests** finance raises against it, over time, each line paying one of the request's Expenses — and shows finance the request's position at a glance ([agx_approval ADR-0010](../agx_approval/docs/adr/0010-approval-ends-at-approval-disbursed-per-expense.md)). The request's own terms (Expense, Approved Amount, Disbursed, In-progress, Remaining, Close) are defined in [agx_approval/CONTEXT.md](../agx_approval/CONTEXT.md).

## Language

**Approval Request (AR)**:
The upstream request (`approval.request`): approved, it stays Open for Disbursement until Completed. The requester records nothing on it after approval.
_Avoid_: expense request, claim

**Disbursement Request (DR)**:
The downstream payment document (`disbursement.request`) a finance officer raises against one approved AR — from the AR or by naming it on the DR. Inherits the AR's reservation, budget code and dimensions; finance enters the payee type, recipients, lines, amounts, banks and its payment type, and — separately from the payees — the Expense breakdown: which of the AR's Expenses it covers, explained, adding up to its total. Draws the reservation down when its budget act consumes it.
_Avoid_: bill, payment request

**Disbursement Overview (ภาพรวมการเบิกจ่าย)**:
What the AR shows once approved: Approved Amount − Disbursed − In-progress − given back at Close = Remaining, per AR and per Expense, and its DRs. Read-only for the requester; finance raises DRs and closes the AR from it.
_Avoid_: บัญชีโครงการ (the project's own overview, a separate page)

**Return (ตีกลับ — DR)**:
The verification officer sending a DR in the circuit back because its data is wrong. The DR goes back to `draft` for **its own author** (the finance officer) to fix and resubmit; the AR is untouched.
_Avoid_: correcting the approval request in place (the superseded ADR-0001 flow), reject, cancel
