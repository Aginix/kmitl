====================
Readonly Management
====================

Centralized readonly field manager for Odoo 16. Instead of scattering
``attrs`` in XML views, administrators define readonly rules in one place
via a **Readonly Management** menu under Settings > Technical.

Features
========

* Define which fields on any model become readonly under configurable domain conditions
* Global gate condition per configuration (applies to all fields in the config)
* Per-field additional condition (AND-ed with the global gate)
* OR-merging when multiple configs target the same field
* Cache-safe: view cache is cleared automatically when rules are modified
* Applies only to form views (list/tree views are intentionally excluded)

Configuration
=============

1. Activate developer mode or log in as Settings Administrator
2. Go to **Settings > Technical > Readonly Management**
3. Create a new configuration and select the target model
4. Optionally set a **Global Gate Condition** (domain string)
5. Add field rules in the **Field Rules** tab

Domain Format
=============

Use standard Odoo domain syntax::

    [('state', 'in', ['submit', 'to_verify'])]
    [('is_locked', '=', True)]
    ['&', ('state', '=', 'done'), ('amount_total', '>', 0)]

Readonly Condition Logic
========================

+------------------+----------------+--------------+-----------------------------+
| Global Gate      | Always Readonly | Per-Field    | Result                      |
+==================+================+==============+=============================+
| Not set          | Yes            | (ignored)    | Always readonly             |
+------------------+----------------+--------------+-----------------------------+
| Set              | Yes            | (ignored)    | Readonly when gate matches  |
+------------------+----------------+--------------+-----------------------------+
| Not set          | No             | Set          | Readonly when field domain  |
+------------------+----------------+--------------+-----------------------------+
| Set              | No             | Set          | Readonly when gate AND field |
+------------------+----------------+--------------+-----------------------------+
| Set              | No             | Not set      | Readonly when gate matches  |
+------------------+----------------+--------------+-----------------------------+
| Not set          | No             | Not set      | (skipped, no rule)          |
+------------------+----------------+--------------+-----------------------------+

When multiple configurations target the same field on the same model, the
resulting readonly condition is OR-merged (field is readonly if **any** rule
applies).

Author: Aginix Technologies
License: AGPL-3
