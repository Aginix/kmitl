# ADR-0019 — Correct a signed step's capacity and regenerate the signed PDF

**Status:** Accepted
**Date:** 2026-10-16
**Modules:** `agx_sarabun_route_edit_person_capacity` (bridge, auto-install),
`agx_sarabun_pdf_regenerate` (optional)

**Amends [ADR-0009](./0009-signature-block-snapshots-name-position-signature.md)**
(the signature snapshot is never rewritten) for one field, and the immutability of the
ฉบับลงนาม.

---

## Context

With `agx_sarabun_person_capacity`, a บุคลากร (Person) step carries a **capacity
ตำแหน่ง**, the title printed under the signature. The signer picks it when signing, and
ADR-0009 freezes it into `signed_position_name`. Sometimes it is genuinely wrong (the
wrong one of the person's titles). Today there is no fix short of Reset (ADR-0011),
which voids every signature and re-runs the whole route. That holds even after the
หนังสือ has completed and its signed PDF is frozen.

## Decision

**Correct the capacity.** A Sarabun Route Editor (ADR-0018) may correct the ตำแหน่ง
of a signed step, using the ✏️ row button on the Route (a small wizard). It works on
a circulating **or a completed** หนังสือ.

- **Eligible steps:** positive-done, `show_signature`, non-originator, Person mode.
  A Position-mode step's capacity *is* its target, so it is not eligible.
- **The new Position** must be one the person currently holds. This is the rule
  person_capacity enforces at signing.
- **What changes:** the step's `position_id` (the capacity label), its
  `signed_as_position_id` when the verb recorded one, and the frozen
  `signed_position_name` the block prints.
- **What stays as signed:** the name, signature image and date.
- **No chatter entry.** Only route editors may do it. The write runs `sudo` after the
  authority check, because a signed step is locked to user writes and a completed
  หนังสือ is read-only.
- **Where it lives:** a bridge, `agx_sarabun_route_edit_person_capacity`. The field is
  person_capacity's and the authority is route_edit's, so neither depends on the
  other. It is `auto_install`.

**Regenerate the signed PDF.** On a completed หนังสือ the frozen PDF still shows the old
title. A **Sarabun Manager** may use **สร้างไฟล์ PDF ใหม่** in the form's Action (⚙)
menu, from the separate optional module `agx_sarabun_pdf_regenerate`. Manager covers
the Route Editor too, since that group implies Manager.

- It re-renders the PDF from current data through the core `_freeze_signed_copy`.
- It **replaces** the frozen file and its visible attachment copy; the old one is
  deleted, so only one ฉบับลงนาม exists.
- `signed_at` becomes the regeneration time.
- No chatter entry.

## Consequences

- ADR-0009's "a signed หนังสือ is never rewritten" now has one admin exception, the
  capacity title. ADR-0018's "done steps are locked" keeps the same exception.
- The frozen ฉบับลงนาม is no longer strictly immutable. A manager can replace it, and
  the replaced file is not kept.
- Both menu actions cannot hide by state. Regenerate refuses a หนังสือ that is not
  completed.
- After both modules are installed, the route-edit step dialog also shows the capacity
  of an acted step as read-only. The bridge repeats person_capacity's attrs with the
  readonly rule. This closes ADR-0018's server-only guard on that field.
