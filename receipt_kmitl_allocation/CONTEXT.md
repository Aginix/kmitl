# Receipt KMITL Allocation

Posting-time fan-out of a single receipt line's revenue into several GL
accounts and organizational units, driven by per-product configuration.
Bridges `receipt_kmitl` (the receipt itself is unchanged) with
`account_analytic_kmitl` (the 6D dimension framework each bucket can
override).

## Language

**Revenue Allocation** (การปันส่วนรายได้):
Splitting one receipt line's revenue, at posting time only, into several
Cr legs on different GL accounts and dimensions. The receipt UI and the
printed receipt never see the split — a cashier still enters and a customer
still sees one line, e.g. ค่าธรรมเนียมการศึกษา. The fan-out is entirely
config-driven (`product.template.receipt_allocation_line_ids`) and entirely
invisible until `kmitl.receipt._action_post()` builds the journal entry.
_Avoid_: Revenue split, distribution (that name is taken by
`analytic_distribution`)

**Allocation Bucket** (`receipt.allocation.line`):
One row of a product's allocation config: a target revenue account plus an
optional override for each of the six financial dimensions, and either a
fixed amount or a percentage. Configured globally per `product.template` —
not per unit — so the same tuition product behaves identically for every
faculty; a bucket that leaves Department blank naturally follows whichever
department issued the receipt (see Inherit dimension below).
_Avoid_: Split line, revenue rule

**Remainder**:
`line.amount − Σ(fixed buckets)`. Percentage buckets are a percentage of the
*remainder*, not of the line's full amount — so a bucket sequence mixing a
fixed สถาบัน fee with percentage-based คณะ/สำนักทะเบียน splits divides only
what's left after the fixed fee. Percentage buckets on a product must sum to
exactly 100% of the remainder; the last percentage bucket (by `sequence`)
absorbs whatever rounding residual is left so credits still sum exactly to
the remainder.

**Inherit dimension / Fixed dimension**:
The two ways a bucket can handle each of the six dimensions. Leaving a
bucket's dimension field blank means **inherit**: the leg carries the
receipt line's own value for that dimension (e.g. a คณะ/หลักสูตร bucket
naturally follows the issuing department). Filling it in means **fixed**:
the leg is pinned to that unit regardless of who issued the receipt (e.g. a
สถาบัน or สำนักทะเบียน bucket always posts to the same department no matter
which faculty's cashier issued the receipt).
_Avoid_: Override (used informally, but "fixed dimension" is the paired term
with "inherit dimension")

**Lumped Cash Debit**:
The receipt line's Dr Cash leg stays a single line at `line.amount` carrying
the *header's* dimensions, even when its Cr revenue side fans out into
several allocation legs with different (bucket-pinned) dimensions. A
deliberate divergence from `receipt_kmitl` ADR-0004's 1:1 Cash/revenue
pairing — see `docs/adr/0001-lumped-cash-debit-for-allocated-lines.md`.
_Avoid_: Split cash, cash allocation (Cash is never split by this module —
only revenue is)

## Known limitations

- A bucket's dimension override applies at posting time only — nothing on
  the receipt form shows that a line will fan out, or into what. Finance
  audits the split from the posted `account.move`, not the receipt.
- Deleting the last remaining bucket of a product (rather than editing the
  set together, as the product form's o2m widget normally does) does not
  re-trigger the "at least one percent bucket summing to 100" check, since
  Odoo constraints run on create/write of `receipt.allocation.line`, not on
  its unlink. Left as encountered — no report reads a mid-edit config.
