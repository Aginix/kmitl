================
HR Employee Code
================

This module adds a unique **KMITL Code** to each employee.

The code is defined on ``hr.employee.base``, so it is shared by both
``hr.employee`` and the read-only ``hr.employee.public`` model — letting
non-HR users see an employee's code (e.g. in pickers and public views)
without access to the private employee record.

Features:

* Unique ``code`` field on the employee, shown on the form, list, search
  and kanban views.
* Change tracking on the code via the chatter.
* Exposed read-only on ``hr.employee.public``.
