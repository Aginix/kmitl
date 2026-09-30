=====================================================
KMITL - Account Analytic Distribution Tree Selection
=====================================================

For plans marked as *Tree Selection* (``use_ztree_widget`` on
``account.analytic.plan``), the analytic distribution widget's autocomplete
field renders as an expandable ``app_web_widget_ztree`` tree (parent/child)
instead of a flat search list, so departments/funds/activities can be
browsed and picked directly in the field.

Enabled by default for the hierarchical dimensions from
``account_analytic_kmitl``: Departments, Funds and Activities. Any other
plan can opt in via the *Tree Selection* checkbox on its form view.

Credits
=======

Authors
~~~~~~~

* Aginix Technologies
