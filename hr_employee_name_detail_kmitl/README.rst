=============================
HR Employee Name Detail KMITL
=============================

This module enriches ``hr.employee`` many2one fields so that, once an employee
is selected, the academic standing title, work email, department (faculty /
department) and KID are shown as extra lines below the input.

The behaviour mirrors the partner ``show_address`` pattern: it is gated by the
``show_employee_detail`` context flag, so the regular display name is unchanged
everywhere else.

Usage
=====

Add the context flag and ``always_reload`` option on any ``hr.employee``
many2one field where the detail should appear::

    <field name="employee_id"
           context="{'show_employee_detail': 1}"
           options="{'always_reload': True, 'highlight_first_line': True}"/>
