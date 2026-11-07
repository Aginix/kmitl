# ADR-0024 — A route actor may take back their own step (🔙 ดึงกลับ)

**Status:** Accepted
**Date:** 2026-11-07
**Modules:** `agx_sarabun`

---

Someone on the Route who has just acted (for example a ตรวจเอกสาร holder who pressed the
button and then spotted a typo) had no way back. ตีกลับ is for the *next* actor, and
the sender's ดึงกลับ restarts the whole Route.

**Decision.** The actor of a completed step can **🔙 ดึงกลับ** it while the หนังสือ
is circulating and **no later ลำดับ has acted**. Their step becomes active again,
with its outcome cleared (who/when, signature snapshot, ความเห็นในการลงนาม, sign
files). The following ลำดับ goes back to waiting: its to-dos and recipient rows are
removed, and people it no longer reaches are unfollowed, consistent with ADR-0023.
Parallel gating steps that were retired when the ลำดับ passed come back. It works for
any verb. A register number already issued is kept and re-used when the step is signed
again, because `_assign_register_number` is idempotent. The reason is optional and is
logged in the chatter.

The sender's move is renamed **⏪ ดึงกลับแบบร่าง** so the two are not confused.

**Limits.** Only steps completed with **complete** can be taken back (เกษียนสั่งการ is
excluded, since it inserts a step). The ผู้จัดทำ row is excluded too, because the
sender already has ดึงกลับแบบร่าง.
