# ADR-0010: The request ends at approval; finance disburses it per Expense over time

## Status

Accepted (2026-10) — **supersedes [ADR-0009](0009-finance-authors-disbursements-from-actuals.md)
and [ADR-0006](0006-category-owned-product-single-product-plan.md)**.

The approval request no longer has an after-approval step for the requester:
no actual-expense record, no hand-off to finance, no one-shot "billed". Finance
raises any number of ใบขอเบิก against an approved request over time, each line
paying one planned **Expense**; the request shows finance its Approved Amount,
Disbursed, In-progress and Remaining at a glance, and closes when Remaining hits
zero or finance closes it, returning the leftover.

Plans are itemized by **Expense Items** each category owns (ticked per category;
an unticked category keeps one Expense, an amount), plus a free-text **อื่น ๆ**
where the category allows it — **not** by `product.product`. Products were the
plan's item before (ADR-0006) and caused more trouble than they carried: a
shared catalogue for what is really per-category wording, and nothing on the
ใบขอเบิก side uses products since its lines became account + amount.

The Approved Amount (the plan total) is a hard cap, checked when a ใบขอเบิก is
submitted; individual Expenses may be overspent against each other
(เกลี่ยระหว่างรายการ) and are only flagged. The cap is the request's own guard:
on a request drawing from a shared reservation (project, procurement plan) the
budget engine would let it overspend its share. For the same reason closing such
a request returns nothing — its leftover stays in the shared reservation —
while a request that reserved its own budget returns its Remaining
(ส่งคืนเงินเหลือจ่าย).

## Considered Options

- **Keep the requester's actual-expense step (ADR-0009).** Rejected: it made
  the requester come back to a document whose job — getting approval — was
  done, and the actuals only re-stated what finance enters on the ใบขอเบิก.
- **Control only the total.** Rejected: a lump "ค่ารับรองและพิธีการ 2,400" says
  nothing about what was approved; finance and reviewers need the breakdown.
- **Hard per-Expense caps.** Rejected: real spending drifts a little between
  items; blocking on each would stall finance for no budget risk.
- **Top up / amend an approved request.** Rejected: spending beyond approval is
  not the request's to cover.
- **Notify finance with a To-Do on approval.** Rejected: a request may sit
  approved for weeks before any money is spent; finance works from the
  paperwork it receives and an "open for disbursement" list.

## Consequences

- Whoever may read a ใบขอเบิก may read the request it references (and so its
  attachments): the OU record rule on the request gains that branch. The
  attachment-check override of ADR-0009 goes away; receipts live on each
  ใบขอเบิก.
- `to_disburse` / `billed` and the hand-off To-Dos disappear; requests in them
  migrate to approved. Old actual-expense rows are kept, unshown, in a
  legacy table (`approval_request_allocation_legacy`); the model is gone.
- `agx_approval_advance_payment` keeps a loan drawn against an approved
  request (and its stat button); the per-row Funding Loan went with the
  actual-expense rows.
