=====================================
Mail Activity Todo — Execution Guard
=====================================

An **Execution** Todo clears only when the user performs the coded action on
the source document. Pressing *Mark Done* / *Cancel* in the chatter deleted the
reminder while the real work stayed undone, so this add-on:

* hides *Mark Done*, *Upload Document* and *Cancel* on Execution activities in
  the chatter, the list/kanban activity popover and the activity form, showing
  a hint to complete the task on the document instead;
* refuses the same calls server-side when the web client invokes them directly
  on ``mail.activity``. Business code that closes Todos inside its own action
  on the source model is unaffected.

Administrators (``base.group_system``) can still close Execution Todos from the
chatter to clear stuck ones.

Install explicitly: ``-i mail_activity_todo_execution_guard``.
