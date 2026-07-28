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
real KMITL sample file** and reproduces it **byte-for-byte** (both sample
detail records regenerate exactly: 123 and 125 bytes). Structure:

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
* Each detail is: a 54-byte prefix (running no. + record code + originator +
  account + amount + date, single-space delimited), a 24-byte **title** field,
  the variable-length **beneficiary name** (not padded), then a fixed 25-byte
  reserved field. Record lengths therefore vary with the name. The trailer is
  53 bytes.

.. NOTE::

   The layout is **validated byte-for-byte against the real KMITL sample**. The
   fixed codes ``7106`` (detail) / ``9100`` (trailer) and the originator code
   are taken from that file, so they are correct for KMITL's current setup.

   Remaining data/config dependencies (not layout issues):

   #. the **title** field value comes from ``partner.title.shortcut`` /
      ``name`` — make sure partners carry the Thai title (e.g. ``นส.``, ``นาง``)
      so it renders like the sample;
   #. if KMITL's KBANK company/originator or product changes, re-check the
      record codes and originator code against a fresh bank test upload.
