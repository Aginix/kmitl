====================
IAM - HR Departments
====================

Bridge between the **iam** app and **hr**. Lets an IAM Manager answer three
questions without leaving the IAM app and without being an HR officer:

* **Which users belong to each department?** — *IAM ▸ HR Directory ▸
  Departments* lists every ``hr.department`` with a user count; opening one
  shows a **Users** smart button that drills into that department's backend
  users.
* **Which users are / aren't linked to an employee?** — the *Users* list gains
  a *Linked to Employee* column and two filters.
* **Which employees don't have a user yet?** — *IAM ▸ HR Directory ▸ Employees
  without User* lists the employees not linked to any ``res.users`` (default
  filter),
  so the manager can find and create the missing users. Toggle the filter to
  cross-check the employees that already have one.

Access design (the non-obvious bit)
====================================

In core ``hr``, ``hr.department`` is readable by every internal user but
``hr.employee`` is **not** (it is restricted to ``hr.group_hr_user``; everyone
else reads ``hr.employee.public``). An IAM Manager is ``erp_manager`` /
``group_user`` and usually **not** HR staff.

So this module never reads ``hr.employee`` in the manager's own right, and it is
**not** granted ``hr.employee`` read access, keeping employee PII off-limits
(PDPA-friendly). Instead:

* The department user count, the department→users drill-down, and the *Linked to
  Employee* search derive their data through ``sudo()`` and surface only an
  integer count and ``res.users`` records (which the manager can already read).
* The *Employees without User* list reads ``hr.employee.public`` — the SQL-view
  projection Odoo already exposes to every internal user — and shows only its
  public fields (name, department, job title, work email, linked user). No
  private employee field is ever touched.

Nothing here adds a model, a stored column, or an ACL row — only computed
helper fields, a handful of reused-model views, and two menus.
