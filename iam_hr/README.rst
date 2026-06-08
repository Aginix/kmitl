==============
IAM - HR Departments
==============

Bridge between the **iam** app and **hr**. Lets an IAM Manager answer two
questions without leaving the IAM app and without being an HR officer:

* **Which users belong to each department?** — *IAM ▸ Departments* lists every
  ``hr.department`` with a user count; opening one shows a **Users** smart
  button that drills into that department's backend users.
* **Which users are / aren't linked to an employee?** — the *Users* list gains
  a *Linked to Employee* column and two filters.

Access design (the non-obvious bit)
====================================

In core ``hr``, ``hr.department`` is readable by every internal user but
``hr.employee`` is **not** (it is restricted to ``hr.group_hr_user``; everyone
else reads ``hr.employee.public``). An IAM Manager is ``erp_manager`` /
``group_user`` and usually **not** HR staff.

So this module never reads ``hr.employee`` in the manager's own right and never
displays employee data. The user count, the department→users drill-down, and
the *Linked to Employee* search all derive their data through ``sudo()`` and
surface only an integer count and ``res.users`` records (which the manager can
already read). The IAM Manager is **not** granted ``hr.employee`` read access,
keeping employee PII off-limits (PDPA-friendly).

Nothing here adds a model, a stored column, or an ACL row — only computed
fields, two reused-model views, and one menu.
