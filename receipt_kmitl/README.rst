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
  Cash Account, a Deposit Bank Account, and a journal
* 6D analytic dimensions at the line level via ``analytic.mixin``, carried on
  every leg of the journal entry, including the treasury-remittance pair
* Per-fiscal-year sequence (``RC/{fiscal_year_be}/{####}``, e.g. ``RC/2569/0001``)
* Confirm assigns the number and allows printing — no journal entry yet
* ``kmitl.receipt.remittance`` (รายงานนำส่งคลัง) bundles confirmed receipts by
  department subtree; an approver reviews the batch and treasury posts it,
  generating one JE per receipt: a Dr Cash Account / Cr income pair for each
  line, plus a Dr Deposit Bank Account / Cr Cash Account pair remitting the
  full total to the treasury (นำเงินส่งคลัง):

  ===  ========================  =====  ====================
  #    Account                   Dr/Cr  Amount
  ===  ========================  =====  ====================
  1    Cash Account              Dr     line 1 amount
  1    Income account            Cr     line 1 amount
  ...  ...                       ...    ...
  N    Cash Account              Dr     line N amount
  N    Income account            Cr     line N amount
  —    Deposit Bank Account      Dr     receipt total
  —    Cash Account              Cr     receipt total
  ===  ========================  =====  ====================

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
   channel, each with a Journal, a Cash Account, a Deposit Bank Account
   (the two must differ), and a Payment Type (Cash / Cheque / Money Transfer /
   Other) — the type controls which box is ticked on the printed official
   receipt.
3. Review the revenue products. The module seeds one product per revenue
   account of the KMITL chart (see `Revenue product data`_) — archive the ones
   your office does not collect, or add your own with an Income Account set to
   an income-type account.

Revenue product data
====================

Receipt lines require a product whose income account is set **on the product
itself** (the picker's domain is ``[('property_account_income_id', '!=',
False)]``; the category fallback in ``_onchange_product_id`` only runs after
that). The module therefore ships the catalogue: one ``product.template`` per
revenue account of the KMITL chart — every code starting with ``4``, 316 in
total, including the header accounts — generated from
``account_kmitl/data/account.account.template.csv``.

Products are filed in a 22-node ``product.category`` tree mirroring the chart's
own levels, rooted at ``รายได้``:

::

  รายได้
  ├── รายได้จากการดำเนินงาน
  │   ├── รายได้จากรัฐบาล → 4111……4115
  │   └── รายได้จากแหล่งอื่น
  │       ├── รายได้อื่น → ค่าธรรมเนียมการศึกษา, ค่าธรรมเนียมอื่นๆ,
  │       │                งานบริการ, เงินผลประโยชน์, อื่นๆ
  │       ├── รายได้จากการรับบริจาค, รายได้ดอกเบี้ย, บัญชีพักรายได้,
  │       └── รายได้ระหว่างหน่วยงานภายใน
  ├── รายได้ที่ไม่เกิดจากการดำเนินการ
  └── รายได้แผ่นดิน → รายได้แผ่นดินอื่น

A product for a header account sits in its own category. ``default_code`` is
the 10-digit account code, ``list_price`` is ``0.00`` so the cashier types the
amount, ``sale_ok``/``purchase_ok`` are off to keep the 316 items out of the
sales and purchase pickers, and taxes are cleared (KMITL charges no VAT).

The data is ``noupdate="1"``: prices, names and archived state edited in the UI
survive an upgrade, and names are not re-synced when the chart changes. Adding
a record to the data file still reaches an installed database on ``-u`` (its
external id does not exist yet); changing a field on an existing record does
not — that needs a migration script.

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
