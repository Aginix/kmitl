=======================
KRIS Project Assignment
=======================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
    :alt: License: LGPL-3

|badge1| |badge2|

Assign a KRIS Officer as the *current handler* on a KRIS project — the
person responsible for acting on it right now — through the shared
Assign to me / Assign… / Unassign banner from ``base_assignment``.

**Table of contents**

.. contents::
   :local:

Description
===========

This add-on inherits ``assignment.mixin`` on ``kris.project`` and declares
the ``assigned_to`` field expected by the mixin. Officers self-claim
unassigned projects; managers reassign or unassign. The assignment
notification is a native ``mail.activity`` that also surfaces in the
unified Todo inbox when ``base_assignment_todo`` is installed.

Configuration
=============

None. Group membership drives who can claim (`kris_project.group_kris_project_officer`)
and who can reassign / unassign (`kris_project.group_kris_project_manager`).

Usage
=====

* **Assign to me** — visible on any unassigned project to a KRIS Officer.
* **Assign…** / **Unassign** — visible to a KRIS Project Manager.
* **Assigned to me** and **Unassigned** search filters plus a
  *Group by Assigned Officer* option.
* Any open assignment To-Do is cleared automatically when the project
  reaches a closed state (``done`` / ``cancel`` / ``terminated`` /
  ``conditional_close``); the ``assigned_to`` field itself is preserved
  as history.

Credits
=======

Authors
-------

* Aginix Technologies

License
=======

LGPL-3
