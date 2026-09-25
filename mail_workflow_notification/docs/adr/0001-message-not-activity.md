# Workflow event notifications use mail.message, not mail.activity

Workflow state-change FYI notifications (e.g. "your พ.1 has been reserved budget") are
implemented as `mail.message` + `mail.notification` rows with a custom
`notification_type = 'workflow'`, **not** as `mail.activity` Acknowledgement Todos.

## Why

`mail.activity` is semantically a task:

- It renders in the **Activity widget** on every form that inherits `mail.activity.mixin` —
  a row with a deadline, a coloured dot, and a "Done" button — visually communicating
  "something is waiting for you here". A state-change FYI has no deadline and requires no
  action; putting it in that widget misleads the user.
- It appears in the **Todo inbox** (`mail_activity_todo`) alongside Execution Todos (things
  the user *must* do). Users complained that Acknowledgement Todos in the same list felt
  like tasks they were being asked to complete.
- The existing `mail_activity_todo` Acknowledgement category (`UC3`) for พ.1 `approved`
  was the direct trigger for this design: users read it as "I have to do something about
  this" rather than "this is just an update for me".

`mail.message` with `notification_type = 'workflow'`:

- Does not appear in the **Activity widget** — no visual noise on the form.
- Does not appear in **Discuss Inbox** — Discuss filters `notification_type = 'inbox'`, so
  workflow rows are invisible to it and do not inflate the Discuss badge count.
- Carries only the fields a feed item needs: subject, body, timestamp, link to source record.
- `mail.notification.is_read` provides read-state natively — no extra table required.

## Considered option: extend mail_activity_todo with an Acknowledgement-only menu

Add a "Notifications" menu to `mail_activity_todo` that lists only
`todo_category = 'acknowledgement'` activities, while the Todo inbox filters them out.

Rejected because:

- The underlying records are still `mail.activity`, so the Activity widget on each form
  still shows them — the root UX complaint is not resolved.
- Splitting the same model into two menus by category adds conceptual overhead without
  changing what the user sees on the form.

## Consequences

- The existing **UC3 Acknowledgement Todo** for พ.1 `in_approval` (in `purchase_request_todo`)
  is **not retired in this iteration**. The user sees both a Todo and a Workflow Notification
  when พ.1 is approved — a deliberate temporary duplication accepted for risk-averse rollout.
  Revisit trigger: once users confirm the Workflow Notification feed meets their needs, remove
  the UC3 automation and activity type from `purchase_request_todo`.
- Bridge modules call `_notify_workflow_event(users, subject, body)` — a helper on
  `mail.thread` — at their state transitions. They never call `activity_schedule()` for
  FYI events.
- There is no completed-notification history page in v1. The 10 most recent *unread*
  events are shown in the systray popover; once marked read they leave the UI (the
  `mail.message` row is retained in the DB but not surfaced). A history view can be added
  as a non-breaking extension in a future iteration.
