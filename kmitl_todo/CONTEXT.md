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

**Approval Todo**:
A Todo cleared only by a real decision on the source record (approve / reject). Reading it does not clear it.
_Avoid_: marking an Approval Todo as "read"

**Execution Todo**:
A Todo asking its owner to do the next step of work on the source record (e.g. a เจ้าหน้าที่แผน filling the operating plan before a พ.1 can be created). Cleared when the step is done.

**Acknowledgement Todo**:
A Todo asking the user to read / sign / acknowledge a document. Cleared by the user marking it done ("Mark as Read").

**FYI Todo**:
A Todo that only informs (e.g. "your พ.1 changed state"); no required action. Cleared by the user marking it read.
_Avoid_: putting FYI and Approval Todos on the same footing

**Inbox (กล่องขาเข้า)**:
The unified page — every open Todo addressed to the current user (personal + role-in-unit), the one place to find incoming work. Modelled as an incoming queue, not an email client.
_Avoid_: dashboard (the inbox lists actionable items, not analytics)

**Mark as Read (อ่านแล้ว)**:
A *per-user* dismissal of an FYI or Acknowledgement Todo — removes it from *your* inbox only, leaving it for everyone else in the group. Recorded in `kmitl.todo.read`; never deletes the shared activity. Not offered on Approval/Execution Todos, which clear by acting on the source.
_Avoid_: treating Mark as Read as completing the work

**Claim (รับเรื่อง)**:
Optionally taking a group Todo as your own (sets the activity's `user_id`), so colleagues can see it is being handled.
_Avoid_: assign (the system never force-assigns a group Todo to one person)

**Completed Todo (history)**:
A finished Todo, snapshotted into `kmitl.todo.log` at completion — the underlying `mail.activity` is deleted when done, so the log is the only record. Shown in the app's "Completed" view with who completed it and when.
_Avoid_: archived activity (the activity is gone, not archived)

**Next actor**:
Who a Todo is for at a given state. Either a single `res.users` (personal Todo), or a *role-in-unit* group — everyone holding a Responsible Role who belongs to the source record's Operating Unit, resolved live (never a stored list). The whole inbox depends on this being determinable from the source record's data.
_Avoid_: approver (the next actor is not always an approver — see the four Todo types)

**Responsible Role (เจ้าหน้าที่…)**:
A `base_user_role` role naming *who does a job* (deliberately assigned, date-bounded) — e.g. เจ้าหน้าที่แผน. Distinct from a `res.groups`, which says only who *may* do it. Group Todos route on the Responsible Role so they reach the people accountable, not everyone with the rights.
_Avoid_: using a bare `res.groups` to mean "the people responsible"

**Operating Unit (OU, คณะ/หน่วยงาน)**:
The organizational unit a source record belongs to, and the second half of a role-in-unit assignment. The only org axis that carries a user mapping (`operating.unit.user_ids`); the analytic `departments` dimension does not.
_Avoid_: department (the analytic `departments` dimension is a different thing with no users)
