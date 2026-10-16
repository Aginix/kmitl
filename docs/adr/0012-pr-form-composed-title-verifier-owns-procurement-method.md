# พ.1 form: the requester answers in plain words, the Verifier owns procurement details, titles are composed

## Status

Accepted (2026-10-06). Amends
[ADR-0010](0010-pr-split-verify-and-budget-commit-direct-entry.md), which lists what the
Verifier enters.

## Context

UAT users could not fill the draft พ.1. Some fields were staff knowledge that a
requester cannot answer:

- วิธีการจัดซื้อจัดจ้าง (the Procurement Method);
- the e-GP checkbox.

The free-typed `title` became the เรื่อง of the หนังสือ verbatim. It came out in every
format but the official one, which is ขอให้{ประเภทการจัดซื้อ/จ้าง}{ประเภทค่าใช้จ่าย},
e.g. "ขอให้ซื้อวัสดุการศึกษาใช้ไป".

## Decision

1. **The title is composed and never typed, on both documents.**
   - The พ.1 title is `ขอให้{type}{expense}`. The requester fills the two blanks in one
     inline row, and the full title shows read-only underneath.
   - The พจ.1 composes `รายงานขอ{type}{expense}` from its own copies of the two values
     (ADR-0004). God Mode changes it only through those values.
2. **ประเภทค่าใช้จ่าย is free text for now.**
   - The requester writes it; the Verifier may correct it.
   - A project PR starts as "วัสดุในโครงการ", and only when the field is empty.
   - A plan PR takes the plan's ชื่อรายการ.
   - It is the same notion as a budget code's expense type, but it is not linked to one.
3. **The requester still picks the Procurement Type,** but only as the verb of the title
   row.
   - Each type name is a single verb phrase. จ้างทำของ/จ้างเหมาบริการ is split into two
     types.
4. **The Procurement Method and e-GP belong to the Verifier.**
   - They are hidden while drafting.
   - Only the verify group may edit them, at `to_verify` and `returned`.
   - ตรวจสอบ refuses a พ.1 without a method.
   - e-GP is forced above 100,000. Below that it is the Verifier's tick, and a new
     amount resets it.

## Considered options

- **Keep `title` editable and pre-fill it.** Rejected. The point is that the หนังสือ's
  เรื่อง always has the official shape. Staff can still edit the เรื่อง on the หนังสือ
  itself.
- **A separate "title wording" on each procurement type.** Rejected. Renaming the one
  combined type is enough, and a second wording would make the row and the title
  disagree.
- **Let the Verifier pick the Procurement Type too.** Rejected. ซื้อ/เช่า/จ้าง is
  something the requester knows. Written as the verb of the title, it no longer reads as
  procurement jargon.

## Consequences

- **Old UAT records keep their typed titles.**
  - Odoo does not recompute an existing column on `-u`.
  - The compute leaves the title alone while the expense type is empty.
  - Old drafts are pushed into the new shape the first time the requester fills the
    expense.
- **The compute depends on the type record, not on its name.** Renaming a type, as the
  007 split does, does not rewrite titles already issued.
- **A พจ.1 made from an old พ.1 (no expense type) receives that พ.1's typed title.** It
  does not get a half-empty "รายงานขอซื้อ".
