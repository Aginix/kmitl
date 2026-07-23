===================================
Thai Localization - Bank Payment Export BAY
===================================

Bank payment file export for **Bank of Ayudhya / Krungsri (BAY / AYUDTHBK)**,
built on top of ``l10n_th_bank_payment_export_format``.

Adds ``BAY`` as an option on ``bank.payment.export`` and ships a fixed-width
file layout (``BAY CashLink``) for exporting vendor payments.

.. IMPORTANT::

   **The file layout in** ``data/bank.export.format.line.csv`` **is a DRAFT.**

   Krungsri does not publish the direct-credit upload byte specification openly.
   The shipped layout reproduces Krungsri's confirmed CashLink conventions
   (256-byte records, ``^`` field separators, ``H``/``D`` record types,
   ``DDMM20YY`` dates, ``9(11)V99`` satang amounts, bank code ``025``) but the
   field order/positions are modelled on the KTB direct-credit layout, **not**
   on an official CashLink direct-credit spec (the only public Krungsri layout
   found was an incoming bill-payment statement, not the outgoing upload).

   Before production use you **must** obtain the official *Krungsri CashLink
   Direct Credit upload file layout* + a sample file from the bank, then
   validate/adjust this CSV accordingly.
