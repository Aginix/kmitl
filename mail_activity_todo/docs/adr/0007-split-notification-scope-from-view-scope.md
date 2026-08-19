# Notification scope is a per-user subset of view scope, not the same thing

Group Todo routing keeps the [ADR-0002](./0002-group-todos-route-by-role-in-unit-resolved-live.md) `role ∩ OU` recipient rule for **access** (who *may* see the Todo), but the **inbox** now filters that further through a per-user **notification scope** — the subset of Operating Units the user has opted to be pinged for. Empty scope = fall back to the full view scope, so the pre-existing behaviour is the default and no configuration is required for regular users.

## Why

- `operating_unit/models/res_users.py` makes `res.users.operating_unit_ids` **expand to every OU** when a user holds `operating_unit.group_manager_operating_unit`. Oversight users at KMITL routinely hold this group together with one or more `*_operating_unit_access_all` bypasses so they can look across faculties.
- ADR-0002 uses `operating_unit_ids` verbatim for group Todo routing, which means the moment such a user also holds a working role (e.g. `เจ้าหน้าที่แผน` — kept as backup or because they occasionally cover), every group Todo in the institution lands in their inbox. The badge stops being actionable and the manager either mutes it mentally or churns through "not mine, not mine, not mine".
- The fix is to separate two axes the OCA layer conflates:
  - **View scope** — who may look. Wide by design; unchanged.
  - **Notification scope** — who should be pinged. User-owned, narrower by default for anyone with wide view scope.

## Design

A per-user `res.users.todo_notify_operating_unit_ids` M2M (subset of `operating_unit_ids`) plus an override table `res.users.todo.notify.rule` keyed on `mail.activity.type` with two modes:

- **`all_ous`** — widen this activity type back to the full view scope, overriding the OU subset (e.g. sarabun confirmations that a manager wants from anywhere).
- **`mute`** — drop this activity type from the primary inbox entirely (still surfaced under Oversight if in view scope).

The mail.activity domain splits into two:

- `_my_todo_domain()` — **view scope** (personal ∪ role ∩ view-scope-OU). Kept broad; record rules, chatter, and Oversight all ride it.
- `_my_primary_todo_domain()` — **notification scope**. Personal Todos always pass (bypass filter — user is the explicit target). Group Todos pass when the (activity type × OU) tuple survives the rules.

The inbox action targets `is_my_primary_todo=True`; the systray badge (`_my_todo_count_domain`) does too. A sibling "อื่นๆ ที่เกี่ยวข้อง" menu targets `is_my_todo=True AND is_my_primary_todo=False` — the Oversight page. The Oversight menu is gated by `group_all_ou_todo` / `group_manager_operating_unit` because without wide OU visibility a user's view scope equals their notification scope and Oversight is definitionally empty.

## Considered options

- **Route by `role ∩ assigned_operating_unit_ids`** (the raw, non-expanded field): would silently fix managers by ignoring the Manager OU expansion, but breaks the "manager can act on any OU" contract of `operating_unit` — they can *see* everywhere but suddenly cannot *be routed* anywhere they are not explicitly assigned. **Rejected** — that is a Preferences problem, not a routing one.
- **A `mute list` per activity type without an OU subset**: covers "don't ping me for planning Todos" but not "ping me for planning Todos, but only in my three responsibility OUs" — the second is the concrete manager ask that motivated the ADR. **Rejected** (insufficient).
- **A separate res.groups the manager can add themselves to for opt-in reduction**: coarse, admin-mediated, and does not compose with per-type overrides. **Rejected.**
- **Materialising an `is_primary` boolean on each activity at create/update time** (instead of computing live): fast to query, but every change to a user's scope would require a mass-recompute — the very "sync window" ADR-0002 was written to avoid. **Rejected** — resolved live like the base routing.

## Consequences

- Users who never touch Preferences see no change: empty scope → notification scope = view scope → `_my_primary_todo_domain()` matches everything `_my_todo_domain()` matches, and the Oversight menu is hidden by the group gate.
- The systray badge is now the "actionable-for-me" count, not the "visible-to-me" count. A wide-view user configuring a narrow notification scope sees their badge drop to the responsibility subset; the Oversight tab appears and holds what fell out.
- Personal Todos (`user_id = me`) bypass the filter entirely — assigning to a specific person is an explicit routing decision that outranks any preference (Q6.1).
- `_todo_recipient_partners` still resolves the *whole* group (role ∩ OU) — bus badges refresh for every member of the group, not only those whose notification scope includes the activity, so scope-filtering never silences group activity from someone who has widened it back with an `all_ous` rule.
- Rules live in `mail_activity_todo_role_unit` (the layer that owns the split), not the core `mail_activity_todo`, keeping the base layer usable without `operating_unit`.
- Two new `ir.rule` entries scope `res.users.todo.notify.rule` to `user_id = user.id` (self-service), with `base.group_erp_manager` seeing all for support.
- ADR-0002 remains the source of truth for **who can see** a group Todo — this ADR only refines **which subset ends up in the primary inbox**.
