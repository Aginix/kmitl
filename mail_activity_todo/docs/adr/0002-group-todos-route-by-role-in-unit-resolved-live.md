# Group Todos route by role-in-unit, resolved live (not materialized teams)

When a Todo's next actor is a group rather than one person, the `mail.activity` is tagged with a `responsible_role_id` (a `base_user_role` role) and an `operating_unit_id`, and `user_id` is left empty. The recipients — holders of that role who belong to that operating unit — are **computed live** wherever Todos are listed, never stored. We rejected materializing one `mail.activity.team` per unit with synced membership. This resolves the open question left by [ADR-0001](./0001-todos-are-native-mail-activity.md).

The shared domain (used by the unified page, the custom systray count, and the form chatter) is:

```python
['|',
   ('user_id', '=', uid),                                      # personal Todos
   '&', ('responsible_role_id', 'in', user.sudo().role_ids.ids),   # I hold the role
        ('operating_unit_id',   'in', user.operating_unit_ids.ids)]  # ...in a unit I belong to
```

## Why

- **Never stale.** Recipients are exactly the current `role ∩ OU` at read time; a role-line or OU-membership change takes effect immediately, with no sync window.
- **No standing infrastructure.** No per-unit team records and no cron/hooks to reconcile membership — both inputs (role assignment, OU membership) are already maintained for other reasons.
- **Responsible ≠ permitted.** `base_user_role` roles are *deliberately assigned* ("this person does the plan work"), whereas a `res.groups` is often held incidentally or by inheritance. Routing on the role keeps group Todos off the screens of people who merely *could* do the work — the anti-clutter requirement that motivated this.
- **OU is the only org axis with a user mapping.** `operating.unit.user_ids` exists and is used system-wide (`*_operating_unit` modules); the analytic `departments` dimension carries no users.

## Considered options

- **Materialized per-OU `mail.activity.team`** (via `mail_activity_team`), `member_ids` synced from `role ∩ OU`: gives the native "Team" systray tab for free, but freezes the recipient list — requiring a recompute on every role-line or OU-membership change and leaving a stale window in between, plus N team records to manage. **Rejected** (the drift is exactly the "รก/stale" failure the design set out to avoid).
- **Plain `res.groups` instead of a role**: membership is often incidental/inherited, so Todos would reach people who hold the rights but not the responsibility. **Rejected.**

## Consequences

- `mail.activity` gains nullable `responsible_role_id` (`res.users.role`) and `operating_unit_id` (`operating.unit`); `user_id` is relaxed to **not required**. These tags and the relaxation live in the `mail_activity_todo_role_unit` layer (ADR-0005), not the core, and we replicate the one-line relaxation there rather than depend on `mail_activity_team`, to avoid pulling in its unused team model and systray patch.
- `res.users.role_ids` is `groups="base.group_erp_manager"`, so a normal user cannot read their own roles — the domain must resolve "my roles" through `sudo()`. Expired role lines drop out of `role_ids` automatically (date-bounded), so temporary responsibility just works.
- The native systray "Activities" menu will not show group Todos (no `user_id`); a small custom systray item re-runs the shared domain, following the existing `sarabun.inbox` / `work.acceptance.inbox` systray precedent.
- Native activity email-on-create targets `user_id`, so it does not fire for group Todos; group notification, if wanted later, is a separate explicit step — v1 relies on the inbox + systray.
- An optional **"รับเรื่อง" (Claim)** action sets `user_id = me`, converting a group Todo into a personal one so colleagues see it is taken.
- Single-user Todos (e.g. `purchase.request.assigned_to`, the requester FYI) set `user_id` and leave the tags empty — one model, two modes; the same domain surfaces both.

## Update (2026-08-09): OU is the source record's OU, cached and kept live

`operating_unit_id` on the activity is **not** a value the caller tags by hand — it is a denormalised copy of the *source record's* `operating_unit_id`. Recipients (`role ∩ OU`) are still resolved live; the OU itself is the piece that gets cached onto the activity so routing, history (`todo.log`), and the oversight group-by/search-panel stay **pure SQL** (a polymorphic `res_model`/`res_id` join to the source's OU cannot be expressed in a `mail.activity` domain).

- **Filled on every create path.** `mail.activity.create` (role-in-unit layer) copies the source record's OU onto the activity when the caller does not pin one — covering the chatter "Schedule Activity" dialog, the inbox form, and `activity_schedule`. Callers pass only the role. An explicitly-passed OU still wins.
- **Kept live on source OU change.** `mail.activity.mixin.write` propagates a source record's OU change onto its open activities (`sudo`, since the mover need not own group activities). Because that goes through `mail.activity.write`, the existing `_todo_notify` fires for the old **and** new OU members — visibility re-resolves and badges refresh immediately, not only on reload.
- **Consequence — the OU is a snapshot between changes.** It is only as live as the propagation hook: it tracks source OU changes made via ORM `write`, and history logs the OU at completion time. This is intentional (fast, queryable) and matches "recipients live, tag cached".
