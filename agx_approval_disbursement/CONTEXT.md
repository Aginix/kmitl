# Approval ↔ Disbursement Bridge

Links an **Approval Request** to the **Disbursement Request** it is billed into.

## Language

**Approval Request (AR)**:
The upstream request (`approval.request`) that reserves budget and, once approved, is billed into one disbursement.
_Avoid_: expense request, claim

**Disbursement Request (DR)**:
The downstream payment document (`disbursement.request`) created from a billed Approval Request; it draws the reservation down when approved.
_Avoid_: bill, payment request

**Bill**:
The act of turning an approved Approval Request into a Disbursement Request; moves the AR to `billed`.
_Avoid_: invoice, charge

**Disbursement evidence (หลักฐานการเบิก)**:
Attachments on the Approval Request flagged `is_disbursement_evidence`, copied onto the Disbursement Request when it is created.
_Avoid_: correction evidence (the DR-return flow that produced that name is gone — see ADR-0001).
