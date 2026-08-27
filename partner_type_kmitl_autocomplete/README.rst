==========================================
Partner Rich Autocomplete: KMITL Partner Type
==========================================

Bridge between ``agx_partner_autocomplete`` and ``partner_type_kmitl``.

On its own the ``partner_autocomplete`` widget shows the generic
Individual/Company classification on each dropdown option's badge. With this
module installed the badge shows the contact's KMITL **Partner Type**
(``partner_type_id``) instead, falling back to Individual/Company only when a
contact has no type assigned yet.

It overrides a single hook — ``_partner_autocomplete_type`` — and changes
nothing else: the widget, its views and the rest of the dropdown payload are
untouched.
