================================
Receipt KMITL Operating Unit
================================

Adds Operating Unit row-level access control to ``kmitl.receipt`` and
``kmitl.receipt.remittance``, following the repo-wide ``*_operating_unit``
pattern. Also stamps ``operating_unit_id`` onto the journal entries created
when a receipt is posted.

See ``receipt_kmitl_operating_unit_access_all`` for the companion "see all
OUs" group.
