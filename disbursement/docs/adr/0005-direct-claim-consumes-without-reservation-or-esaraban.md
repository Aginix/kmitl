# A direct claim (ตั้งเบิกตรง) consumes the pool directly and skips e-Saraban

Some disbursements are authorised by a memo (หนังสือบันทึกข้อความ) produced outside
the system. They have no budget reservation (ใบจองงบประมาณ) and no source document,
yet under budget control a request could not be approved without a reservation
(`_check_commitment_obligable`), and with `disbursement_sarabun` installed it could
not reach `signed` without a หนังสือ routed through e-Saraban — the memo's signature
would be collected twice.

## Decision

A request ticked **ตั้งเบิกตรง** (`is_direct_claim`) is a **direct claim**:

- **No e-Saraban.** It cannot be submitted to Sarabun; Submit requires the
  **memo number** and at least one attachment (the memo itself) and moves the
  request straight to `signed`. Every later step — the officer's Validate and
  the two-approver step (ADR 0001) — is unchanged.
- **Reservation optional.** A direct claim may still draw a reservation, and
  is then consumed through it like any request. Without one it carries its own
  dimensions and budget code, and on the Rector-delegated approval
  `disbursement_direct_claim_budget` posts a **Direct Consumption** (ตัดงบตรง, budget
  ADR-0019) for the request's amount; cancelling the request cancels it.
  Availability is pre-checked on Submit and enforced again when posting.
- **Anyone may tick it.** The request's own approval chain — officer, Finance
  Director, Rector-delegated approver — is the control, so the Budget-Manager
  right ADR-0019 requires for a hand-posted direct consumption is waived for a
  consumption posted by an approved request (context
  `budget_direct_consume_by_document`). The pool and dimension checks still run.

The **memo number** (`memo_number`) lives in core so both paths share it: typed by
hand on a direct claim, stamped by `disbursement_sarabun` the instant e-Saraban
issues the number otherwise (new `_on_sarabun_numbered` origin hook).

The feature is an opt-in extension, not core: **`disbursement_direct_claim`**
(the flag, the memo checks, submit → `signed`; installed with `-i`) and the
auto-installed bridge **`disbursement_direct_claim_budget`** (direct consumption,
its two submit rules). Core keeps only what the regular flow also uses: the
memo number, the head-signed date (`sign_date`, stamped on sign unless already
set) and the dates group. `disbursement_sarabun` needs no glue: a direct claim
moves from draft to `signed` in one call and never waits at `submitted`, the
only state its submit button and guard act on.

## Considered options

- **The request reserves its own commitment on Submit (rejected)** — holds the
  budget while the request waits for approval, but creates a reservation per
  unplanned expense: the paperwork ADR-0019 set out to avoid.
- **Reserve and consume in one go on approval (rejected)** — no budget held either,
  and a reservation slip that exists only to be emptied.
- **Keep direct consumption Budget-Manager-only (rejected)** — every direct claim
  would need a budget officer to post it by hand after the request is approved,
  outside the request's own flow.
- **Keep e-Saraban for direct claims (rejected)** — the external memo already
  carries the head of department's signature.

## Consequences

- No budget is held between Submit and approval; a pool drained in the meantime
  makes the approval fail, and the request goes back to fix its dimensions.
- `budget_direct_move_id` on the request links the posted consumption; a request
  returned to verification and approved again keeps it (idempotent).
