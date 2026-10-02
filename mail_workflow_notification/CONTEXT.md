# Workflow Notifications

A lightweight notification feed that tells a document's creator when that document changes state — shown in a dedicated systray icon, separate from Todo tasks and from Discuss messages.

## Language

**Workflow Notification (การแจ้งเตือนเหตุการณ์)**:
A `mail.message` + `mail.notification` pair posted when a source document transitions state. It reaches the creator's systray icon and is dismissed per-user with "Mark all read". It carries no deadline, requires no action, and does not block any workflow step.
_Avoid_: calling this a Todo (that is a `mail.activity`, a task); treating it as a Discuss message (it does not appear in Discuss Inbox).

**Recipient**:
The `user_id` of the source document (its creator / responsible). Each bridge decides who to notify; the default is creator-only.
_Avoid_: followers, role-based routing — those belong to the Todo system.

**Systray Bell (Workflow)**:
The bell icon (fa-bell-o) added to the top navigation bar by this module. It is distinct from Odoo's native Discuss activities bell and from the Todo checkmark icon. Its badge shows the count of unread Workflow Notifications for the current user.
_Avoid_: confusing with the Discuss systray bell (that shows DM/@mention counts, not workflow events).

**`notification_type = 'workflow'`**:
The value added to `mail.notification.notification_type` by this module. Discuss Inbox filters for `notification_type = 'inbox'`, so workflow notifications are invisible to it. The Workflow systray filters exclusively for `notification_type = 'workflow'`.
_Avoid_: setting `notification_type = 'inbox'` when posting workflow events — that would pollute Discuss Inbox.

**Bridge**:
A small module (e.g., `purchase_request_notification`) that depends on this core and calls `_notify_workflow_event()` at specific state transitions on a source model. The core owns no knowledge of which models or transitions exist.
_Avoid_: adding source-model logic to the core module.

## Known limitations (accepted, revisit later)

- **Notification history is not shown** — only the 10 most recent *unread* events appear in the systray. Once marked read, an event is no longer surfaced. No history page exists in this version. If a user marks all read before opening the link, the event is gone from the UI (but the `mail.message` row remains in the DB).
- **UC3 Acknowledgement Todo for พ.1 `approved` coexists (duplicated temporarily)** — `purchase_request_todo` still posts an Acknowledgement Todo when พ.1 moves to `in_approval`. The bridge `purchase_request_notification` also posts a Workflow Notification for the same event. The user sees both until the Todo is retired in a future iteration. See [ADR-0001](docs/adr/0001-message-not-activity.md).
