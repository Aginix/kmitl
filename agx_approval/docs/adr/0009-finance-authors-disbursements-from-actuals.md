# ADR-0009: The requester records actuals only; finance authors the disbursements

## Status

Accepted (2026-10) — **supersedes [ADR-0002](0002-payment-type-per-actual-row.md)
and [ADR-0003](0003-per-participant-borrowing-against-an-approved-request.md)**;
amends [ADR-0001](0001-plan-vs-actual-payee-off-the-plan.md) (the recipient
leaves the request entirely and is decided on the ใบขอเบิก).

## Context

In production, the actual-expense step (บันทึกค่าใช้จ่ายจริง) asked the
requester — usually ธุรการ or an ordinary user — to name a recipient
(`res.partner`) and bank on every row and to classify it as จ่ายตรง /
สำรองจ่าย / เงินยืม. Paying a vendor directly required the partner to exist
first. Users found this far harder than the job they actually do: say what was
spent and attach the receipts. Deciding who is paid, how, and on which
ใบขอเบิก is the finance officer's expertise.

## Decision

- **The requester's actual row is product + description + amount** (product
  still limited to the plan's products). No recipient, bank or payment type on
  the request. Request-level evidence files stay, optional.
- **Finance authors the disbursements.** While the request is
  `to_disburse`, a disbursement user may create **any number** of ใบขอเบิก from
  it. Each starts with the request's header (reference, budget reservation,
  budget code, dimensions, description) and **no lines**; finance enters
  recipients, items, amounts, banks and the payment type per ใบขอเบิก.
- **Cap:** the non-cancelled ใบขอเบิก of a request together may not exceed its
  recorded actual total (total only, not per product). Under-billing is normal.
- **Closing is explicit.** Finance presses ตั้งเบิกครบแล้ว (≥ 1 non-cancelled
  ใบขอเบิก) → `billed`; no new ใบขอเบิก afterwards. Unused reservation is **not**
  returned automatically — budget staff use คืนจอง on the ใบจองงบประมาณ.
- **Requester evidence is not copied** onto each ใบขอเบิก; the ใบขอเบิก shows the
  request's evidence read-only and carries its own files.
- **Borrowing is decoupled.** `agx_approval_advance_payment` (never deployed) is
  removed; linking loans to requests is future work.
- The งบหน้าใบสำคัญคู่จ่าย PDF is removed; the ใบขอเบิก's own print is used.

## Considered options

- **Keep payee/payment type on the request, but optional.** Rejected: two
  places to enter the same payee, and finance would still have to re-check it.
- **Prefill ใบขอเบิก lines from the unbilled actual rows.** Rejected: lines
  carry no recipient, so finance rewrites them anyway, and with several ใบขอเบิก
  the prefill would repeat on every one.
- **Auto-close when the ใบขอเบิก total reaches the actual total.** Rejected:
  finance may decline items (missing evidence), so the total may never match.
- **Auto-return the leftover reservation on close.** Rejected by the user:
  returning budget stays a deliberate budget-side action.

## Consequences

- One request → many ใบขอเบิก, each with its own payment type, so ADR-0002's
  "one DR, header `direct`" interim is gone.
- Existing rows lose recipient/bank/payment type; billed requests keep that
  history on their ใบขอเบิก lines.
- No loan ↔ request integration exists until borrowing is redesigned; a loan
  drawn for a trip is not visible on the request.
