``base_assignment`` schedules an activity of type
``base_assignment.mail_activity_assignment`` on the record every time an
officer is assigned to a document — as a notification for the new owner.
Out of the box this activity does not carry a ``todo_category``, so it
never surfaces in the unified Todo inbox provided by ``mail_activity_todo``:
the assignee only sees it as a native Odoo activity on the record's
chatter.

This bridge is data-only: it tags the assignment activity type with
``todo_category = "acknowledgement"`` on install/upgrade, so the same
notification also lands in the assignee's Todo inbox and can be cleared
with **Mark as Read**.

**Why Acknowledgement, not Execution or Approval?**

The assignment activity has no "done" state of its own — it is unlinked
when the officer is reassigned or unassigned, not when they finish any
particular step. Acknowledgement is the Todo category that expects the
assignee to dismiss the notification themselves (Mark as Read), which
matches this lifecycle. The retention cron sweeps read acknowledgements
after the configured threshold so the inbox stays clean.
