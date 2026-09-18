# Purchase Invoice Plan — Sub-Installment

How an installment (`purchase.invoice.plan`) on a `purchase.order` may be split into
sub-installments (งวดย่อย) that act like installments themselves but stay inside the
budget of their parent.

## Language

**Installment (งวด)**:
A `purchase.invoice.plan` record attached to a `purchase.order`. The original OCA
flat model.

**Root installment (งวดหลัก)**:
An installment whose `parent_id == False`. Originally the only kind of installment.
When a root installment is split it stops being a leaf and becomes a *container* —
its `amount`/`percent` are derived from its children and it can no longer carry a
WA or an invoice on its own.
_Avoid_: "Parent installment" in user-facing copy — use "งวดหลัก".

**Sub-installment (งวดย่อย)**:
An installment whose `parent_id != False`. A child of a single root installment.
A sub-installment carries its own `amount`, `percent`, `plan_date`, `deliverables`
and `wa_id`; it behaves exactly like a root installment did before splitting.
Nesting is one level only — a sub may not have its own sub.

**Leaf installment**:
Any installment with `child_ids == False`. This is the only place where a Work
Acceptance (`work.acceptance.installment_id`) or a vendor invoice may attach.
Both root installments that have not been split and every sub-installment are
leaves.

## Sum invariant

`sum(root.child_ids.amount) == root.amount` always holds for any root that has
children. The root's `amount` and `percent` are computed from the children — the
user cannot edit the root directly once it has children. A sub-installment's
`percent` is "% of PO total" (same semantics as the root) so existing WA quantity
scaling (`product_qty * installment.percent / 100`) needs no change.
