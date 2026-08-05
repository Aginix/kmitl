# Dissolve the e-Saraban inbox tray onto native `mail.activity` + the `agx_sarabun_todo` bridge

e-Saraban shipped its **own** systray (the Action tray, `agx_sarabun.SarabunSystray`)
with its own `sarabun_inbox/updated` bus and a count computed from the routing
model (`get_my_sarabun_inbox`) — a surface parallel to the cross-cutting Todos
inbox ([`mail_activity_todo`](../../../mail_activity_todo/CONTEXT.md)). When both
are installed the same gating step shows in **two** bells (Todo seq 95, Sarabun
seq 90) and is double-counted — exactly the fragmentation
`mail_activity_todo` exists to kill (its ADR-0006), and the convergence its
ROADMAP already lists as item #3. Since KMITL develops both modules and deploys
them together, we **remove the sarabun tray** and make e-Saraban surface its
awaiting-action work purely as native `mail.activity`, with a new
`agx_sarabun_todo` bridge routing it into the one Todo inbox.

## Decision

**Delete the sarabun Action tray.** Remove `sarabun_systray.esm.js` / `.xml` /
`.scss`, the `sarabunNotificationHandler` service, `get_my_sarabun_inbox`, the
`sarabun_inbox/updated` bus + its `_notify_inbox` emitters, and the `"bus"`
manifest dep if nothing else needs it. **Keep** the กล่องหนังสือเข้า (Incoming
box) backend menu (`menu_sarabun_inbox` / `action_sarabun_document_inbox`) — the
persistent by-reach mailbox is a different surface and survives untouched; only
the transient bell is removed.

**Base e-Saraban surfaces awaiting-action work as native `mail.activity`** (the
native Odoo activity bell). Every **active** step now schedules an activity for
each snapshot holder — **gating AND non-gating** (รับทราบ / สำเนาเรียน /
`verb_acknowledge_sign`) alike; the old gating-only filter is dropped, so no
awaiting-action work is invisible once the tray is gone. Core defines **two
activity types** (`_action`, `_ack`) and `_schedule_activities` picks by
discriminator: **execution iff (`gating` OR `show_signature`)** — a step that
gates or physically signs the letter is execution; a pure read-only รับทราบ is
acknowledgement. `_clear_activities` stays in core (`agx_sarabun_reset` depends on
it).

**The `agx_sarabun_todo` bridge** (depends `agx_sarabun` + `mail_activity_todo`
core — no `role_unit`, since sarabun activities are **personal**, one per holder)
tags the two activity types with `todo_category`: `_action → execution`,
`_ack → acknowledgement`. So gating/signing to-dos clear **only by acting at the
หนังสือ**, while a pure รับทราบ clears by **Mark as Read** (the per-person
`read_date` / เปิดอ่านแล้ว keeps the opened-audit; the activity self-clears when
the หนังสือ completes). The bridge adds **no `ir.rule`** on `mail.activity` — it
relies on native activity access plus `_mail_post_access = 'read'`
([ADR-0013](./0013-e-saraban-access-control-model.md)). `mail_activity_todo`
already hides the native activity bell (`hide_native_activity_systray`), so there
is never a double bell. `todo_category` is a `mail_activity_todo` field, so only
the bridge (never core, which stays Todo-agnostic) may set it.

**Notification sound is a two-layer opt-in.** A generic add-on
`mail_activity_todo_sound` (depends `mail_activity_todo`) plays a sound on a
**new** Todo and gives each user a per-person on/off toggle in Preferences. The
play decision is made **server-side** via a `_todo_notify(sound=…)` hook — the
current bus payload is only `{refresh: True}` and cannot distinguish new-work
from a clear or carry the source model — so `create` notifies with sound intent,
`write`/`unlink` stay silent, and the client simply obeys `payload.sound`. The
`agx_sarabun_todo` bridge refines this into **per-source** control: a **separate**
per-user toggle for sarabun vs non-sarabun, routed by `res_model`
(`play = sarabun_toggle if res_model == 'sarabun.document' else general_toggle`),
so a user drowning in general Todos can silence those yet still be pinged for a
หนังสือ. This refinement is active only where `mail_activity_todo_sound` is
installed — `agx_sarabun_todo` **soft-depends** on it (the sound module carries the
`_todo_notify(sound=…)` hook + the base toggle the refinement extends); the activity
bridge still installs and tags `todo_category` without it. MVP is sound only; a
browser Notification and a distinct sarabun sound
are enhancements.

## Considered options

- **Keep both systrays / unify styling only** (rejected) — leaves the double
  count and two bells; violates `mail_activity_todo` ADR-0006's single-inbox
  mandate.
- **Keep the sarabun tray, exclude sarabun activities from the Todo inbox**
  (rejected) — contradicts ADR-0006 ("no invisible work / every assigned activity
  is in the inbox").
- **Make the bridge own activity scheduling** (rejected) — base e-Saraban must
  stand on native `mail.activity` without `mail_activity_todo`; scheduling +
  clearing stay in core, only `todo_category` tagging is the bridge's job.
- **Discriminate the category by `gating` alone** (rejected) — `verb_acknowledge_sign`
  is non-gating yet signs the letter; it must be execution (a signature can't be
  Mark-as-Read'd away). The discriminator is `gating OR show_signature`.
- **Put the sound in `mail_activity_todo` core for all apps** (rejected) — the
  inbox is high-volume; a global ding is noise. Sound is an opt-in add-on with
  per-source control.

## Consequences

- Delete the tray assets + `get_my_sarabun_inbox`; port/remove
  `tests/test_p4_access_notify.py::test_inbox_lists_my_active_step_documents` and
  `::test_acknowledge_step_schedules_no_activity` (รับทราบ now **does** raise an
  activity).
- Core grows a second activity type + the discriminator; the bridge adds the
  `todo_category` data + the per-source sound refinement (kept in
  `agx_sarabun_todo` per the layering choice — split to `agx_sarabun_todo_sound`
  later only if the activity bridge must install without the sound feature).
- New generic module `mail_activity_todo_sound` that **extends the existing**
  `mail.activity._todo_notify` with a `sound=` argument (create → sound, other
  transitions silent) + a `res.users` sound preference (SELF_WRITEABLE, in
  Preferences).
- `mail_activity_todo` ROADMAP #3 (converge `sarabun.inbox`) — the e-Saraban half
  is decided here; its wording predates the rebuilt engine (`sarabun.routing.step`,
  not `sarabun.inbox`).
- Pre-production — feature branch only; no migration; no version bump for the
  pre-deployment Todo stack.
