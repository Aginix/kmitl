=================================
Purchase Contract Revision KMITL
=================================

Replaces the ``purchase_order_change`` wizard flow with first-class
``purchase.contract`` revision records for each ``purchase.order``.

**Design pillars:**

* **PO stays as the static hub** — number, vendor, department, budget commitment,
  fiscal year and all referencing documents (WA, disbursement, guarantee,
  ครุภัณฑ์) keep pointing to the ``purchase.order``.
* **Each amendment is a full snapshot** — header + lines + งวด + committees
  are copied into a ``purchase.contract`` record; historical revisions can be
  reprinted verbatim.
* **No in-system approval** — approval happens outside the system (paper /
  สารบรรณ). The record only enforces that at least one attachment
  (``approval_attachment_ids``) is present before ``action_apply`` will run.

**Lifecycle**

* Rev 0 auto-created on ``purchase.order.button_confirm``; state = ``applied``.
* Rev N (N ≥ 1) created from the "แก้ไขข้อมูลสัญญา" button on the PO form;
  state = ``draft`` → user edits + attaches the external approval doc →
  ``บันทึกการแก้ไข`` moves state to ``applied`` and syncs the snapshot back
  into ``purchase.order.line`` / ``purchase.invoice.plan``.
* Only one draft revision per PO is allowed at a time.

**Replaces:** the deleted ``purchase_order_change`` and
``purchase_order_change_committee`` modules. They no longer exist in the
codebase — this module is the sole revision path.

.. warning::

   **Deployment**: if a target database has ``purchase_order_change`` or
   ``purchase_order_change_committee`` **installed**, uninstall them from
   the Apps UI *before* deploying this module. Odoo cannot boot with an
   installed module whose code is missing on disk.
