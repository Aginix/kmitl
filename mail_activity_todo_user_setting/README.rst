Mail Activity Todo: Per-User Notification Scope
===============================================

Extends ``mail_activity_todo_role_unit`` (ADR-0002) with a per-user
**notification scope** (ADR-0007) so wide-access managers are not flooded
by group Todos from every Operating Unit.

Features
--------

* **OU-level filter**: each user picks which OUs trigger primary-inbox
  notifications (Preferences → *Todo Notifications*).  Empty = receive from
  every OU you can see (backward-compatible default).
* **Per-type overrides**: ``all_ous`` widens a type back to every view-scope
  OU; ``mute`` drops a type from the primary inbox entirely.
* **Systray badge** counts only the narrowed primary scope.
* **Personal Todos** always bypass the filter.

Usage
-----

Install this module in addition to ``mail_activity_todo_role_unit``.
Each user configures their scope via *Preferences → Todo Notifications* or
an admin can set it via *Settings → Users & Companies → Users → Todo
Notifications* tab.

ADR
---

* ADR-0007: ``mail_activity_todo/docs/adr/0007-split-notification-scope-from-view-scope.md``
