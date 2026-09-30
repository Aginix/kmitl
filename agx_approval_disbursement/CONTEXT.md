# Approval ↔ Disbursement Bridge

Links an **Approval Request** to the **Disbursement Request** it is billed into, and governs how a disbursement is returned for correction: the disbursement is kept intact while its approval request is corrected in place.

## Language

**Approval Request (AR)**:
The upstream request (`approval.request`) that reserves budget and, once approved, is billed into one disbursement.
_Avoid_: expense request, claim

**Disbursement Request (DR)**:
The downstream payment document (`disbursement.request`) created from a billed Approval Request; it draws the reservation down when approved.
_Avoid_: bill, payment request

**Bill**:
The act of turning an approved Approval Request into a Disbursement Request; moves the AR to `billed`. One DR covers exactly one **payment type** (จ่ายตรง/สำรองจ่าย/เงินยืม), chosen via a wizard — an AR with several payment types on its actual-expense rows is billed once per type, and the "Submit for Disbursement" button stays available until every type present has its own DR (see [ADR-0002](docs/adr/0002-advance-is-a-disbursed-payment-type.md)).
_Avoid_: invoice, charge

**Return (ตีกลับ)**:
The verification officer sending an approval request back because its data is wrong. The Disbursement Request is kept as-is at `signed`; only the Approval Request moves to `returned`.
_Avoid_: reject, refuse, cancel

**Returned (state)**:
The Approval Request state entered when its disbursement is returned; only the payee bank, description and disbursement evidence may be edited here.

**Correction (การแก้ไข)**:
The requester's edit of a returned request's payee bank, description and disbursement evidence, then **Confirm Correction** — which pushes those onto the kept disbursement request and moves the approval request back to `billed`.
_Avoid_: revision, amendment
