# Secondary action links on a Todo via an extension hook

Some Todos point at workflows that the recipient does not finish inside the
source record's backend form — they finish them in a portal page (the
recipient may not even have backend access), and that portal URL carries a
**per-recipient** token. The primary "Open Source" action on a Todo
([ADR-0001](./0001-todos-are-native-mail-activity.md)) cannot reach those
pages: it points at the source record only, and its target is the same for
every viewer. We add an extension point `mail.activity._get_todo_action_links()`
that lets a bridge attach secondary URLs to a Todo, resolved **live per
viewer**, and the Discuss Todo list renders them as pills next to the primary
button. The first user is `purchase_work_acceptance_portal`: each committee
review Todo carries a "ตรวจรับใน Portal" link with that committee member's own
`committee_token`, and an "เอกสารสัญญา (PO)" link to the related purchase
order portal page.

## Why

- **Per-viewer tokens cannot be pre-rendered into a shared field.** A group
  Todo is one activity seen by many users; even a personal Todo's URL token
  may change (regenerated, rotated). Resolving at render time from
  `self.user_id` keeps the URL correct without storing it anywhere.
- **The hook composes with the existing extensibility shape.** The core
  already exposes `_my_todo_domain()`, `_todo_recipient_partners()` and
  `_todo_log_vals()` for bridges to override (ADR-0005). `_get_todo_action_links`
  is the same pattern: returns an additive list, super-friendly, no schema
  change to `mail.activity`.
- **The primary action stays load-bearing.** ADR-0001 keeps "Open Source" as
  *the* button on every Todo; action links sit alongside it, never replace it.

## Considered options

- **HTML `<a>` tags inside `mail.activity.note`** — zero schema, but the
  `note` field is user-editable rich text used for free-form context; mixing
  rendered actions into it muddies content, risks user edits stripping the
  link, and the same string surfaces in the chatter activity bubble where we
  don't want it. **Rejected.**
- **Typed `wa_portal_url` / `order_portal_url` fields on `mail.activity`** —
  explicit and indexable, but pollutes the core schema for one use case (and
  every future portal-driven workflow would want its own pair). **Rejected.**

## Consequences

- New method `mail.activity._get_todo_action_links()` returns
  `list[{"label": str, "url": str, "icon": str}]`. The core returns `[]`;
  bridges override and branch on `self.res_model`. Icons are fontawesome
  fragments (e.g. `"fa-external-link"`); the renderer prepends `fa`.
- `res.users.get_my_todos()` in `mail_activity_todo_discuss` calls the hook
  once per activity and includes the result in each Todo's payload as
  `action_links`. No extra query if the override does not search additional
  data.
- The Discuss Todo view template renders the pills inside the existing
  per-todo button, below the note preview, with `t-on-click.stop` on each
  link so the click does not bubble up to the parent's "open source"
  handler. Pills carry `target="_blank" rel="noopener noreferrer"` so the
  source-record form stays in place when the user follows a portal link.
- **Action links are not surfaced in the systray dropdown or the chatter
  activity bubble.** Both are compact summaries; pills only belong on the
  unified inbox page where the user is choosing what to act on.
- **Action links must remain additive.** A bridge that uses them to *replace*
  the source-record button would break ADR-0001's invariant; reviewers should
  reject overrides that return links intending to substitute for the primary
  action.
- Token-bearing URLs are not persisted to the database; rotating a token
  takes effect on the next render, no migration required.
