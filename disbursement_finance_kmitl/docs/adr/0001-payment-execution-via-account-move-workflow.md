# 0001 — Payment posts via the account.move maker-checker after bank confirmation

- Status: accepted
- Date: 2026-07-21

## Context

After a disbursement request (DR) is billed (`bills_posted`), the money still
has to be audited, authorized, paid to the bank, and finally booked and matched
against the bill ("ล้างหนี้"). Two questions shaped the design:

1. **Who posts the payment's journal entry, and when** — at finance approval /
   bank export, or later?
2. **What is "clearing" (ใบล้างหนี้)** — a new journal entry, a separate manual
   reconcile action, or the payment posting itself?

The KMITL finance stack already posts **vendor bills** through the
`accounting_kmitl_workflow` maker-checker on `account.move` (Approve = post),
and `finance_kmitl` is explicitly built to let payments be **bank-exported
while still `submitted`** (before posting).

## Decision

A DR payment is **posted by the accounting office through the same
`account.move` maker-checker as the vendor bill**, and only **after** finance
has confirmed the real bank result (`success`) and moved the DR to `paid`.
Posting the payment move reconciles it against the bill (the deferred
`to_reconcile_payment_line_ids`), so **posting == clearing (ล้างหนี้) →
`cleared`**. Reconciliation is triggered on the move-posting path
(`account_move._post`) because the workflow Approve does not run
`account.payment.action_post`. A guard blocks posting a DR payment until its DR
is `paid` and its bank result is `success`.

The DR lifecycle becomes a single linear chain:

```
… approved(+budget) → bills_posted
   → payment_audited → payment_authorized → paid → cleared
```

## Alternatives rejected

- **Post at finance approve/export, reverse on failure.** Books the
  disbursement before the bank confirms, so a failed transfer leaves a posted
  payment plus a reversal — phantom entries that government auditors dislike.
- **A separate "create clearing" button that reconciles (decoupling
  auto-reconcile from posting).** Adds a bespoke action and a reconcile-decouple
  migration for no benefit once accounting is the one posting: the maker-checker
  Approve already is the deliberate accounting act, and reconcile-on-post is the
  clearing.

## Consequences

- The general ledger records a payment only when the money actually left the
  bank; a failed bank result produces no accounting entry.
- Clean segregation of duties: finance executes (create/export/confirm),
  accounting records (post/clear).
- `finance_kmitl`'s auto-reconcile-on-post is kept unchanged.
- ~~A DR payment sits in the accounting `account.move` approval queue from the
  moment finance submits it (needed for export); the guard prevents it from
  being posted before finance confirms the bank result.~~ **Revised by ADR-0004:**
  the queue showed the accounting office vouchers it could not post. A payment
  now enters the queue only at the Hand-over (the request reaching `paid`).
