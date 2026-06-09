# Completed Todos are snapshotted to a history table

To let users review Todos they have finished — which the inbox cannot show, because core Odoo **deletes** a `mail.activity` when it is marked done — we snapshot every completed Todo into a dedicated `todo.log` table. `mail.activity._action_done` is overridden to record the activity (only those carrying a `todo_category`) just before core unlinks it. The log captures the routing (assignee or responsible role + operating unit), the source record, the category, the deadline, and *who* completed it *when*.

## Why

- Core's done-handling unlinks the activity and leaves only a per-record chatter message; there is no cross-record "Todos I finished" history. This was the open consequence noted in [ADR-0001](./0001-todos-are-native-mail-activity.md).
- A snapshot taken at completion preserves the role-in-unit routing (ADR-0002) that the chatter message does not carry, so history can be filtered by category / operating unit / completer.

## Considered options

- **Query the chatter messages** mail already logs on done (`mail.message` with `mail_activity_type_id`): no new model, but the author is whoever completed it (group Todos misattribute), it cannot express "was on my role's plate", and the messages are noisy. **Rejected.**
- **Keep done activities (don't unlink)**: fights core, which unlinks; every inbox/systray query would have to exclude done, and chaining/feedback assume deletion. **Rejected.**

## Consequences

- New model `todo.log` (read-only to users; written via `sudo()` from the `_action_done` hook). The `mail_activity_todo` core defines the personal columns; the role-in-unit layer extends it with `responsible_role_id` / `operating_unit_id` via the `_todo_log_vals` hook.
- Only activities with a `todo_category` are logged, so non-Todo activities (a plain "Call", etc.) are not captured.
- An activity cleared via `activity_feedback` on a *cancelling* transition (e.g. a plan put on hold) is logged like any completion; distinguishing "done" from "cancelled" is a later refinement, not v1.
- A "Completed" view + menu live under the Todos app alongside the inbox; the default filter is "Completed by me".
