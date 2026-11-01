==========================
Web Domain Selector Record
==========================

In the standard Odoo 16 domain editor a condition on a relational field
(Many2one, Many2many, One2many) only offers a free text box, so a rule such as
"the user is Administrator" has to be written as ``User = 1`` after looking up
the id.

This module replaces that text box with a searchable record picker:

* ``=`` / ``!=`` / ``child of``: pick one record by name.
* ``in`` / ``not in``: pick several records, shown as tags.
* Users, partners and employees show their avatar next to the name.
* ``contains`` / ``not contains`` still use a text box.

Saved domains show the record names (e.g. ``User = "Administrator"``) instead of
their ids. The stored domain is unchanged and still holds the ids, so every
existing domain widget (record rules, buddies, work center rules, ...) benefits
without any change.
