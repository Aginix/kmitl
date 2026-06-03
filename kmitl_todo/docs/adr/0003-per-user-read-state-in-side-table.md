# Per-user read state lives in a side table, not on the activity

"Mark as Read" must dismiss a Todo **for the reader only**. A group Todo (a `role ∩ OU` activity with no `user_id`) is seen by many people on one shared `mail.activity`; marking it read on the activity itself would clear it for the whole group and confuse everyone else. So read/dismissal is tracked in a thin side model `kmitl.todo.read` (`activity_id × user_id × read_date`), and the inbox hides the activities the current user has read. The `mail.activity` stays the single source of truth for content, routing and deadline; the side table only records who has dismissed it.

## Why

- **The shared-record problem.** Group Todos are one activity seen by N users. Read state is inherently per-person, so it cannot live on the shared record.
- **Scope: FYI and Acknowledgement only.** These are read independently by each recipient. Approval and Execution Todos are **not** individually dismissable — they clear globally via `activity_feedback` when someone acts on the source (once approved / done, nobody else needs them), so they need no per-user state.
- **One kind of object in the inbox.** FYI Todos are kept as activities rather than Discuss `mail.message` notifications (which already carry per-user read state), so the unified page holds a single object type. The side table is the price of that uniformity.

## Considered options

- **`is_read` boolean on `mail.activity`**: global — one reader clears it for the whole group. **Rejected** (the exact confusion this ADR exists to prevent).
- **Route FYI through `mail.message` / `mail.notification`** (native per-user read + Discuss Inbox): splits the inbox across two object types and two surfaces. **Rejected** for the single-page goal.

## Consequences

- New model `kmitl.todo.read` — `activity_id` (`mail.activity`, `ondelete=cascade`), `user_id` (`res.users`), `read_date`; unique on (`activity_id`, `user_id`).
- The inbox domain (and the systray count) gain `AND activity NOT IN (activities the current user has read)`, on top of the [ADR-0002](./0002-group-todos-route-by-role-in-unit-resolved-live.md) `is_my_todo` domain.
- **"Mark as Read" creates a read row for `env.user`; it never deletes the activity.** Available on FYI / Acknowledgement Todos; Approval / Execution Todos show only "ไปต้นทาง" and clear by acting on the source.
- The activity itself is removed by its own lifecycle: Approval / Execution by feedback-on-action; FYI / Acknowledgement by an age-based retention cron that deletes a FYI/Acknowledgement Todo once it has been read **and** is older than a configurable threshold, **default 180 days**. (A per-record "supersede" rule — keep only the latest status FYI — is a later refinement, not v1.)
- Personal Todos (single `user_id`) use the same read row, so "Mark as Read" is one code path; since only that user sees them the per-user distinction is invisible but harmless.
