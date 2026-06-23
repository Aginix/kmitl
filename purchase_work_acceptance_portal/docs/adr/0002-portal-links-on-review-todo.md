# Portal/PO links ride on the review Todo as per-viewer action pills

The committee review Todo ([ADR-0001](./0001-committee-notification-via-mail-activity-todo.md))
is a `mail.activity` whose primary "Open Source" button opens the WA backend
form ([mail_activity_todo ADR-0001](../../../mail_activity_todo/docs/adr/0001-todos-are-native-mail-activity.md)).
A committee member, though, finishes the review from a **portal** page whose
URL carries that member's own `committee_token` — and the PO portal page,
gated by the WA's `wa_token`, supplies the underlying contract. Neither URL
fits in the backend form button: targets differ per viewer, and the tokens
must resolve at render time, not at activity-create time. We surface both
URLs as a small list of "action link" pills attached to the Todo card in the
Discuss Todos view, computed live from `activity.user_id` each time
`get_my_todos()` runs.

The mechanism is a method `_get_todo_action_links()` on `mail.activity`,
defined by *this* module via `_inherit`, plus a `res.users.get_my_todos()`
override (also this module) that calls the method per Todo and attaches the
result as `action_links` in the payload. The Discuss template is extended
with `t-inherit-mode="extension"` to render the pills inside
`o_DiscussTodoView_text`, with `t-on-click.stop` so a pill click does not
fall through to the parent's "open source" handler. Pills carry
`target="_blank" rel="noopener noreferrer"`.

## Why

- **Per-viewer tokens cannot be pre-rendered into a shared field.** Even a
  personal Todo's URL is recipient-specific; storing it on the activity
  would have to be redone whenever a token rotates. Resolving from
  `self.user_id` at `get_my_todos` time keeps the URL correct with no
  persisted state.
- **`mail.activity.note` is the wrong place.** It is user-editable rich text
  meant for free-form context; embedding rendered links risks user edits
  stripping them and the same string surfaces in the chatter activity
  bubble, where we explicitly do not want portal pills.
- **The primary "Open Source" action stays load-bearing.** [mail_activity_todo
  ADR-0001](../../../mail_activity_todo/docs/adr/0001-todos-are-native-mail-activity.md)
  keeps that button as *the* way to reach the source — pills sit beside it,
  they do not replace it.

## Considered options

- **Push the hook into `mail_activity_todo` core so any consumer can attach
  links.** Cleaner extension point, but only this module needs it today and
  the base modules are shared with workflows that have no portal flavour.
  Adding an unused-by-anyone-else hook to a base module is speculative
  generalisation; we keep the method private to this module until a second
  consumer proves the pattern. If that happens, the method moves up.
  **Rejected for now.**
- **Typed `wa_portal_url` / `order_portal_url` fields on `mail.activity`.**
  Explicit and indexable, but pollutes core schema for one use case and
  cannot represent per-viewer tokens without per-user computed fields.
  **Rejected.**
- **HTML `<a>` tags inside `mail.activity.note`.** Zero schema, but mixes
  rendered actions with user content and the same string leaks into the
  chatter activity bubble. **Rejected.**

## Consequences

- The method `mail.activity._get_todo_action_links()` exists **only** in
  this module's `_inherit` of `mail.activity`. There is no `super()` call —
  the base does not define it. A second module that wants the same shape
  must either (a) coordinate with this module to lift the method into
  `mail_activity_todo`, (b) inherit `mail.activity` itself and add its own
  branch (the dispatcher will run both classes), or (c) declare an explicit
  dependency on `purchase_work_acceptance_portal` (only sensible if that
  module is genuinely upstream of the new consumer). The status quo costs
  nothing while only one consumer exists.
- `res.users.get_my_todos()` is overridden in this module to attach the
  `action_links` field to every Todo in the payload — a single
  `act._get_todo_action_links()` call per row, returning `[]` for any res
  model that is not `work.acceptance`.
- The Discuss view template is extended via `t-inherit-mode="extension"`
  pointing at `mail_activity_todo_discuss.DiscussTodoView`; the xpath
  inserts the pills inside `o_DiscussTodoView_text`. `t-on-click.stop`
  prevents the pill click from triggering `onTodoClick`.
- **Pills appear only in the Discuss Todos view.** Not in the systray
  dropdown, not in the chatter activity bubble — both are compact summaries
  where contextual portal links are noise.
- **The hook must remain additive.** An override that returns links
  intending to replace the source-record button would break the
  load-bearing primary action; reviewers should reject such overrides.
- Token-bearing URLs are not persisted; rotating a token takes effect on the
  next render, no migration needed.
