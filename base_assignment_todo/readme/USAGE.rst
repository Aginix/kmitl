This bridge has no user-facing UI and no code to write. Just install it.

Prerequisites
-------------

* ``base_assignment`` and at least one consumer that inherits
  ``assignment.mixin`` (e.g. ``procurement_assignment_kmitl`` or
  ``disbursement`` in this repository).
* ``mail_activity_todo`` — the unified Todo inbox engine.

After install
-------------

#. Open the **Todo Inbox** menu.
#. Every officer sees their pending assignment notifications listed
   alongside their other Todos (approvals, executions, FYIs).
#. Each assignment Todo can be dismissed with **Mark as Read** — that
   only removes it from *your* inbox; the underlying activity on the
   source record is untouched.
#. Reassigning or unassigning the record on the source document also
   clears the corresponding Todo automatically.

Uninstall
---------

Uninstalling this bridge simply removes the ``todo_category`` tag from
the assignment activity type. The activities themselves and the
``base_assignment`` module continue to work as before — you only lose
the Todo-inbox integration.
