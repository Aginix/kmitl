======================================
Receipt KMITL Product Data
======================================

Revenue product master data for the KMITL receipt application.

Overview
========

``receipt_kmitl`` requires a product on every receipt line, and its picker only
shows products that carry an income account on the product itself
(``domain=[('property_account_income_id', '!=', False)]``). This module seeds
that catalogue so cashiers can issue receipts right after installation instead
of creating products by hand.

One ``product.template`` is created per revenue account of the KMITL chart of
accounts — every account whose code starts with ``4``, 316 in total, including
the header accounts (``4000000000`` รายได้, ``4100000000`` รายได้จากการ
ดำเนินงาน, …) and accounts that are not collected over the counter
(``4111……`` รายได้จากเงินงบประมาณ, ``4124……`` บัญชีพักรายได้).

Source data: ``account_kmitl/data/account.account.template.csv``.

Product fields
==============

* ``default_code`` — the 10-digit account code
* ``name`` — the account name, verbatim (Thai only; the chart has no English
  names)
* ``categ_id`` — a single ``รายได้`` category created by this module
* ``property_account_income_id`` — resolved by code at load time, so the
  account must already exist; ``account_kmitl`` is a dependency for that reason
* ``detailed_type`` — ``service`` (no ``stock`` dependency)
* ``list_price`` — ``0.0`` so the cashier types the amount; Odoo's default of
  ``1.00`` would otherwise land on the receipt line
* ``sale_ok`` / ``purchase_ok`` — both off, keeping 316 revenue items out of
  the purchase request and sales pickers
* taxes cleared — KMITL does not charge VAT

Known issues / Roadmap
======================

* The data is **not** ``noupdate``: upgrading the module re-syncs product names
  with the chart of accounts, overwriting names edited in the UI. Fields the
  records do not set (price, extra flags) are left untouched.
* To narrow what cashiers see, archive the unused products — no need to edit
  the data file.
