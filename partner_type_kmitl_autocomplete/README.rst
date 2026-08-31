==========================================
Partner Rich Autocomplete: KMITL Partner Type
==========================================

Bridge between ``agx_partner_autocomplete`` and ``partner_type_kmitl``.

On its own the ``agx_partner_many2one`` widget shows the generic
Individual/Company classification on each dropdown option's badge. With this
module installed the badge shows the contact's KMITL **Partner Type**
(``partner_type_id``) instead, falling back to Individual/Company only when a
contact has no type assigned yet.

It overrides a single hook — ``_partner_autocomplete_type`` — so the partner
type flows to both the dropdown badge and the selected-value subtitle, and
inherits the widget's "Search More…" list to replace the Individual/Company
column with the KMITL partner type. The option's leading icon follows the
KMITL type automatically too, since it's derived from ``company_type`` and
this module writes to that same field — no code needed here. Nothing else is
touched.
