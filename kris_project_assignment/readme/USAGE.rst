Usage
=====

Any KRIS Project officer (``kris_project.group_kris_project_officer``)
may claim an *unassigned* project through the **Assign to me** button in
the banner. Reassigning to another officer, or unassigning an already
assigned project, is manager-only
(``kris_project.group_kris_project_manager``).

Filtering
---------

The project search view gains two new filters and a group-by:

* **Assigned to me** — projects where ``assigned_to = current user``.
* **Unassigned** — projects with no ``assigned_to``.
* **Group by Assigned Officer**.

Todo inbox
----------

Install ``base_assignment_todo`` alongside this module to surface
assignment notifications in the unified Todo inbox
(``mail_activity_todo``). No extra configuration is needed — the bridge
tags the assignment activity type on install.
