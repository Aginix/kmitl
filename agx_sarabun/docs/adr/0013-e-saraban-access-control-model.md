# The e-Saraban access-control model: recipient-ledger visibility, read that persists across attempts, and act-without-write

The access model was until now implicit in `security/security.xml` + inline
comments — one of which is **wrong** (the actor rule's comment claims read
"spans prior re-send attempts", but the rule traverses the `active=True`
`routing_step_ids` only, so an archived attempt would drop out under `active_test`).
This ADR records the model explicitly and pins the two changes the
systray→native-activity move ([ADR-0014](./0014-dissolve-inbox-tray-onto-native-activity-and-todo-bridge.md))
requires. The stakeholder's requirement, verbatim: *a user may access their own
document; if they are **involved** with a หนังสือ they may access it too but
**cannot edit/delete** — except the route actions (ลงนาม/อนุมัติ/รับทราบ) they
are entitled to.*

## Decision

**The recipient reach-ledger is the single visibility key.** A user may **read**
a `sarabun.document` iff they are:

- its **sender** (`sender_user_id` — read/write/create, no unlink), **or**
- **involved** = they hold (or have ever held) a `sarabun.step.recipient` row on
  any of its steps — read only (`perm_write`/`create`/`unlink` = False), **or**
- a **Manager** (`group_sarabun_manager` — sees all),

`AND` the global multi-company rule. Recipient rows are minted (via sudo) for
**every** snapshot holder the instant a step activates — gating actors **and**
non-gating รับทราบ / สำเนาเรียน (CC) holders alike — and are **never deleted**.
Keying read on the same permanent per-person ledger as the กล่องหนังสือเข้า
(Incoming box) is deliberate: the two surfaces can never diverge.

**Read persists after completion *and* across ตีกลับ / ดึงกลับ / Reset.** Being
*involved with a หนังสือ* is a property of the หนังสือ, not of the current
attempt: someone who signed or was CC'd in a prior round must still be able to
open the หนังสือ they handled (audit trail). Because those three transitions
archive the whole chain (`active=False`) and `routing_step_ids` is
`active`-scoped, a raw `routing_step_ids.recipient_ids.user_id` traversal would drop
prior-attempt holders once the chain is archived — the search-domain join injects
`active_test` on `sarabun.routing.step`; the same flag, via a *different* ORM path
(x2many value conversion), is why `archived_step_ids` needs
`context={'active_test': False}` to read at all. The visibility key is
therefore a **stored `reached_user_ids` (M2m)** that aggregates recipient users
across **active + archived** steps (resolved with `active_test=False`), and the
actor rule keys on that field.

**Write = sender only; unlink = manager only.** The sender rule alone carries
`perm_write`; the involved-actor rule is read-only; no user-group rule grants
`unlink`. So an involved non-sender may read the whole Route (the เกษียน trail /
who-acts-next) but cannot edit or delete the หนังสือ.

**Route actions run act-without-write.** A user-initiated transition
(complete / เกษียนสั่งการ / มอบหมาย / ตีกลับ / ปฏิเสธ / ดึงกลับ / ยกเลิกการส่ง /
Reset) verifies authority against the **actor** (`actor ∈ actor_user_ids`, or the
sender/manager/`group_sarabun_reset` guard) and **then** runs privileged
(`sudo`); the identity is recorded as `acted_by_id = actor`, never the sudo
user. This is the sanctioned way a read-only involved actor performs the act they
are entitled to without holding document-write rights.

**Open-from-inbox needs `_mail_post_access = 'read'`.** `mail.activity` has no
`ir.rule`; its read / search / `read_group` delegate to the source document's
`_mail_post_access`, which defaults (via `mail.thread`) to **`'write'`**. Since
an involved holder is read-only, once the awaiting-action surface becomes native
`mail.activity` ([ADR-0014](./0014-dissolve-inbox-tray-onto-native-activity-and-todo-bridge.md))
their sarabun to-dos would be filtered out of the Todo count and
**AccessError on open**. `sarabun.document` therefore sets
**`_mail_post_access = 'read'`** — a document-reader can read / count / open
their own activity. Accepted side effect: a document-reader may also **post
chatter** on the หนังสือ (the same access gate).

**Side-model reads are scoped to the parent หนังสือ.** `sarabun.step.recipient`
and `sarabun.routing.step.activity` previously carried **no** `ir.rule`, so any
Sarabun user could read the full recipient ledger / step↔activity links of
documents they cannot open. Each gets a rule scoping read to the parent
document's readability, and the over-broad write/unlink on the activity-link is
trimmed. (`sarabun.document.number` register-number leak is lower priority and
tracked separately.)

**"Own document" (เอกสารของตนเอง) = `sender_user_id`.** Not `create_uid`, not the
originator routing step. A เจ้าหน้าที่ธุรการ who ร่าง on behalf and presses send
is the **sender** (owns it); the downstream signer is an **actor** (reads via the
route). This matches the non-signing-drafter case (ADR-0008).

## Considered options

- **Follower-based read** (rejected) — Odoo `mail.thread` followers get **no**
  record read; adding a follower rule would silently widen access beyond the
  route. Involvement must come from the route (a recipient row), not ad-hoc
  following. If the Todo bridge auto-subscribes assignees as followers, that must
  not become a backdoor read path.
- **A dedicated read/auditor group** (rejected) — access is data-driven by the
  ledger; a group would duplicate that logic. User + Manager (+ the independent
  `group_sarabun_reset`) suffice; there is no "read-only auditor who is not a
  manager" persona in v1.
- **Let read lapse on a returned/reset หนังสือ** (rejected) — the cheap fix (just
  correct the wrong comment). Rejected because it violates the stated rule
  ("involved with *that* หนังสือ") and loses the audit trail for a prior signer.

## Consequences

- New stored `reached_user_ids` (M2m, active+archived recipients) + the actor
  rule rekeyed onto it; the wrong `security.xml` comment corrected. Add
  visibility tests for the **archive paths** (ตีกลับ / ดึงกลับ / Reset), which are
  currently untested — only reject (which does not archive) is covered.
- `_mail_post_access = 'read'` on `sarabun.document` widens who may post chatter
  to every document-reader.
- New `ir.rule`s on `sarabun.step.recipient` + `sarabun.routing.step.activity`
  (parent-document scoping) + trimmed link write/unlink.
- Route-action tests must run `with_user(actor)` (not admin), else the ACL path
  stays masked; add coverage for direct / delegate / return / recall and a
  plain-user send (which, post-ADR-0014, schedules activities for CC holders).
- Pre-production — the whole stack is on the feature branch, not in
  `origin/16.0`; no data migration.
