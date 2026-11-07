# ADR-0023 — No attempt history on ตีกลับ / ดึงกลับ / Reset

**Status:** Accepted
**Date:** 2026-11-07
**Modules:** `agx_sarabun` (core), `agx_sarabun_reset`

**Supersedes** the "archive-not-overwrite" rule of
[ADR-0006](./0006-recall-split-pullback-vs-cancel-send.md) and ADR-0002 §3.4, and
amends [ADR-0013](./0013-e-saraban-access-control-model.md): an old round's recipient
rows are deleted, so read for those people rests on following.

---

Until now a ตีกลับ, ดึงกลับ or Reset froze the whole Route as history (steps set to
`active=False`, `attempt_seq` bumped) and recreated a fresh one. Nobody used that
history, so it was dead weight. It also held earlier signers' comment files and kept
everyone from the old round able to read the หนังสือ.

**Decision.** These three moves now **delete** the old round: its steps, their
recipient rows, to-do links and sign-comment files. `attempt_seq` stays at 1.
Read access: people the หนังสือ reached in the old round were subscribed as followers
when their to-do was raised, and they **keep reading it** as followers (UAT decision
2026-11-07). People it has **not reached yet** never could read it, so a waiting step
still grants nothing.
What remains is the chatter: the reason of a ตีกลับ / ดึงกลับ / Reset and the
document's tracked changes.

**Mechanism.** The steps are still set aside first (`active=False`), so the origin
callbacks of the same transaction (`_on_sarabun_returned`, `_on_sarabun_step`, …)
can read the returned step. `_purge_archived_steps` deletes them when the flow ends:
after the last callback of `act_on_step` (ตีกลับ), after `action_pull_back`,
`_restart_chain` and the reset. A returner who loses read is sent to their incoming
box instead of a form that would fail to reload. The 16.0.7.4.0 migration deletes
the history that already exists.

**Consequences.** The ตีกลับ reason must be written into the chatter, because the
returned step no longer survives (it is also shown to the sender as a banner). The deletion cannot be undone, so take a database backup
before deploying.
