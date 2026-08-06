# The inbox shows every activity assigned to the user; `todo_category` is metadata, not a gate

The unified Todo inbox (full page + systray) lists **every open `mail.activity` assigned to the current user** — built-in, OCA, hand-scheduled, and workflow-emitted alike — not only those carrying a `todo_category`. Membership is "assigned to me and still open"; `todo_category` no longer decides what *is* a Todo, it only refines behaviour (how a Todo clears, its urgency colour, its grouping). This is what lets the module hide Odoo's native activity bell without hiding work: nothing a user is responsible for can fall outside the one inbox.

## Considered options

- **Curated inbox — only activities with a `todo_category`** (the original discriminator): keeps the inbox to system-emitted workflow steps, but because the native activity bell is hidden ([`hide_native_activity_systray`](../../static/src/js/hide_native_activity_systray.esm.js)), any built-in / OCA / hand-scheduled activity then has *no* systray surface at all — invisible work. **Rejected.**
- **Keep the curated inbox and un-hide the native bell** (two bells side by side): restores visibility of uncategorised activities but re-introduces the "check each surface separately" fragmentation this module exists to kill. **Rejected.**

## Consequences

- The inbox action domain, the systray count (`res.users._my_todo_count_domain`), and the systray drill-down drop the `("todo_category", "!=", False)` filter.
- Two clear paths only: `execution` clears by acting on the source (the workflow calls `activity_feedback`); **everything else** — `acknowledgement` *and* uncategorised activities alike — clears by per-user **Mark as Read** (the read-clearable test is `todo_category != 'execution'`). There is deliberately **no native Mark-Done button** in the inbox (mis-click safety — [ADR-0003](./0003-per-user-read-state-in-side-table.md)).
- `todo_category` collapses to **two** behavioural values — `execution` (clears only at the source; absorbs the former "approval") and `acknowledgement` (dismissable by Mark as Read; absorbs the former "fyi") — since the four original values only ever expressed these two behaviours. It is set once on the `mail.activity.type` (auto-filling onto each activity of that type); the per-activity picker in the Schedule-Activity dialog is removed.
- Live-badge notification (`_todo_notify`) and completed-history logging (`_log_completed`, [ADR-0004](./0004-completed-todos-logged-to-history-table.md)) stay scoped to categorised workflow Todos — the inbox showing *everything* does **not** mean every activity completion is broadcast or audited.
- Uncategorised activities keep `todo_category = False` — the compute does **not** default them to `acknowledgement`. They behave *as if* Acknowledgement for clearing (Mark as Read), but staying technically uncategorised is exactly what keeps notification and history scoped to real workflow Todos. Defaulting the stored value would silently turn "log workflow Todos" into "log every activity" (the deferred 6B).
