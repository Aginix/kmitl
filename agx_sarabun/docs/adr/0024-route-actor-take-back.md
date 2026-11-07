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

**Gating vs non-gating.** Reopening a **gating** step reopens its ลำดับ, which is
what sends the next ลำดับ back to waiting. A **non-gating** step (รับทราบ / CC) never
held the ลำดับ back, so taking it back reopens only that step and leaves the following
ลำดับ untouched. A gating step whose ลำดับ was also passed by another gating actor
cannot be taken back, because reopening it would not reopen anything. The origin is
told through `_on_sarabun_step(step, "take_back")`.

**Followers.** Only followers the engine added itself when it raised a step's to-dos
are unfollowed (`auto_follower_partner_ids`); a follower added to share the หนังสือ
stays. The 16.0.7.4.0 migration has no such record for old rounds, so it unfollows
the old round's unreached holders outright and logs each document and user.

**Limits.** Only steps completed with **complete** can be taken back (เกษียนสั่งการ is
excluded, since it inserts a step). The ผู้จัดทำ row is excluded too, because the
sender already has ดึงกลับแบบร่าง.
