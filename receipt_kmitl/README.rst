==============
Receipt KMITL
==============

Cash receipting workflow for KMITL.

Overview
========

Brings receipt issuance, daily cash deposit, and central posting into Odoo.
Faculty/department accountants issue receipts (choosing the income account via
a product), print them, and submit a daily cash deposit to central treasury.
Central finance reviews the deposit and posts — creating one journal entry per
receipt.

Key features
============

* Custom ``receipt.kmitl`` document with multi-line entries
* Line uses ``product_id`` (standard ``product.product``) whose income account
  (``property_account_income_id``, a chart-of-accounts level-4 income account)
  drives the credit; free-text description like a normal invoice line
* Configurable payment methods (``receipt.kmitl.payment.method``) — each binds a
  debit GL account and a journal
* 6D analytic dimensions at the line level via ``analytic.distribution.mixin``
* Per-department × per-fiscal-year sequence (``RC/{dept_code}/{FY2}/{####}``)
* Confirm assigns the number and allows printing — no journal entry yet
* Cash deposit slip bundles confirmed receipts; central finance posts the batch,
  generating one JE per receipt (Dr payment-method account / Cr income)

Roles
=====

* ``Cashier`` — issues and confirms receipts, builds and submits cash deposits
  for assigned departments (set via ``Users → KMITL Receipt → Departments``)
* ``Central Finance`` — reviews and posts cash deposits across all departments
* ``Central Finance Manager`` — manages payment methods and settings

Configuration
=============

After install, the Central Finance Manager must:

1. Open ``Receipts → Configuration → Settings`` and set the Walk-in Partner
   (a default ``Walk-in Customer`` is provided).
2. Open ``Receipts → Configuration → Payment Methods`` and create one method per
   channel, each with a Journal and a Debit Account.
3. Create products (standard Odoo products) with an Income Account set to the
   appropriate level-4 chart-of-accounts income account.
4. For each Cashier, open ``Settings → Users → KMITL Receipt`` and select the
   departments they may operate on.

Usage
=====

1. Cashier creates a receipt, adds product lines, and clicks **Confirm**, then
   prints it.
2. End of day: Cashier creates a ``Cash Deposit``, clicks **Pull Pending
   Receipts**, then **Submit to Treasury**.
3. Central Finance opens the submitted deposit, reviews it, and clicks
   **Review & Post** — every receipt in the batch is posted with its own
   journal entry.

Receipts can be cancelled while still in draft/confirmed and not yet part of a
deposit; the receipt number is preserved. Posted receipts are reversed via a
standard Accounting credit note / reversal.
