=========================
Receipt KMITL Exception
=========================

Adds ``base_exception`` blocking/warning rule checks on ``kmitl.receipt``
confirmation. When an active rule fails, confirming pops up a wizard listing
the outstanding exceptions; a manager may choose to ignore and proceed.

Configuration
=============

Manage exception rules from the generic ``exception.rule`` model (model
``kmitl.receipt``). One example rule ships disabled (``active=False``).
