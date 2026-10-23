============================
Purchase Request Work Center
============================

.. |badge_devstat| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
   :target: https://odoo-community.org/page/development-status
   :alt: Beta
.. |badge_license| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :alt: LGPL-3

|badge_devstat| |badge_license|

Brings `work_center` to the **งานพัสดุ** work area: it seeds the area, routes
พ.1 (``purchase.request``) to a work center while the request is draft, and adds
the area's overview menu under Purchase.

See ``work_center/CONTEXT.md`` for the glossary and
``work_center/docs/adr/0001-*`` for the design.

What it adds
============

* The **งานพัสดุ** work area, covering ``purchase.request``.
* ``requesting_department_id`` (ส่วนงานผู้ขอ) as a routing field, so a rule such
  as "ส่วนงานผู้ขอ is under ภาควิชาไฟฟ้า" stamps the พ.1 while it is draft.
* Six card counters, one per open stage of the พ.1: ร่าง/ตีกลับ, รอตรวจสอบ,
  รอจองงบประมาณ, รออนุมัติ, รอ e-GP / พจ.1 and อนุมัติแล้ว. They are seeded with
  ``noupdate``, so an administrator's edits survive an upgrade.
* Work center field, column, search field, group-by and the *My Work Centers* /
  *No Work Center* filters on the พ.1.
* Purchase ▸ **Work Center**: the overview (filtered to this area) plus the
  area-scoped configuration, routing rules and counters.

Credits
=======

Authors
-------

* Aginix Technologies
