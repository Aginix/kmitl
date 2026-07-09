=====================
Base Assignment Todos
=====================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
    :alt: License: LGPL-3
.. |badge3| image:: https://img.shields.io/badge/language-th-red.png
    :target: README.th.rst
    :alt: อ่านภาษาไทย

|badge1| |badge2| |badge3|

Data-only bridge — surfaces the Assigned Officer notifications produced by
``base_assignment`` inside the unified Todo inbox shipped by
``mail_activity_todo``, so an assignee sees their pending work in one place
and can dismiss it with **Mark as Read**.

**Table of contents**

.. contents::
   :local:

Description
===========

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

Usage
=====

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

Known issues / Roadmap
======================

Deferred
--------

* **auto_install**. The manifest keeps ``"auto_install": False`` so
  operators explicitly opt in to Todo-inbox integration. A deployment
  that uses ``base_assignment`` without ``mail_activity_todo`` should not
  see this bridge silently installed. Revisit if every deployment ends
  up with the inbox by default.
* **Per-consumer todo_category override**. Every consumer's assignment
  notifications are tagged as ``acknowledgement`` — future work could
  let a consumer pick a different category (e.g. ``execution`` if the
  activity has an actual "done" step).

Migration
---------

This module was renamed from ``procurement_assignment_todo`` (it was
introduced before ``base_assignment`` existed). The pre-migration in
``migrations/16.0.2.0.0/`` rewrites the module name and ``ir.model.data``
rows in place; existing installations upgrade without an uninstall/reinstall
step. The rename shim will be kept indefinitely so late-upgrading databases
still work.

Credits
=======

Authors
-------

* Aginix Technologies
* KMITL (King Mongkut's Institute of Technology Ladkrabang)

Contributors
------------

* Aginix Technologies
* KMITL (King Mongkut's Institute of Technology Ladkrabang)

Referenced work
---------------

* ``base_assignment`` — the Assigned Officer mixin this bridge tags
* ``mail_activity_todo`` — the unified Todo inbox engine
