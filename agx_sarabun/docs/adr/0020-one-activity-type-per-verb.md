# ADR-0020 — One activity type per verb

**Status:** Accepted
**Date:** 2026-10-23
**Modules:** `agx_sarabun` (core), `agx_sarabun_todo` (bridge)

**Supersedes in part [ADR-0014](./0014-dissolve-inbox-tray-onto-native-activity-and-todo-bridge.md)**
(the two activity types `_action` / `_ack` and the `gating OR show_signature`
discriminator). The tray removal and the Todo bridge in ADR-0014 still stand.

---

ADR-0014 raised every awaiting-action Todo with one of just two generic types, so the
holder of a ตรวจเอกสาร step saw "ต้องดำเนินการ" instead of what they are actually asked
to do. Since a verb's label *is* the human instruction (CONTEXT §Step verbs), **each
`sarabun.verb` now owns one `mail.activity.type`**, created and kept in sync by core.
The sync runs one way, verb → type: the name, in every language, with no prefix; the
active flag; and `res_model = sarabun.document`. A step raises its verb's type. Deleting
a verb deletes its type, or archives it while an activity still points at it. The
icon is set once when the type is created; after that it and the other Odoo settings
are edited on the type itself, which the verb form opens from a smart button.

**The Todo category moves onto the verb, with no forced rule.** `agx_sarabun_todo`
exposes `sarabun.verb.todo_category`, read from and written to the verb's type
(sudo, because a Sarabun Manager edits verbs but has no right on activity types).
Core no longer discriminates. The built-in verbs are seeded **once** with the category
the old discriminator gave them, so behaviour is unchanged after the upgrade. New
verbs start **blank**, and the admin decides. A blank Todo can be cleared by Mark as
Read and is not kept in "Completed by me".

## Considered options

- **Keep the two types, only rename them / show the verb in the summary** (rejected):
  the type name is what the Todo inbox shows as the "kind" of work. Two generic kinds
  cannot say "ตรวจเอกสาร".
- **Admin picks a (shareable) type per verb** (rejected): nothing would keep the name
  in sync, which is the whole point.
- **Keep a step-level override** (e.g. a `for_info` CC step is always
  acknowledgement) (rejected by the user): the category is whatever the verb says,
  freely configurable.

## Consequences

- Migration `agx_sarabun 16.0.7.2.0` creates a type for every verb. It re-points open
  sarabun activities from `_action` / `_ack` to their step's verb type using raw SQL,
  so each open Todo keeps its stored category, and then archives the two old types
  (`todo.log` history still names them). `agx_sarabun_todo 16.0.1.1.0` seeds the
  built-in categories.
- A change to a verb's category affects only Todos raised afterwards
  (`mail.activity.todo_category` follows only `activity_type_id`).
- A behaviour beyond execution / acknowledgement (e.g. a new kind of Todo) is the
  bridge's to add on the verb. Core stays Todo-agnostic.
