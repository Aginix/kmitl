=====================================================
KMITL - Account Analytic Distribution Tree Selection
=====================================================

Adds a "Browse tree…" option to the analytic distribution widget's
autocomplete for plans marked as *Tree Selection* (``use_ztree_widget`` on
``account.analytic.plan``). It opens a dialog that lets users navigate the
plan's analytic accounts by parent/child (departments, funds, activities)
instead of only searching a flat list.

Enabled by default for the hierarchical dimensions from
``account_analytic_kmitl``: Departments, Funds and Activities. Any other
plan can opt in via the *Tree Selection* checkbox on its form view.

Credits
=======

Authors
~~~~~~~

* Aginix Technologies
