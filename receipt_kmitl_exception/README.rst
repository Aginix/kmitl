=========================
Receipt KMITL Exception
=========================

Adds ``base_exception`` rule checks on ``kmitl.receipt``. Rules are evaluated
whenever a receipt is created or edited (the receipt has no confirm step —
numbers are minted at creation). A failing **blocking** rule (``is_blocking``)
prevents the receipt from being saved; non-blocking rules are still detected
and stored on the record for visibility but do not block saving.

Configuration
=============

Manage exception rules from the generic ``exception.rule`` model (model
``kmitl.receipt``). Example rules ship disabled (``active=False``).

The **Configuration → Exception Rules** menu is restricted to users in the
``base_exception.group_exception_rule_manager`` group.
