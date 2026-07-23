===================================
Thai Localization - Bank Payment Export BAY
===================================

Bank payment file export for **Bank of Ayudhya / Krungsri (BAY / AYUDTHBK)**,
built on top of ``l10n_th_bank_payment_export_format``.

Adds ``BAY`` as an option on ``bank.payment.export`` and ships a fixed-width
file layout (``BAY Direct Credit``) for exporting vendor payments.

File layout
===========

The layout in ``data/bank.export.format.line.csv`` was **reconstructed from a
real (but masked / trimmed) KMITL sample file** (``testBOA``), not from KTB.
Confirmed characteristics of that sample:

* Pure **fixed-width** records — there are **no field delimiters**.
* Every record is exactly **128 bytes**, encoded **cp874 / TIS-620**, line
  terminator **CRLF**, and the file ends with a trailing CRLF.
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

   Before production use, obtain the official *Krungsri CashLink Direct Credit
   upload file layout* + a fresh sample from the bank and validate/adjust the
   CSV accordingly.
