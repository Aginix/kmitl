=========================
Receipt KMITL Exception
=========================

Adds ``base_exception`` blocking/warning rule checks on ``kmitl.receipt``
confirmation. When an active rule fails, confirming pops up a wizard listing
the outstanding exceptions; a manager may choose to ignore and proceed.

Configuration
=============

Manage exception rules from the generic ``exception.rule`` model (model
``kmitl.receipt``). Example rules ship disabled (``active=False``).

The **Configuration → Exception Rules** menu is restricted to users in the
``base_exception.group_exception_rule_manager`` group.
