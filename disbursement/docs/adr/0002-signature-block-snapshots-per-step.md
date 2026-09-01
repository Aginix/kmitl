# The printed signature block is a child model of frozen per-step snapshots

The ใบขอเบิก PDF must show a real signature (image + ชื่อ + ตำแหน่ง + วันที่) for every
actor in the request's flow — the officer who verifies, the Finance Director, the
Rector-delegated approver, and, after the bills are posted, the payment auditor and
the payment authoriser. The request already stored *who acted when* for four of those
five steps, but nothing printed and the `report_disbursement_request_signature`
template had been an orphan since it was written.

## Decision

Each signature is a row on a new **`disbursement.request.signature`** child model
whose ชื่อ / ตำแหน่ง / ลายเซ็น are **snapshotted at the instant the step is taken** —
`signed_name`, `signed_position_name`, `signed_signature`, written by
`disbursement.request._stamp_signature(step)` under `sudo`. The field names
deliberately mirror `sarabun.routing.step` (agx_sarabun
[ADR-0009](../../../agx_sarabun/docs/adr/0009-signature-block-snapshots-name-position-signature.md)),
whose reasoning applies verbatim here: an ใบขอเบิก is a government financial record,
and *any* re-render showing a signature the signer did not make at that moment is an
integrity failure. A name correction in HR, a job-title change, or a replaced
signature image must never rewrite an already-signed request — and the PDF is
re-renderable at will, including from the portal.

## Considered options

- **Dereference `user.employee_id.signature` live at render time (rejected)** — the
  smallest possible change (no new model, no new fields beyond the missing Validate
  stamp), and it is what `purchase_work_acceptance_kmitl` does. Rejected for the
  ADR-0009 reason above: a signature image is mutable master data, and the DR keeps
  being reprinted long after approval, through the bill and payment stages.
- **Snapshot into flat fields on `disbursement.request` (rejected)** — five steps ×
  three snapshot values is fifteen new columns on an already wide model, and the two
  post-bill steps live in `disbursement_finance_kmitl`, so the bridge would have to
  add its own six columns *and* inherit the report template to render them.
- **Route steps 3–7 through e-Saraban to reuse its block (rejected)** — the routing
  engine is the wrong tool for an in-app, group-gated, forward-only approval that
  already has its own state machine (ADR-0001), and it would make the internal
  finance workflow depend on the correspondence system.

## Consequences

- **The bridge only declares and stamps.** `disbursement_finance_kmitl` adds its two
  steps with `selection_add` and calls `_stamp_signature`; the block in `disbursement`
  loops every row, so no report inheritance is needed. This fell out of the child
  model and is the main reason it was chosen over flat fields.
- **Superseded rows are archived, not deleted.** The rule is *archive wherever the
  workflow already clears the matching stamp*: `_reset_approval` archives the two
  approval rows (so cancel / reset-to-draft / return-to-verification are covered for
  free), `action_request_approval` archives them on its own inline clear, and
  `_reset_verification` archives the Validate row. `active=False` keeps "who signed
  the previous round" while the PDF prints only the current one. The payment-execution
  steps are forward-only and their stamps are never cleared, so they are never
  archived either.
- **The role caption is NOT snapshotted.** `step` is a Selection: the role belongs to
  the *step*, not to the person, so relabelling "Verified by" later should — and does —
  correct every historical document. Only identity is frozen.
- **The image falls back to live master data when the snapshot is empty** — the
  computed `signature_image` is what the report prints. This covers the real case of
  someone who approved before uploading their signature, without weakening the freeze:
  a snapshot that exists always wins. The fallback is read under `sudo` and lives in
  Python rather than the template, because ordinary users cannot read another person's
  `hr.employee` and whether the official document shows a signature must not depend on
  who is printing it.
- **`disbursement` now depends on `hr`** (via `hr_employee_digitized_signature`) and on
  `thai_date_utils` for `format_datetime_thai_sign`. The snapshot source is read under
  `sudo` so capturing the official-record identity does not depend on the acting user's
  `hr.employee` read grants.
- **The requester and the head-of-department are deliberately out of scope.** The
  requester signs nothing on this form, and the head's signature is already rendered
  by `agx_sarabun`'s own block, which `disbursement_sarabun` now injects *before* the
  `o_dr_signatures` anchor so the two blocks read in chronological order.
- **A term was freed up.** `disbursement_sarabun`'s head-of-department position was
  named "ผู้อนุมัติเบิกจ่าย", the same words as the post-bill payment authoriser's
  group. With both signatures now on one page it was renamed to "หัวหน้าส่วนงาน
  (Head of Department)"; because that record is `noupdate="1"`, an existing database
  needs the rename done once by hand in Configuration ▸ Positions.
