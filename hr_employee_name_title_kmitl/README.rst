===========================
HR Employee Name Title KMITL
===========================

This module composes the stored ``hr.employee.name`` as a work-track title
prefix glued to the employee's name parts, and locks it:

* **Academic staff** (``role = academic``) are prefixed with their Academic
  Standing Title (``ศาสตราจารย์``, ``ผู้ช่วยศาสตราจารย์`` ...).
* **Support staff** and employees with no track are prefixed with their personal
  honorific ``prefix_id`` (``นาย`` / ``นาง`` / ``นางสาว``). Academic staff with no
  academic title fall back to the honorific too.

The Thai name glues the prefix directly to the first name
(``ผู้ช่วยศาสตราจารย์สมชาย ใจดี``); the English ``name_secondary`` keeps a space
(``Assistant Professor Somchai Jaidee``).

``name`` becomes a derived, locked value: it is rebuilt from the name parts and
the title whenever they change, is never edited directly, and is never split back
into parts (the ``kmitl_hr_employee_full_name`` inverse is dropped). The
create-time split is kept so name-only creation paths still seed the parts. See
``docs/adr/0001-employee-name-derived-and-locked.md``.

Installing the module backfills every existing employee.
