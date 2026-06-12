# Setup is validated at confirm; the งวด schedule and completion are discretionary

KRIS validates a project's **setup data** strictly at confirmation (value, allocation,
contract, client, fiscal year), but deliberately does **not** enforce its งวด (Installment)
schedule or money-completeness:

- A project flagged **`no_installment_tracking`** (ไม่มีงวดงานกำกับ) can be confirmed
  without a complete งวด plan and keeps its Installments editable while In Progress —
  test/trial work often has no fixed schedule up front.
- For **every** project, **Done** is allowed even when received Revenue is below Project
  Value and not all งวด are received, and **Cancel** is never blocked by recorded
  Revenue — projects legitimately close under-collected, at KRIS's discretion.

## Why record this

It is a revenue-tracking module, so the obvious default is to block closing until the
money is collected. We don't: the rules that would (`kris_excep_revenue_remaining`,
`kris_excep_installments_not_received`, `kris_excep_cancel_with_receipts`) are kept
`active=False`. Re-enabling them to "fix" the gap would reintroduce exactly the block
this decision removes.

## Note

The `base_exception` popup is effectively a **hard block** for KRIS users — its "ignore"
checkbox is limited to `base_exception.group_exception_rule_manager`, which no KRIS group
implies. So a "warning that still lets you proceed" (e.g. cancel-with-Revenue) is
implemented as an on-form banner, not a non-blocking exception rule.
