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
