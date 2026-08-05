# Completed Todos are snapshotted to a history table

To let users review Todos they have finished — which the inbox cannot show, because core Odoo **deletes** a `mail.activity` when it is marked done — we snapshot every completed Todo into a dedicated `todo.log` table. `mail.activity._action_done` is overridden to record the activity (only those carrying a `todo_category`) just before core unlinks it. The log captures the routing (assignee or responsible role + operating unit), the source record, the category, the deadline, and *who* completed it *when*.

## Why

- Core's done-handling unlinks the activity and leaves only a per-record chatter message; there is no cross-record "Todos I finished" history. This was the open consequence noted in [ADR-0001](./0001-todos-are-native-mail-activity.md).
- A snapshot taken at completion preserves the role-in-unit routing (ADR-0002) that the chatter message does not carry, so history can be filtered by category / operating unit / completer.

## Considered options

- **Query the chatter messages** mail already logs on done (`mail.message` with `mail_activity_type_id`): no new model, but the author is whoever completed it (group Todos misattribute), it cannot express "was on my role's plate", and the messages are noisy. **Rejected.**
- **Keep done activities (don't unlink)**: fights core, which unlinks; every inbox/systray query would have to exclude done, and chaining/feedback assume deletion. **Rejected.**
- **Depend on OCA `mail_activity_done` and reuse its archived done-activities instead of `todo.log`**: `mail_activity_done` keeps the completed `mail.activity` alive (`active=False, done=True`) rather than unlinking, so in principle history could be read off the archived activities and `todo.log` dropped. **Rejected**, for the same reason as the chatter option: the archived activity records only `date_done` (when), not *who* completed it — for a group Todo the completer (`env.uid`) is not the assignee (`user_id`), so attribution is lost. `todo.log.completed_by` exists precisely to capture this. The dependency would also (a) pull in `mail_activity_done`'s invasive machinery — the `self._cr.execute` SQL string-replacement in `_read_progress_bar` / `_search_activity_state` and the system-wide `active=True` redefinition of `activity_ids` — for the sake of removing one small table, and (b) is unnecessary for resolving the inbox-visibility concern, since Odoo's default `active_test` already excludes `active=False` records from inbox/systray searches. The one genuine upside (a clean single-chain MRO for `_action_done`) does not outweigh the lost group attribution and the imported baggage. `mail_activity_todo` therefore depends only on `mail`, and the two modules should be treated as mutually exclusive — do not install `mail_activity_done` alongside it, since both override `_action_done` / `unlink` on `mail.activity`.

## Consequences

- New model `todo.log` (read-only to users; written via `sudo()` from the `_action_done` hook). The `mail_activity_todo` core defines the personal columns; the role-in-unit layer extends it with `responsible_role_id` / `operating_unit_id` via the `_todo_log_vals` hook.
- Only activities with a `todo_category` are logged, so uncategorised activities (a plain "Call", etc.) are not captured — even though [ADR-0006](./0006-inbox-shows-all-assigned-activities.md) now shows them in the inbox. This scoping is deliberate; expanding it to log *every* completed activity is deferred (see ROADMAP) and only becomes useful paired with an auditor group that can read history beyond its own scope.
- An activity cleared via `activity_feedback` on a *cancelling* transition (e.g. a plan put on hold) is logged like any completion; distinguishing "done" from "cancelled" is a later refinement, not v1.
- A "Completed" view + menu live under the Todos app alongside the inbox; the default filter is "Completed by me".
