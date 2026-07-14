This add-on wires ``kris.project`` into the reusable ``assignment.mixin``
provided by ``base_assignment``. It adds an *Assigned Officer* concept
(``assigned_to``) — the KRIS Officer currently responsible for acting on
a project — alongside the existing ``user_id`` ("Responsible", the fixed
owner). Users interact with it through the standard
Assign to me / Assign… / Unassign banner injected above the project form.

When ``base_assignment_todo`` is also installed, assignment notifications
surface in the unified Todo inbox as an *Acknowledgement*-category
activity — the assignee dismisses it with **Mark as Read**.

The open To-Do is cleared automatically when the project reaches a closed
state (``done`` / ``cancel`` / ``terminated`` / ``conditional_close``), so
inboxes stay clean.
