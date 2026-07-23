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
#. Select bank **KBANK**, fill the KBANK configuration (Originator Code) and the
   Effective Date, then *Confirm* and *Export Text File*.

File layout
===========

The layout in ``data/bank.export.format.line.csv`` was **reconstructed from a
real (but masked / trimmed) KMITL sample file**, not from a public
specification. Structure:

* **No header record.** The file is ``N`` detail records followed by a single
  trailer record.
* Fields within a record are **single-space delimited**; numeric fields are
  zero-padded and amounts are expressed in *satang* (baht × 100).
* Dates use ``YYMMDD``. Beneficiary account numbers are 10 digits.
* The file is encoded **cp874 (TIS-620)** with ``CRLF`` line endings and a
  trailing ``CRLF``.
* Both the detail and trailer records carry a **record code** (``7106`` on
  details, ``9100`` on the trailer) and the 7-digit **originator code**
  (``kbank_company_id``).
* The final beneficiary-name field is variable length (not padded), so record
  lengths vary; the fixed part of a detail record is 103 bytes and the trailer
  is 53 bytes.

.. IMPORTANT::

   The following items were inferred from the sample and are **pending official
   K-Cash Connect Plus spec confirmation** before production use:

   #. the meaning of the record codes ``7106`` (detail) and ``9100`` (trailer);
   #. the title/prefix field — its width (assumed 49) and source
      (``partner.title.shortcut`` / ``name``);
   #. the source of the 7-digit originator code (``kbank_company_id``);
   #. validation of a generated file against a bank test upload.
