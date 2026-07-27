===================================
Thai Localization - Bank Payment Export BAY
===================================

Bank payment file export for **Bank of Ayudhya / Krungsri (BAY / AYUDTHBK)**,
built on top of ``l10n_th_bank_payment_export_format``.

Adds ``BAY`` as an option on ``bank.payment.export`` and ships a fixed-width
file layout (``BAY CashLink Payroll (PYR128_OUR)``) for exporting vendor
payments.

Format type
===========

KMITL confirmed with the bank that the CashLink upload format is
**``PYR128_OUR``**:

* ``PYR`` – Payroll / direct-credit-to-account product.
* ``128`` – fixed record length of **128 bytes** (matches the sample and this
  layout).
* ``OUR`` – charges are borne by the originator (sender pays all fees).

The per-field byte layout of ``PYR128_OUR`` is still proprietary (not published
by Krungsri); the CSV layout was reconstructed from the sample file — see below.

File layout
===========

The layout in ``data/bank.export.format.line.csv`` was **reconstructed from a
real (but masked / trimmed) KMITL sample file** (``testBOA``), not from KTB.
Confirmed characteristics of that sample:

* Pure **fixed-width** records — there are **no field delimiters**.
* Every record is exactly **128 bytes** (consistent with ``PYR128``), encoded
  **cp874 / TIS-620**, line terminator **CRLF**, and the file ends with a
  trailing CRLF.
* The file is **1 HEADER record + N DETAIL records** — there is **no trailer**.
* Every record begins with the constant prefix ``507`` (Record ID) followed by
  ``001`` (Originator ID).
* Dates: the header **File Date** is ``DDMMYY`` and both header and detail carry
  a ``MMYY`` **Value Period**.
* Amounts are satang integers (value × 100), zero-padded right-justified.

.. NOTE::

   The layout is **validated byte-for-byte against the real KMITL sample**: the
   generated HEADER and the (unmasked) first DETAIL record regenerate the sample
   exactly, 128 bytes each. The detail **Amount** width of **11** and the fixed
   constants below are therefore confirmed for KMITL's current setup.

   The fixed constants ``712`` (header Code), ``A001`` (header Type Code) and
   ``001`` (Originator ID) are literals taken from KMITL's real file. They only
   need re-checking if KMITL's originating company/account with Krungsri
   changes; a fresh bank test upload should then confirm them.

   The header **Originator Acct/Ref** field is derived from the first line's
   journal bank account number (matches the sample).
