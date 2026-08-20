# 0007 — A request crosses the Hand-over when its last voucher is paid, not when someone presses

- Status: **accepted**
- Date: 2026-08-19
- Refines: ADR-0005 (the Hand-over stays exactly where it was; what changes is who moves
  it)

## Context

ADR-0005 made the Hand-over a single human confirmation given once per request, on the
request, standing for every payment it covers — so that nobody had to confirm the same
fact twice in two places.

That holds while one person can honestly give it. A request's payees are served from
whichever หัวจ่าย their **เรื่องที่จ่าย** chose, and an e-payment file debits exactly
one account, so a request with payees on four paying accounts leaves in four files. The
assignment rules route by paying account among other things, so those four files are
routinely four different officers' work.

Asking one of them to press "จ่ายครบ" for the whole request asks them to vouch for three
files they never uploaded and never saw a bank reply for. In practice that is either
guessed or chased by walking round the office — and the press it produces reads in the
system as a first-hand assertion.

## Decision

Nobody presses it. The request crosses when the last of its vouchers is paid.

Each officer confirms the file they handled; closing a file marks every voucher it
carried `finance_state = paid` (finance_kmitl ADR-0004); and a voucher turning paid asks
its request whether they all are now (`_try_hand_over_when_all_paid`). The officer who
happens to be last brings the request across without having to know they were last.

The confirmation ADR-0005 asked for is still given exactly once per voucher, and still
by the person who is in a position to give it. What is dropped is the _aggregation_ of
those confirmations into one press by someone who did not make them all.

## Consequences

- **The join is the voucher, not the file.** A voucher belongs to one request and at
  most one file, and a payee settled by cheque or cash is still a voucher. Counting
  vouchers covers every payee; counting files does not — a request whose files are all
  closed can still have a cheque payee unpaid, or a หัวจ่าย whose file nobody has made
  yet.
- **`_hand_over` is idempotent and filters on the state it crosses _from_.** It is
  reached from the voucher write and from the override press below, and the accounting
  office must not get the same Todo twice.
- **A voucher left at `finance_state = draft` holds the request here**, and that is
  correct: it has not been paid and the accounting office has nothing to book for it.
  What says so is the finance office's own Todo, which stays open until the crossing,
  and จ่ายแล้ว n/m on the request. The old press used to quietly confirm such a voucher
  for the bank on its way through; nothing does that silently now.
- **`action_confirm_paid` on the request survives as a technical override**, in
  developer mode only (`base.group_no_one`). It confirms whatever is still draft, marks
  the rest paid and crosses, all in one — the way past a voucher stuck for a reason that
  is not the office's to fix.
- **A voucher that enters no file is confirmed on itself.** Cheque and cash payees have
  no file to close, so `account.payment.action_confirm_paid` accepts them even on a
  request — the refusal there is narrowed to the vouchers that do travel in one, for
  which closing the file is already that press. Without this, moving the request's own
  button to developer mode left such a payee with no reachable press at all.
- **Three things are watched, because there are three ways to stop being unpaid.**
  `finance_state` turning paid is a write on this model, so `write` catches it. Leaving
  is not: `state` belongs to the journal entry through `_inherits` and core cancels by
  calling `move_id.button_cancel()`, so `action_cancel` and `unlink` are hooked directly
  rather than inferred from a write that never happens.
- **The crossing runs `sudo`.** It writes `disbursement.request.state`, and the officer
  who triggers it holds write on the e-payment file and read-only on the request — so
  without it, closing a file raises `AccessError` and rolls back, taking the file with
  it. Same reason `_try_create_payments` is sudo'd.

## Rejected alternatives

- **Keeping the single press and telling the officer what is still outstanding** (a
  count, a list of the files not yet closed). Cheapest, and it leaves the press itself a
  claim about work the presser did not do.
- **Crossing when every e-payment file of the request is closed.** This is the shape the
  problem is first described in, and it is wrong twice over: it ignores the payees who
  travel in no file at all, and it is satisfied by "all the files that exist are closed"
  on a request whose fourth file was never made.
- **An owner on the file, assigned like the voucher's.** Would make "whose file is this"
  explicit, at the cost of a second assignment concept to route and maintain — and it
  answers a different question from the one blocking here, which is not who owns a file
  but who may speak for all of them.
- **A cron that sweeps requests whose vouchers are all paid.** Same outcome, minutes
  late, and it puts a request's crossing somewhere no officer's action explains.
