# mail_activity_todo — Roadmap & Backlog

Forward-looking backlog for the unified Todos inbox. Design rationale for what
already exists lives in [`docs/adr/`](./adr) (ADR-0001..0005) and the glossary
in [`../CONTEXT.md`](../CONTEXT.md). This file tracks what is **shipped** vs
**remaining**, with enough detail to pick up each item. Effort = S/M/L,
Value = high/med/low.

## Shipped

PoC + review hardening + quick wins are merged on
`16.0-add-unified-activity-todo-dashboard` (PR #821):

- Core: Todos = native `mail.activity`; role-in-unit group routing resolved live
  (ADR-0001/0002); per-user read state in `todo.read` (ADR-0003);
  completed-Todo history in `todo.log` (ADR-0004).
- UC1 procurement plan fill-Todo, UC2 PR activity tagging, UC3 requester FYI.
- L1 inbox (list/form + searchpanel + filters + decorations), native-style
  grouped systray (replaces the native Activities menu), Completed history view.
- Review fixes: `todo.log` record rule, server-side category gate, GC
  personal-only, FYI supersede, follower-free group scheduling, cancel-vs-done,
  `read_group` systray counts, indexes, explicit deps.
- Quick wins: **Claim/Release (รับเรื่อง)**, bulk Mark Read/Unread, Read filter.
- **Live systray** via `bus.bus` + role∩OU fan-out (closes ADR-0002 deferral).
- Test suite in `tests/`.
- **Modular split + rename** (ADR-0005): the single `kmitl_todo` addon became
  `mail_activity_todo` (core, `mail`-only) + `mail_activity_todo_role_unit`
  (group routing) + `procurement_plan_todo` + `purchase_request_todo` bridges,
  so the engine is reusable outside KMITL.

## Remaining — Strategic (M/L, high value)

### 1. `schedule_group_todo()` / `schedule_personal_todo()` mixin helper — M
- **Problem:** ADR-0001 says "copy the pattern," but `procurement_plan.py` and
  `purchase_request_approval.py` hand-roll routing (ref-by-xmlid, dedup guard,
  role∩OU-vs-personal branch, fallback user), re-introducing per-call-site drift.
- **Proposal:** add helpers to the existing `mail.activity.mixin` override
  (`models/mail_activity_mixin.py`) + a `clear_todo` wrapper; rewrite callers to
  ~3 lines. Do this **before** the tier bridge multiplies call sites.
- **Grounded in:** ADR-0001 (copy-the-pattern consequence).

### 2. `tier.validation` → Todo bridge (new addon `kmitl_todo_tier_validation`) — L
- **Problem:** `tier.validation` is the dominant approval mechanism
  (stock_request, work_acceptance, egp, accounting) but its pending reviews are
  invisible to the inbox.
- **Proposal:** override `request_validation` / `validate_tier` / `reject_tier`
  / `restart_validation` to schedule/clear Approval Todos from each review's
  reviewers. The next-actor ADR-0001 feared computing is already resolved by
  `tier.review` → ~5 workflows covered at once.
- **Grounded in:** ADR-0001 (the explicitly-deferred "hard part").

### 3. Converge `sarabun.inbox` + `work.acceptance.inbox` onto Todos — L
- **Problem:** three parallel inboxes / read tables / bells — the fragmentation
  this module set out to kill.
- **Proposal:** replace bespoke inbox rows with Acknowledgement-category Todos
  dismissed via `kmitl.todo.read`; retire legacy `bus.bus` broadcasts; start
  with work.acceptance as proof. Sequence **after** item 1 (the helper).
- **Grounded in:** ADR-0001 + README "Known limitations".

### 4. Personal / manual Todos (จดเอง) — M
- **Problem:** the inbox is a passive mirror; no way to jot a personal reminder.
- **Proposal:** "New personal Todo" action scheduling a `user_id=env.uid`
  activity (new `personal` category) on a neutral anchor, via a mini-wizard.
- **Grounded in:** ADR-0001 (reminders explicitly in scope).

### 5. Overdue escalation cron + re-notify — M
- **Problem:** Approval/Execution Todos (un-dismissable) can sit overdue forever;
  only the retention GC cron exists.
- **Proposal:** daily `_escalate_overdue_todos` re-notifying recipients on a
  cadence (reuse the bus fan-out helper), escalating to the OU manager after N
  days (config param), digest-grouped per recipient.

## Remaining — Later (medium value or dependent)

- **Snooze / Defer (เลื่อน)** — `snoozed_until` on `kmitl.todo.read`, excluded
  from `_my_todo_domain` until due. M. Extends ADR-0003.
- **Delegate / reassign a personal Todo** — wizard writing `user_id` + chatter
  note, personal Todos only. S.
- **Due-soon bucket + highlight** — search filter + systray `due_soon_count`
  (N via config). S.
- **Kanban + Calendar inbox views** — group by category/state; calendar on
  `date_deadline`. No model change. M.
- **Daily digest email** — per-user `_my_todo_count_domain` rendered to QWeb,
  opt-in. M.
- **Completion SLA metrics** — add a created-at snapshot to `kmitl.todo.log` +
  cycle-time / on-time pivot+graph. S.
- **Per-user inbox preferences** — default OU, hide-claimed, default group-by on
  `res.users`, fed into `_my_todo_domain`. M. Pairs with Claim.
- **Auditor group for the Completed log** — a dedicated group with a broader
  `ir.rule` so compliance can read all history (today everyone, incl. admins,
  sees only their own scope). S.

## Remaining — Tech debt / polish

- **Backfill `todo_category`** on already-shipped activity types and any future
  ones (the inbox now *hides* uncategorised, but tagging them surfaces them). S.
- **i18n** — export `i18n/kmitl_todo.pot` + `th.po` (Thai source via the agreed
  i18n route; ensure JS systray strings use `_t`). S.
- **Document the security model** in CONTEXT.md/ADR-0001: Todo visibility ==
  source-document read access; `is_my_todo` / inbox filters are presentation
  only, not an access boundary. S.
- **Timezone note** — inbox date filters key off the viewer tz (`context_today`)
  while the tree `state` decoration uses the assignee tz (UTC for group Todos);
  document or back both from one searchable mirror. S.
- **App icon** — add `static/description/icon.png` + `web_icon` on the root menu
  (cosmetic; does not affect systray group icons). S.
- **Retention index** — optional `create_date` partial index if the activity
  table ever grows (self-limiting today). low.
