=============================
HR Employee Name Detail KMITL
=============================

This module shows extra employee information (academic standing title, work
email, department as *faculty / department*, and KID) on ``hr.employee``
many2one fields once an employee is selected.

Two presentations are provided.

Styled detail card (recommended)
=================================

The ``employee_detail_many2one`` widget renders the detail as an icon-prefixed
card below the field::

    <field name="employee_id" widget="employee_detail_many2one"/>

No context flag is needed: the widget reads the employee fields directly, so
empty values are skipped without shifting the layout.

Plain text extra lines
======================

For places where a custom widget is not desired, ``name_get`` can append the
same information as plain extra lines (the partner ``show_address`` pattern),
gated by the ``show_employee_detail`` context flag::

    <field name="employee_id"
           context="{'show_employee_detail': 1}"
           options="{'always_reload': True, 'highlight_first_line': True}"/>
