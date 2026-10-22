================================================
Purchase Invoice Plan Sub-Installment KMITL
================================================

Split a purchase order installment (งวด) into sub-installments (งวดย่อย).

A root installment (`purchase.invoice.plan` with no parent) can be split into
multiple sub-installments. Once split, the root becomes a container:

- ``sum(children.amount) == root.amount`` is invariant.
- Work Acceptance and vendor invoices attach to leaves only.
- Sub-installments work like the original installments (percent of PO total,
  same WA/invoice flow).

The split is one level deep; sub-installments may not be split further.

Usage
=====

* Open a Purchase Order with Invoice Plan enabled.
* In the Invoice Plan tab, click "แบ่งงวดย่อย" on the row you want to split.
* Choose the number of sub-installments and an initial plan date; the parent's
  amount/percent is split evenly across the children.
* Edit each child's amount, percent, plan_date and deliverables inline; the last
  child takes the leftover so the children always sum to the parent.

Credits
=======

* Aginix Technologies
