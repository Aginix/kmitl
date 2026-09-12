# 0002 — Freeze งวด on disbursement.request, not on WA acceptance

Status: accepted (2026-09)

## Context & Decision

The requirement uses two related-but-not-identical terms for the "งวดที่ต้อง
ปกป้อง" gate on case 2.2:

- "งวดที่ตรวจรับแล้ว" (งวด with WA accepted)
- "งวดที่มีเบิกแล้ว" (งวด with a disbursement request)

WA acceptance is a strict prerequisite for a disbursement request in this
codebase, so the two form a chain: WA accepted → disbursement raised → paid.
Freezing on WA acceptance is stricter (earlier lockout); freezing on
disbursement is looser (later lockout).

We freeze on ``disbursement.request`` presence.

## Why

- User request. During the design grill, the user explicitly asked for the
  looser gate: "จะสร้างใบเบิกได้ ต้องตรวจรับเสร็จก่อน" — i.e., because WA is
  a prereq for disbursement, freezing on disbursement is a subset of freezing
  on WA. This gives the finance team a window between WA acceptance and
  disbursement submission where they can still reshape the งวด if
  paperwork surfaces a correction.
- Real-world workflow: WA is often signed by inspection staff, but the
  disbursement paperwork is prepared later by a different officer. A late
  correction to งวด structure (e.g., splitting a งวด into two) is legitimate
  up until the disbursement request is filed.

## Consequences

- The ``is_frozen`` compute on ``purchase.contract.invoice.plan`` checks for
  a ``disbursement.request`` on the parent PO. When the disbursement model
  gains an explicit ``installment_id`` link, the check will tighten to
  per-งวด granularity (currently it approximates via ``invoiced`` on the
  source งวด).
- The lower-bound constraint on ``sum(new PO amount) ≥ sum(frozen งวด)``
  uses this same freeze definition — it's the sum of งวด that have a
  disbursement.request, not the sum of WA-accepted งวด.
- Note the language in the CONTEXT.md glossary — "Frozen งวด" is defined as
  the disbursement-based version. Anyone reading the code who expects the
  stricter WA-based interpretation from the raw requirement text will find
  this deviation surprising and should be pointed at this ADR.
