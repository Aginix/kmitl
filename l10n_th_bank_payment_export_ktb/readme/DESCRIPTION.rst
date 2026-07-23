This module extends the functionality of Bank Export Payment to support a KTB.

Two export layouts (``Bank Export Format``) are provided:

* **KTB iPay** (``ktb_ipay``) — the legacy iPay layout.
* **KTB Direct Credit (H/D/T)** (``ktb_hdt``) — a fixed-width 128-byte
  Header / Detail / Trailer layout reconstructed from a real KMITL sample
  file. Use this format to match the file KTB actually returns.

Both layouts are written in the TIS-620/cp874 encoding required by the bank.

.. note::

   The ``ktb_hdt`` HEADER and DETAIL records are **validated byte-for-byte
   against the real KMITL sample** (128 bytes each; the detail amount width of
   13 was confirmed by reproducing the sample amount exactly). Only the TRAILER
   record's internal count/amount field breakdown could not be fully confirmed
   because the sample trailer reflects the untrimmed original batch; those
   fields are marked ``TODO`` in ``data/bank.export.format.line.csv`` and should
   be checked against a bank test upload.
