=====================================
Purchase Request Approval Work Center
=====================================

.. |badge_devstat| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
   :target: https://odoo-community.org/page/development-status
   :alt: Beta
.. |badge_license| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :alt: LGPL-3

|badge_devstat| |badge_license|

Adds พจ.1 (``purchase.request.approval``) to the **งานพัสดุ** work area of
`work_center`, next to the พ.1 that `purchase_request_work_center` routes.

A พจ.1 is routed **independently** of the พ.1 it came from, on its own
``requesting_department_id`` and while it is still draft. The two usually land
on the same work center, but a พจ.1 moved by hand stays where it was put.

Because ``purchase.request.approval`` is under ``tier.validation``, the work
center fields are whitelisted in the under- and after-validation exceptions:
the ADR allows the work center to be corrected in every state.

What it adds
============

* ``purchase.request.approval`` as a document model of the งานพัสดุ area.
* Three card counters: พจ.1 ร่าง, รออนุมัติ and ตีกลับ / รอแก้ พ.1.
* Work center field, column, search field, search panel, group-by and the
  *My Work Centers* / *No Work Center* filters on the พจ.1.

Credits
=======

Authors
-------

* Aginix Technologies
