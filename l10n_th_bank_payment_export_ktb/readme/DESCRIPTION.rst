This module extends the functionality of Bank Export Payment to support a KTB.

Two export layouts (``Bank Export Format``) are provided:

* **KTB iPay** (``ktb_ipay``) — the legacy iPay layout.
* **KTB Direct Credit (H/D/T)** (``ktb_hdt``) — a fixed-width 128-byte
  Header / Detail / Trailer layout reconstructed from a real KMITL sample
  file. Use this format to match the file KTB actually returns.

Both layouts are written in the TIS-620/cp874 encoding required by the bank.

.. note::

   The ``ktb_hdt`` layout was reconstructed from a masked/trimmed sample.
   A few detail/trailer field widths (notably the detail amount width and the
   trailer count/amount breakdown) still need to be confirmed against the
   official KTB file-format specification. Fields awaiting confirmation are
   marked with ``TODO`` in ``data/bank.export.format.line.csv``.
