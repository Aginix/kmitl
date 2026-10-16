# A disbursement may consume no budget

`action_approve` called `_action_approve_budget()` unconditionally, and
`_check_commitment_obligable()` refused anything without a
`budget_commitment_id` — "Budget commitment is required before approval." That
was the right rule while every disbursement spent the institute's money.

Returning a supplier's security deposit does not. The money has been sitting on
a deposit liability since the guarantee was receipted; sending it back settles
that liability and cuts no appropriation. There is no commitment to link, and
inventing one would reserve budget that was never appropriated.

**Chosen: `is_non_budget`, a stored computed Boolean on the request, which
`_action_approve_budget()` returns early on with a chatter note.** The base
computes `False`; a bridge that owns such documents overrides the compute, the
same shape as `is_budget_account_product_expense` /
`_budget_account_line_product()` already in this model.

## Considered options

- **Return the money through `account.payment` instead**, the way
  `advance_payment` returns a loan (`payment_type_advance_payment_inbound`) and
  the way guarantees used to be received. Rejected: a loan return is the
  borrower handing money back and needs no authorisation, whereas paying a
  supplier out of KMITL's bank account is a disbursement in every sense the
  institute cares about — it wants the ใบขอเบิก, the two-approver step and the
  signature block. The budget is the only part that does not apply.
- **A private `_requires_budget_commitment()` method with no field.** Rejected:
  the approver would see a request that looks like every other one and sign it
  believing budget was obligated. If the exception is worth making it is worth
  showing, so it is a field on the form and in the approver's queue.
- **A zero-amount or dummy budget commitment.** Rejected: it would put a
  reservation in the budget ledger for money that was never appropriated, and
  every budget report would have to learn to ignore it.
- **A separate document type for deposit returns.** Rejected for the same reason
  receipt_kmitl ADR-0005 rejects a separate receipt model: the approval
  ceremony, the payee list, the signature block and the payment-execution phase
  are all wanted unchanged.

## Consequences

- **`CONTEXT.md`'s "this approval — and only this one — obligates and consumes
  the budget" now carries an exception**, stated there.
- **The four financial dimensions stay required.** A non-budget request still
  has to say which unit's money moved; the return request copies them from the
  guarantee, so the requester fills nothing in by hand.
- **`budget_commitment_id` and `budget_account_id` stay empty** on these
  requests and are simply not read. Nothing else in the approval chain changes:
  both approvers still sign, and the payment-execution phase runs as usual.
- **A bridge raising this flag is asserting something about the money, not about
  convenience.** "Not appropriated" is the test — not "the requester has no
  commitment handy."
