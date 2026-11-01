# An apportioned request consumes the pool directly and posts its own budget transfer

Income KRIS receives for academic-service or testing work is disbursed by one
ใบขอเบิก: part of it is paid to the project head, the rest is **apportioned**
(ปันส่วน) to units inside the institute — no money moves for that part, only
budget, and the destinations differ from one case to the next.

## Decision

A request ticked **มีการปันส่วน** (`is_apportioned`, `disbursement_apportionment`)
carries **apportionment lines** (budget code + ส่วนงาน / กองทุน / กิจกรรม + amount;
แหล่งเงิน is the request's). Its ตัดงบประมาณ act does both, in one transaction:

1. **Consumes the payee lines only** (`amount_total`, e.g. 900,000) directly from
   the pool at the request's own budget code and dimensions — a direct
   consumption (budget ADR-0019), reusing `disbursement_direct_claim_budget`.
2. **Creates and posts a `budget.transfer`** for the apportioned share (e.g.
   100,000): one FROM line at the request's coordinate, one TO line per
   apportionment line. It skips the Buddy check, the Budget-Manager approval
   and e-Saraban (`_skip_submit_review`), like a kmitl_project Direct Floating
   Allocation: the request's own chain — the head's e-Saraban signature and
   the stations' acts — is the control.

So the source loses exactly the income (900,000 + 100,000). If the transfer
fails (pool drained, a destination refused), the consumption rolls back with it.
Submit pre-checks that the pool covers the **budget total**.

An apportioned request **has no reservation** (ใบจองงบประมาณ): reserved money
cannot be moved by a transfer without a release first, and the income is
disbursed as soon as it arrives. Unlike a direct claim it still goes through
e-Saraban.

**Cancel is independent.** Cancelling the request cancels its direct
consumption only; the posted transfer stays, and a Budget Manager reverses it
by hand if the destinations have not used it.

## Considered options

- **Consume the full 1,000,000 and also transfer 100,000 (rejected)** — the
  source would lose 1,100,000; the transfer could not pass its availability
  check on a pool funded by the income alone.
- **Consume 1,000,000 and only top up the destinations (rejected)** — budget
  created out of nothing at the destinations; not a transfer.
- **Draw a reservation and release the apportioned share before transferring
  (rejected)** — three ledger events per request for no control the request
  does not already give.
- **Leave the transfer for a Budget Manager to approve (rejected)** — the
  consumption and the transfer would drift apart, and the 100,000 could be
  spent at the source in between.
- **Reverse the transfer when the request is cancelled (deferred)** — a
  destination may already have spent it; kept manual for now.

## Consequences

- `budget.transfer.disbursement_request_id` links the transfer back; the
  request's `apportionment_transfer_id` makes the act idempotent across a
  divert back.
- Destinations are typed by hand; prefilling them from a KRIS project's
  allocation lines (`kris.project.allocation.line`) is a later bridge.
