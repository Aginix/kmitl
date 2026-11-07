# ADR-0022 — A recipient may edit the หนังสือ while circulating (แก้ไขเอกสารได้)

**Status:** Accepted
**Date:** 2026-11-06
**Modules:** `agx_sarabun` (core)

**Amends [ADR-0013](./0013-e-saraban-access-control-model.md)** — a reached actor is no
longer always read-only.

---

Some steps exist to fix the หนังสือ, e.g. a ธุรการ who corrects the เรื่อง or adds a
file before it goes up. Until now only the ผู้จัดทำ could edit, and only in draft /
returned, so these fixes had to go through ตีกลับ and a re-send.

A verb can now be flagged **แก้ไขเอกสารได้**. While a step with that verb is active,
its holders may edit the content fields: เรื่อง, เรียน, เนื้อหา (and มีเนื้อหา),
หมายเหตุ, อ้างถึง and สิ่งที่ส่งมาด้วย. The right ends when the step is acted on.
With several holders, all of them may edit until the first one acts.

**Mechanism.** The document stores the set of users who may edit it right now
(`content_editor_user_ids`, recomputed from the active steps). A write-only
`ir.rule` on that set grants them write access. This is also what lets them upload
สิ่งที่ส่งมาด้วย, because `ir.attachment` checks write access on the document.
`write()` then limits such a user to the content fields. Every edit they save posts a
chatter note, and the tracked เรื่อง shows its old and new value.

**Alternatives rejected.**
- *Run the write with sudo after a check.* Attachment uploads go through
  `ir.attachment` and never reach that code, so it cannot cover สิ่งที่ส่งมาด้วย.
- *Send the หนังสือ back to the ผู้จัดทำ (ตีกลับ).* This is the round trip the
  users asked to avoid.

**Accepted consequence.** An edit may come after earlier signers have signed. Their
signatures then sit on content they did not see. The users chose this over blocking
the edit; the chatter shows who changed what and when. A สำเนาเรียน (CC) step whose
verb carries the flag also gets the right. Whether CC / forward steps should is still
open.
