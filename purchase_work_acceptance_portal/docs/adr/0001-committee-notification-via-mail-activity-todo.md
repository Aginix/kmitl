# Committee review notification via mail_activity_todo, not a standalone inbox

The module previously shipped its own `work.acceptance.inbox` model with a dedicated systray dropdown, OWL component and `work_acceptance/inbox` bus channel — a per-(user, WA) notification row marked read/unread on its own state, separate from anything else a committee member had to act on. We delete that whole stack and let the unified [Todos](../../../mail_activity_todo/CONTEXT.md) inbox carry committee review notifications: one `mail.activity` per (committee user, WA), category Approval, with portal links surfaced as [Action Links](./0002-portal-links-on-review-todo.md). Committee members now see review work alongside every other Todo addressed to them — no second place to look.

## Why

- **One inbox, not two.** Before this change a committee member had to check the Discuss Todos panel *and* the WA systray for pending work. The WA systray was the only reason a committee member ever opened that dropdown — there was no other content there. Folding it into Todos is what "รวมศูนย์" requires.
- **The data model on the activity is the same shape as what the inbox was tracking.** `mail.activity` already carries `(res_model, res_id, user_id)`, lifecycle state, and a deletion path that logs to `todo.log` ([ADR-0004 of mail_activity_todo](../../../mail_activity_todo/docs/adr/0004-completed-todos-logged-to-history-table.md)) — i.e. the inbox row's `(user_id, work_acceptance_id, is_read)` plus a history table for free. The custom inbox was reinventing what we already had.
- **Approval is the right category.** Committee members make a real decision (`status` in `accept` / `not_accept` / `leave` / `other`); they should not be able to clear the Todo with "Mark as Read". The Approval semantics from `mail_activity_todo` ([ADR-0003](../../../mail_activity_todo/docs/adr/0003-per-user-read-state-in-side-table.md)) enforce that — the dismissal action isn't even offered.
- **Portal URLs still work because of Action Links.** The committee member's `committee_token` (and the WA's `wa_token` on PO links) is per-recipient and per-document; storing pre-rendered URLs in a side table was the inbox's reason to exist. The Action Links hook resolves URLs live against `activity.user_id` so the same need is met without a side table — see [ADR-0002](./0002-portal-links-on-review-todo.md).

## Considered options

- **Coexist (Todo + inbox running in parallel during transition)** — committee members would see the same WA in two places until the inbox is retired; the doubled-up notification is exactly what this change is supposed to remove. **Rejected.**
- **Keep the inbox model, retire only the systray** — half-measure: the data layer of the old design would survive without anyone reading it, accumulating rows on every `request_validation()`. **Rejected.**

## Consequences

- A committee member without `employee_id.user_id` set blocks `request_validation()` with a `UserError` — previously they were silently skipped (no notification at all). This is the intended tightening: a committee with no way to be notified is a configuration error, and the inbox flow was hiding it.
- No data migration. Any WA that was already in review when this lands will still have its `review_ids` in tier-validation but no Todo until someone re-calls `request_validation()` on it (the WA returns to draft and is re-submitted). For in-flight WAs the existing portal links continue to work — they were always token-driven and live on the WA, not the inbox.
- Removed in this change: model `work.acceptance.inbox`, asset bundle entries for `wa_systray.{esm.js,xml,scss}` and `wa_notification_handler.esm.js`, the `work_acceptance/inbox` bus channel, `res.users.{get_wa_inbox_count,get_wa_inbox_all,mark_all_wa_read}`, the inbox `ir.model.access` row and `ir.rule` — the whole stack goes together.
- Tier validation systray suppression stays (`res.users.review_user_count` filters `work.acceptance`) and `_notify_review_requested` is still a no-op: the tier-validation mail/systray would otherwise double-notify on top of the Todo.
- Mid-flight committee changes are handled automatically: adding a committee to a WA already `in_review` schedules a Todo for the new user; removing a committee unlinks their pending Todo (no `todo.log` entry, no decision was made); `button_draft` cancels every pending review Todo for the WA.
