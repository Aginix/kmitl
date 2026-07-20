# Signature block renders a per-step snapshot of ชื่อ / ตำแหน่ง / ลายเซ็น, not live master data

**Extends [ADR-0003](./0003-position-catalog-not-hr-job.md) and amends the *Signature block content* of [ADR-0007](./0007-official-pdf-source-embeds-endorsement-block.md) / [ADR-0008](./0008-signatures-only-showsignature-and-nonsigning-drafter.md).** ADR-0003 snapshots the *holder-set* onto a step at activation "so later org changes never rewrite history" — but that guarantee covered only *who may act* (`actor_user_ids`), never the values printed in the signature block. ADR-0007/0008 defined the block to render, per positive-done `show_signature` step: a signature image, the signer's ชื่อ, their ตำแหน่ง, the วันที่, and their ความเห็น. Three of those were dereferenced **live** at render time — the image from `hr.employee.signature`, ชื่อ from `hr.employee.name`, ตำแหน่ง from `sarabun.position.name`.

Only two of the five were durable: `acted_date` and `note` are stored scalars on the step. The other three are live foreign-key dereferences into mutable master data. So after a หนังสือ is signed, any later edit — an employee's name correction, a position renamed in an org restructure, a replaced signature image — silently rewrites the rendered signature on the already-signed, historical document.

The frozen `signed_pdf` (ADR-0007 §5.4) does not close this: it freezes rendered *bytes* only at `completed`, and only on the `/pdf` path. The block still renders live (a) in the on-screen preview (always a live render), (b) whenever the **origin record is printed directly** — ADR-0007 explicitly accepted the block appears there — and (c) it captures each signer only as-of-completion: on a multi-signer document, an early signer who changes their signature before the final sign is rendered with the *new* image even in the frozen PDF.

## Decision

The signer's rendered identity is **snapshotted onto the step at the instant of signing** — the same principle ADR-0003 applies to holder resolution, now extended from routing *resolution* to the *rendered block*.

- Three snapshot fields on `sarabun.routing.step`: `signed_name`, `signed_position_name`, `signed_signature` (image). With `acted_date` + `note` already persisted, all five block values are now durable.
- Written in `_stamp()` and in `_sign_originator_step()` (the auto-sign at send), gated on **positive disposition ∧ the step's verb has `show_signature`** — the exact filter `_signature_block_steps()` renders. Non-signing verbs (ตรวจสอบ / พิจารณา / ส่งต่อ, a non-signing ผู้จัดทำ) and a ตีกลับ / ปฏิเสธ snapshot nothing.
- `signed_position_name` prefers the signed capacity (`_resolve_capacity`), else the step's target Position — mirroring the block's fallback order.
- The block reads **snapshot-first with a live fallback** (`signed_signature or acted_by_id.employee_id.signature`, …) so legacy / in-flight rows still render.

## Considered options

- **Freeze only the PDF, treat every live re-render as non-authoritative (rejected)** — declaring `signed_pdf` the sole official record and the direct-origin print a mere "view". Rejected: for a government หนังสือ, *any* rendering showing a wrong signature is an integrity failure, and the direct-origin print is a real, accepted path (ADR-0007) with no cheap way to redirect it to the frozen bytes.
- **Snapshot only ชื่อ + ลายเซ็น; keep ตำแหน่ง as the live FK deref (rejected)** — `sarabun.position.name` is editable and `translate=True`; a renamed post would still rewrite history. All three drift, so all three are snapshotted.
- **Snapshot on every done step regardless of verb (rejected)** — needlessly copies signature images onto ตรวจสอบ / พิจารณา / reject / return rows that never render. Gating on `show_signature` writes exactly what the block reads.

## Consequences

- **`_stamp` / `_sign_originator_step` write three more fields** on show_signature steps. `signed_signature` is `attachment=True`, so identical images dedupe by checksum — no meaningful storage cost.
- **The block is now correct on every path** — frozen PDF, live preview, direct-origin print, and the Route display — and each signer is captured as-of-*their own* signing, not as-of-completion.
- **The fallback keeps old rows working**; when the academic prefix lands (phase-2, ADR-0007) it snapshots here too, for the same reason.
- **Pre-production** — the whole stack is on the feature branch, not in `origin/16.0`; no migration of existing frozen copies or signed steps.
