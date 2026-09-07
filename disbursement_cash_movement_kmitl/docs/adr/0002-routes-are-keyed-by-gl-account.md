# A cash route is keyed by GL account, not by หัวจ่าย

Every other context in this repo treats หัวจ่าย (`account.payment.method.line`)
as the unit of "which account money leaves from" — a disbursement picks a
เรื่องที่จ่าย, which derives a หัวจ่าย per payee; the paying account *is* the
destination everywhere else. A cash route breaks that convention on purpose and
points at the underlying `account.account` instead.

## Considered options

- **Key by หัวจ่าย** (`account.payment.method.line`), matching every other
  context. Rejected: `account_kmitl` already enforces that every หัวจ่าย booked
  against one bank account uses the same GL account
  (`account_payment_method_line.py::_check_paying_account`) — a current account
  drawn on by both transfer and cheque is two หัวจ่าย rows for one route. Keying
  by หัวจ่าย would mean seeding, and maintaining, the identical hop chain twice
  for every such account; keying by GL account states it once.
- **Key by GL account** (chosen). One route serves every หัวจ่าย booked against
  that account, whatever method pays it — which is also exactly how the source
  Excel groups its blocks.

## Consequences

- **A route is discovered from `account.payment.outstanding_account_id`**, not
  from `payment_method_line_id` directly — core already resolves that GL
  account for any payment method, so the lookup does not care whether the
  voucher paid by transfer or cheque.
- **A future reader has to know this is deliberate.** Every other paying-account
  reference in the repo is a หัวจ่าย; a route naming a GL account instead reads,
  at first glance, like a mistake rather than a considered exception.
