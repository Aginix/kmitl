========================
Partner Rich Autocomplete
========================

The stock Many2one dropdown shows a single truncated line per option, which is
rarely enough to tell contacts apart while typing — two people share a name, a
company and its branch look identical.

This module ships a ``partner_autocomplete`` field widget: a drop-in
replacement for the standard Many2one that renders a rich, multi-line option
for each ``res.partner`` candidate while searching — name, type, VAT, address,
e-mail and phone — with a beautiful Owl template. It works both on a normal
form field and inside a Tree/list cell.

Usage
=====

Add ``widget="partner_autocomplete"`` to any Many2one that points at
``res.partner``::

    <field name="partner_id" widget="partner_autocomplete"/>

The same works inside a list view (the rich dropdown appears while the cell is
being edited)::

    <tree editable="bottom">
        <field name="partner_id" widget="partner_autocomplete"/>
    </tree>

Nothing else changes: selection, quick-create, "Search More…" and the external
link button all behave exactly like the standard Many2one — only the dropdown
options are enriched. Applied to a field whose comodel is not ``res.partner``
the widget silently degrades to the plain dropdown.

Extending the payload
======================

The dropdown content comes from
``res.partner.get_partner_autocomplete_info()``, which delegates to a handful
of per-record hooks. Override them to change what each option shows:

* ``_partner_autocomplete_type`` — the classification on the badge (defaults to
  the Individual/Company label).
* ``_partner_autocomplete_rows`` — the (label, value, icon) detail rows.
* ``_partner_autocomplete_address`` — the one-line address string.

See ``partner_type_kmitl_autocomplete`` for a minimal example that puts the
KMITL partner type on the badge in place of Individual/Company.
