# Todos

A cross-cutting view of everything a user must act on or be aware of, gathered from every module into one place — the answer to "ต้องกดเข้าไปดูทีละแอปว่ามีงานของตนเองเข้ามาหรือยัง". A Todo is always backed by a native `mail.activity` on its source record; this context owns no business state, only the shared language, the consolidated page, and the rules for whom a Todo is assigned to.

## Language

**Todo (สิ่งที่ต้องทำ)**:
A single piece of pending work surfaced to a user — something awaiting their action or acknowledgement. The user-facing, ubiquitous term for the whole concept.
_Avoid_: task, action item, reminder (reminder is a Todo with a future deadline, not a separate thing)

**Activity** (the mechanism, not the concept):
The `mail.activity` record that *is* a Todo under the hood. Say "Todo" to users, "activity" when talking about the record. They are the same object seen from two sides.
_Avoid_: using "activity" and "Todo" interchangeably in user-facing text

**Source record (ต้นทาง)**:
The originating business document a Todo points back to (a procurement plan, a พ.1, a budget transfer …). Every Todo carries a button that opens its source record — the load-bearing feature of the whole context.
_Avoid_: parent, origin

There are exactly **two** behavioural categories (`todo_category`), splitting Todos by how they clear:

**Execution Todo**:
A Todo that clears **only by acting on the source record** — doing the next step of work, approving, or rejecting (e.g. a เจ้าหน้าที่แผน filling the operating plan before a พ.1 can be created; an approver approving/rejecting an entry). Reading it never clears it. Absorbs what was previously split into "Approval" and "Execution".
_Avoid_: marking an Execution Todo as "read"; treating approval as its own category

**Acknowledgement Todo**:
A Todo cleared by the user **marking it read** ("Mark as Read" — per-person and reversible), whether it asks the user to read/sign a document or only informs them (e.g. "your พ.1 changed state"). Absorbs what was previously split into "Acknowledgement" and "FYI".
_Avoid_: FYI (folded into Acknowledgement); treating Mark as Read as completing the work

**Inbox (กล่องขาเข้า)**:
The unified page — every open activity assigned to the current user (and, with the role-in-unit layer, to their role-in-unit groups), gathered from every module into one place. Membership is "assigned to me and still open", **not** "carries a category": built-in, OCA, and hand-scheduled activities all belong here too. The category only refines how a Todo is flagged and cleared, it does not decide whether it is in the inbox. The one place to find incoming work, modelled as an incoming queue, not an email client. With ADR-0007 the Inbox surfaces the *primary* Todos only (personal + group Todos in notification scope); anything the user could see but is not being notified for lives in the sibling **Oversight** page.
_Avoid_: dashboard (the inbox lists actionable items, not analytics); conflating Inbox with Oversight (the badge follows Inbox alone)

**Mark as Read (อ่านแล้ว)**:
A *per-user* dismissal of any Todo that is **not** an Execution Todo — an Acknowledgement Todo *or* an uncategorised built-in / hand-scheduled activity — removes it from *your* inbox only, leaving it for everyone else in the group. Recorded in `todo.read`; never deletes the shared activity. It is the single user-driven clear gesture (there is no "Mark Done" button); only Execution Todos are excluded, because they clear by acting on the source.
_Avoid_: treating Mark as Read as completing the work

**Claim (รับเรื่อง)**:
Optionally taking a group Todo as your own (sets the activity's `user_id`), so colleagues can see it is being handled.
_Avoid_: assign (the system never force-assigns a group Todo to one person)

**Completed Todo (history)**:
A finished Todo, snapshotted into `todo.log` at completion — the underlying `mail.activity` is deleted when done, so the log is the only record. Shown in the app's "Completed" view with who completed it and when.
_Avoid_: archived activity (the activity is gone, not archived)

**Next actor**:
Who a Todo is for at a given state. Either a single `res.users` (personal Todo), or a *role-in-unit* group — everyone holding a Responsible Role who belongs to the source record's Operating Unit, resolved live (never a stored list). The whole inbox depends on this being determinable from the source record's data.
_Avoid_: approver (the next actor is not always an approver — see the two Todo types)

**Responsible Role (เจ้าหน้าที่…)**:
A `base_user_role` role naming *who does a job* (deliberately assigned, date-bounded) — e.g. เจ้าหน้าที่แผน. Distinct from a `res.groups`, which says only who *may* do it. Group Todos route on the Responsible Role so they reach the people accountable, not everyone with the rights.
_Avoid_: using a bare `res.groups` to mean "the people responsible"

**Operating Unit (OU, คณะ/หน่วยงาน)**:
The organizational unit a source record belongs to, and the second half of a role-in-unit assignment. The only org axis that carries a user mapping (`operating.unit.user_ids`); the analytic `departments` dimension does not.
_Avoid_: department (the analytic `departments` dimension is a different thing with no users)

**View scope**:
Every OU the user *can see data for*, exposed as `res.users.operating_unit_ids`. Wide by design for oversight roles — the OCA `operating_unit` module expands it to *all* OUs for anyone holding `group_manager_operating_unit`, and `*_operating_unit_access_all` add-ons layer further per-model bypasses on top. This is the "who is allowed to look" scope — separate from **notification scope**.
_Avoid_: conflating view scope with who receives the Todo (that is notification scope)

**Notification scope**:
The subset of view scope the user has opted to be *pinged* for on group Todos, stored on `res.users.todo_notify_operating_unit_ids`. Empty = fall back to the full view scope (backward-compatible default). Configured per user in Preferences; keeps a wide-access manager's inbox from mirroring every OU's chatter while leaving their view scope untouched (ADR-0007).
_Avoid_: mixing this with view scope — a filter here never removes access, only badges/pings

**Todo Notification Rule**:
A per-user override on a specific `mail.activity.type` (`res.users.todo.notify.rule`). Two modes: `all_ous` widens back to every OU in view scope regardless of notification scope (e.g. a manager who wants sarabun confirmations from anywhere), `mute` drops the type from the primary inbox entirely (still surfaced under Oversight if the user could see it). No rule for a type = follow notification scope.
_Avoid_: treating a rule as a routing decision — routing still runs role ∩ view scope; rules only reshape the primary/oversight split

**Oversight Todo**:
A group Todo the user can *see* (inside view scope) but that falls *outside* their notification scope — a manager glancing at team activity, not their own next action. Surfaced under a separate "อื่นๆ ที่เกี่ยวข้อง" tab (visible only when there is one to show); does not count toward the systray badge (ADR-0007).
_Avoid_: acting on an Oversight Todo as if it were assigned to you (Claim converts it to personal first)
