# พจ.1 (PA) carries its own copied, divergeable data — own columns + own line model, not pure delegation

D1/D8/D9 require the พจ.1 to be **copied** from the พ.1 and then edited independently (vendor, VAT,
line prices, amount), without mutating the พ.1. Today `purchase.request.approval` uses
`_inherits = {"purchase.request": "request_id"}` — pure delegation — so every field (partner, taxes,
`line_ids`, `estimated_cost`) resolves to the shared PR; editing them on the PA writes straight back to
the พ.1. That cannot satisfy "copied but divergeable".

**Decision.** Give the PA its **own stored columns** for the divergeable header fields (vendor/partner,
VAT/tax, amount) and its **own line model** `purchase.request.approval.line` (product + quantity locked,
price editable). Both are populated by a **snapshot copy from the PR at PA creation** — identical at
first, then free to diverge. `_inherits` is **kept only** to carry the shared, non-divergeable
descriptive metadata (requester, department, financial dimensions, title, fiscal year) as read-only
single-source context on the PA.

## Considered options

- **Pure delegation (status quo)** — rejected: PA data physically cannot diverge from the PR.
- **Drop `_inherits` entirely and copy every field** — rejected: large churn and loses the shared-metadata
  single source of truth for descriptive fields that must *not* diverge.

## Consequences

- **`_inherits` field shadowing:** a PA-own field cannot share a name with a delegated one — either declare
  the PA-own field so it takes precedence over the delegated related, or use distinct names. Verify Odoo 16
  `_inherits` shadowing behaviour at implementation.
- **Blast radius:** any PA code / report / compute that currently reads delegated `line_ids` /
  `estimated_cost` / `partner_id` must repoint to the PA-own line model and columns. The พจ.1 PDF renders
  **PA-own** data; the God-Mode amount edit and vendor/VAT edits live on PA columns; the budget check
  (total ≤ reserved) reads the **PA-own** total.
- The 1 พ.1 → 1 พจ.1 policy (D3) is re-enforced by re-enabling the commented-out `request_id_uniq`
  constraint. Reinforces [ADR-0002](0002-pa-separate-model.md).
