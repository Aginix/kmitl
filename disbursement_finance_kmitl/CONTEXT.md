# CONTEXT — Disbursement ↔ KMITL Finance Bridge

Glossary for the **post-bill payment-execution workflow** on
`disbursement.request` (DR). This module owns the phase that runs **after** the
accounting office posts the vendor bills.

## The two approval rounds (do not conflate)

The word "ตรวจสอบ / verify" and "อนุมัติ / approve" appear in **two different
rounds**. They use different vocabulary and different security groups.

| Concept | Round 1 — request approval (module `disbursement`, before bill) | Round 2 — payment execution (this module, after bill) |
|---|---|---|
| Verify | **Request Verification** — state `verified`, "ตรวจสอบคำขอ", `group_disbursement_officer` | **Payment Audit** — state `payment_audited`, "ตรวจสอบการเบิกจ่าย", `group_disbursement_payment_auditor` |
| Approve | **Request Approval** — state `approved` (obligates + consumes budget), "อนุมัติคำขอ", `group_disbursement_manager` | **Payment Authorization** — state `payment_authorized`, "อนุมัติเบิกจ่าย" (rector delegate), `group_disbursement_payment_authorizer` |

Round 2 deliberately uses the verbs **audit** and **authorize** so it never
collides with round 1's verify/approve.

## Terms

- **Payment Audit** (`action_audit`, `bills_posted → payment_audited`): the
  auditor checks the disbursement documents after the bills are posted.
- **Payment Authorization** (`action_authorize`, `payment_audited →
  payment_authorized`): the rector's delegate authorises the money to be paid.
- **Payment** (`action_create_payment`, run while `payment_authorized`): the
  finance office creates one `account.payment` per posted bill (net of WHT),
  submits it and sends it to the bank via a bank payment export. The request
  stays at `payment_authorized` while the payment is in transit.
- **Bank Result** (`account.payment.bank_result_status`): the actual outcome
  reported by the bank for an outbound e-payment (`success` / `failed`),
  recorded from the bank payment export line.
- **Paid** (`action_confirm_paid`, `payment_authorized → paid`): the finance
  office confirms every payment of the request succeeded at the bank. The money
  has left; the accounting entry is **not** posted yet.
- **Cleared / ล้างหนี้** (`paid → cleared`): the accounting office posts the
  payment move through the **same account.move maker-checker as the vendor
  bill** (Approve = post). Posting reconciles the payment against the bill,
  clearing the payable. Set in `account_move._post`. This is the KMITL sense of
  "ล้างหนี้" — recording the cash-out and matching it to the liability.

## Rules

- The workflow is **forward-only** in round 2: there is no reject/return. A
  request that must be corrected is cancelled (before payment) or the bill is
  reversed by accounting.
- **Budget is untouched** in round 2. It is obligated and consumed exactly once
  at round-1 `approved` and never re-cut here.
- A DR payment move can be **posted only after the request is `paid`** and the
  payment's bank result is `success` (guard in `account_move._post`). A failed
  bank transfer therefore never produces an accounting entry.
- **Full payment only** — each bill is paid in full (no partial). For a
  multi-partner DR there is one payment per bill; the DR reaches `paid` only
  when every payment is confirmed success, and `cleared` only when every
  payment is posted.

## System note

Payments linked to a DR (`account.payment.disbursement_request_id`) are posted
by accounting through the account.move approval queue, exactly like the bill.
The deferred reconcile that normally lives in `account.payment.action_post`
runs on the move-posting path here, so **posting a DR payment == clearing it**.

See `docs/adr/0001-payment-execution-via-account-move-workflow.md`.
