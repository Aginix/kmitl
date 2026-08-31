==============
Receipt KMITL
==============

Cash receipting workflow for KMITL.

Overview
========

Brings receipt issuance, remittance to the treasury, and central posting into
Odoo. Department cashiers issue receipts (choosing the income account via a
product), print them, and remit their confirmed receipts to central treasury.
Treasury officers review the remittance and post — creating one journal entry
per receipt.

Key features
============

* Custom ``kmitl.receipt`` document with multi-line entries
* Line uses ``product_id`` (standard ``product.product``) whose income account
  (``property_account_income_id``, falling back to the product category's
  income account) drives the credit; free-text description like a normal
  invoice line
* Configurable payment methods (``kmitl.payment.method``) — each binds a
  debit GL account and a journal
* 6D analytic dimensions at the line level via ``analytic.mixin``
* Per-fiscal-year sequence (``RC/{fiscal_year_be}/{####}``, e.g. ``RC/2569/0001``)
* Confirm assigns the number and allows printing — no journal entry yet
* ``kmitl.receipt.remittance`` (รายงานนำส่งคลัง) bundles confirmed receipts by
  department subtree; an approver reviews the batch and treasury posts it,
  generating one JE per receipt (Dr payment-method account / Cr income)
* Removing a single receipt from a submitted remittance (via the standard
  widget on the receipts list) returns it to the pending pool for correction,
  without tearing down the whole document; rejecting the whole remittance is
  also available for the approver

Roles
=====

* ``Viewer`` — read-only access to receipts, remittances, payment methods
* ``User`` (เจ้าหน้าที่หน่วยงาน) — creates/confirms/cancels receipts; creates and
  submits remittances. Cannot approve or post accounting.
* ``Manager`` — configures payment methods and the walk-in partner.
  Implies Remittance Approver. Exception rules require the separate
  ``base_exception.group_exception_rule_manager`` group.
* ``Remittance Approver`` (ผู้อนุมัติรายงานนำส่ง) — an independent capability (not
  a tier) that may approve or reject a submitted remittance and mark it
  ``posted``, creating the accounting entries.

Row-level access (who sees which department's/OU's records) is provided by
the ``receipt_kmitl_operating_unit`` add-on, not by the base module.

Configuration
=============

After install, a Manager must:

1. Open ``Receipts → Configuration → ลูกค้า Walk-In`` and set the Walk-in
   Partner (a default ``Walk-in Customer`` is provided; config-parameter
   ``receipt_kmitl.walkin_partner_id`` overrides it).
2. Open ``Receipts → Configuration → Payment Methods`` and create one method per
   channel, each with a Journal, a Debit Account, and a Payment Type
   (Cash / Cheque / Money Transfer / Other) — the type controls which box is
   ticked on the printed official receipt.
3. Create products (standard Odoo products) with an Income Account set to the
   appropriate income-type account.

Usage
=====

1. A User creates a receipt, adds product lines, and clicks **Confirm**, then
   prints it.
2. A User creates a ``Receipt Remittance``, clicks **Pull Pending Receipts**,
   then **Submit to Treasury**. The remittance number and submission date are
   assigned at that point.
3. A Remittance Approver opens the submitted remittance and clicks
   **Approve**, then **Post Journal Entries** — every receipt in it is posted
   with its own journal entry.
4. To correct a mistake on one receipt, remove it from the ``receipt_ids`` list
   on the remittance form and use **แก้ไขใบเสร็จ** on the receipt to reopen it
   for editing; it keeps its number and can be remitted again later. To send
   the whole remittance back, the approver can **Reject** it with a reason.

Receipts can only be cancelled while in ``draft`` and not part of a
remittance; the receipt number is preserved. Posted receipts are reversed via
a standard Accounting credit note / reversal.
