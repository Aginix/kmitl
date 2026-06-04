# Todos are native mail.activity records, not a custom aggregation table

The unified "สิ่งที่ต้องทำ" inbox surfaces pending work as real `mail.activity` records scheduled on each source document, and treats `mail.activity` as the **single source of truth**. We deliberately did *not* build a separate `kmitl.todo` table that every workflow populates. A Todo is created with `activity_schedule()` when a record enters a state that needs someone's action, and cleared with `activity_feedback()` when it leaves that state.

## Why

- 24 models already inherit `mail.activity.mixin`; the plumbing — deadline, overdue/today/planned state, reminders, the cross-model systray menu, and access control inherited from the source document — exists for free.
- The requested scope explicitly includes reminders / scheduled todos; `mail.activity.date_deadline` covers this natively with no extra model.
- Clearing is deterministic and drift-free: the activity's lifecycle is bound to the document's state transition, so the inbox can never disagree with the document.

## Considered options

- **Custom `kmitl.todo` aggregation table** — the shape of the existing `sarabun.inbox` and `work.acceptance.inbox` (per-user rows, `is_read`, `bus.bus` broadcast). Gives full UI control and native group rows, but reinvents deadlines / access / chatter / reminders and must be reconciled by every transition in ~15 models — a standing drift risk and a third bespoke inbox. **Rejected.**

## Consequences

- Every workflow that raises a Todo must schedule/clear an activity at its state transitions; the existing `purchase_request_approval` activity_schedule/feedback pair is the reference pattern (the only live one in the codebase today).
- v1 assigns each Todo to a **single `res.users`** — the determinable next actor (e.g. `procurement.plan.user_id`, `purchase.request.assigned_to`).
- **Dynamic group routing via `tier.validation` is out of scope for v1** — it resolves the next actor to a `res.groups` per record, which is the hard part; deliberately deferred. Group assignment (where any member may act) is instead handled by role-in-unit tags resolved live — see [ADR-0002](./0002-group-todos-route-by-role-in-unit-resolved-live.md).
- `procurement.plan` inherits only `mail.thread` today; the PoC adds `mail.activity.mixin` to it.
- The two existing custom inboxes (`sarabun.inbox`, `work.acceptance.inbox`) are left untouched for now; converging them onto activities is a later decision, not a v1 goal.
- PoC scope is the `procurement_plan → พ.1` slice only; the pattern is meant to be copied to other modules afterward.
- A done activity is unlinked by core, so there is no native completed-Todo history; completed Todos are snapshotted to a history table — see [ADR-0004](./0004-completed-todos-logged-to-history-table.md).
