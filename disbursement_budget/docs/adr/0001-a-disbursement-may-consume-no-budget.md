# A disbursement under budget control may still consume no budget

`_on_final_approval()` consumes the linked commitment, and
`_check_commitment_obligable()` refuses anything without a
`budget_commitment_id` — "Budget commitment is required before approval."

[ADR-0003 in `disbursement`](../../../disbursement/docs/adr/0003-budget-split-into-disbursement-budget.md)
already carved out the request that escapes this: a **Stand-alone request**,
raised where budget control is not installed at all. That is not the case here.
`disbursement_budget` is `auto_install`, so wherever `budget` is present every
request passes through this module — including one that returns a supplier's own
security deposit. That money has sat on a deposit liability since the guarantee
was receipted; sending it back settles the liability and cuts no appropriation.
There is no commitment to link, and inventing one would reserve budget that was
never appropriated.

**Chosen: `is_non_budget`, a stored computed Boolean, which
`_action_approve_budget()` returns early on with a chatter note.** The base
computes `False`; the source bridge that owns such documents overrides the
compute — the same shape as `is_budget_account_product_expense` /
`_budget_account_line_product()` alongside it.

## Considered options

- **Treat it as a Stand-alone request.** Rejected: a stand-alone request has no
  source document either, and this one is raised *from* a guarantee and must
  stay linked to it. The two are different facts and the glossary keeps them
  apart.
- **Return the money through `account.payment` instead**, the way
  `advance_payment` returns a loan (`payment_type_advance_payment_inbound`).
  Rejected: a loan return is the borrower handing money back and needs no
  authorisation, whereas paying a supplier out of KMITL's bank account is a
  disbursement in every sense the institute cares about — it wants the ใบขอเบิก,
  the two-approver step and the signature block. The budget is the only part
  that does not apply.
- **A private method with no field.** Rejected: the approver would see a request
  that looks like every other one and sign it believing budget was consumed. If
  the exception is worth making it is worth showing, so it is a field on the
  form and in the approver's queue.
- **A zero-amount or dummy commitment.** Rejected: it would put a reservation in
  the budget ledger for money that was never appropriated, and every budget
  report would have to learn to ignore it.

## Consequences

- **The flag lives here, not in core.** `disbursement` knows nothing about
  budget after ADR-0003, so a source bridge that raises it depends on this
  module rather than on `disbursement` alone.
- **The four financial dimensions stay required.** A non-budget request still
  has to say which unit's money moved; the source bridge copies them into the
  create values.
- **`budget_commitment_id` and `budget_account_id` stay empty** and are simply
  not read. `_on_cancel()` finds no commitment and does nothing. Nothing else in
  the approval chain changes: both approvers still sign, and the
  payment-execution phase runs as usual.
- **The approve button still warns that it will consume the budget.** `confirm`
  takes no `attrs`, and rewording it for every request to cover this one would
  be worse; the form shows **No Budget Consumed** instead.
- **A bridge raising this flag is asserting something about the money, not about
  convenience.** "Not appropriated" is the test — not "the requester has no
  commitment handy."
