=====================================
Thai Localization - Bank Payment Export KBANK
=====================================

Bank payment file export for **Kasikornbank (KBANK / KASITHBK)**, built on top
of ``l10n_th_bank_payment_export_format``.

This module adds ``KBANK`` as an option on ``bank.payment.export`` and ships a
fixed-width file layout (``KBANK K-Cash Connect Plus``) so that vendor payments
can be exported as a text file for upload to KBANK.

Usage
=====

#. Create vendor payments (Manual, bank journal) as usual.
#. From the Payments list, use *Create Bank Payment Export* (or create a
   ``bank.payment.export`` and *Get All Payments*).
#. Select bank **KBANK**, fill the KBANK configuration (Company ID, Sender Name,
   Service Type) and the Effective Date, then *Confirm* and *Export Text File*.

.. IMPORTANT::

   **The file layout in** ``data/bank.export.format.line.csv`` **is a DRAFT.**

   Kasikornbank does not publish the byte-level file specification openly. The
   shipped layout (Header ``HDCT``, 178 bytes / Detail ``D``, 487 bytes, amounts
   in satang, ``YYMMDD`` dates, 10-digit same-bank account numbers) was
   reconstructed from the public reverse-engineered library
   `MicroBenz/kbank-payroll.js <https://github.com/MicroBenz/kbank-payroll.js>`_
   and models KBANK's **same-bank K-Cash Connect Plus direct credit**.

   Before production use you **must**:

   #. obtain the official *K-Cash Connect Plus / K-Direct Credit File Format
      Specification* from KBANK (relationship manager / K-BIZ Contact Center),
   #. confirm the product used (same-bank direct credit vs interbank SMART — the
      latter needs additional bank/branch code fields, like the KTB module),
   #. validate a generated file against a real sample and a bank test upload,
      then adjust the layout CSV (and add config fields) accordingly.
