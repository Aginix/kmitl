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

.. IMPORTANT::

   **This layout is reconstructed and still needs official spec confirmation.**

   The sample was decoded by byte offset; several constants and one width could
   not be derived unambiguously and are **pending official Krungsri CashLink
   Direct Credit upload spec confirmation**:

   * Meaning of the fixed constants ``712`` (header Code), ``A001`` (header Type
     Code) and ``001`` (Originator ID) — encoded as literals for now.
   * Exact **Amount** field width in the detail record. One sample line was
     masked to 10 digits; width was taken as **11** so the record sums to 128.
   * Whether the header **Originator Acct/Ref** field is the originator bank
     account number or a batch reference — currently derived from the first
     line's journal bank account number.

   Before production use, obtain the official *Krungsri CashLink ``PYR128_OUR``
   upload file layout* (byte-position table) + a fresh, non-masked sample from
   the bank and validate/adjust the CSV accordingly.
