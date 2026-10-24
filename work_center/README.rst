===========
Work Center
===========

.. |badge_devstat| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
   :target: https://odoo-community.org/page/development-status
   :alt: Beta
.. |badge_license| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :alt: LGPL-3

|badge_devstat| |badge_license|

A **work center** (ศูนย์งาน) is the unit that owns and tracks a document — whose
work it is and who follows it up, e.g. ศูนย์งานภาควิชาไฟฟ้า or ศูนย์งานการเงินกลาง.
It is stamped on the document itself, so the unit never loses sight of its own
paperwork.

This module is the core. It ships no document type and no work area of its own:
each **work area** (ระบบงาน — งานการเงิน, งานงบประมาณ …) arrives as a bridge module
that seeds the area, puts the mixin on its documents and adds the area's overview
menu.

See ``CONTEXT.md`` for the glossary and ``docs/adr/0001-*`` for the decision
behind the design.

How it works
============

* **Routing rules** (กฎการจัดเข้าศูนย์งาน) are an ordered list per document model:
  the first rule whose condition matches a **draft** document puts it on that
  work center. Rules of a work center that has an operating unit implicitly also
  require that operating unit.
* Once the document leaves draft the value is **sticky** — rules never move it
  again, but anyone who may write the document can still change it by hand.
* A work center picked by hand that differs from the rule result **pins** the
  document; clearing the field un-pins it and, while draft, routes it again.
* Each area has one synthetic **Unassigned** card counting the documents no rule
  matched. Those documents are never blocked; they just wait there.
* **Counters** are configurable per area and counted with the viewer's own
  access rights, so every number equals the list it opens.
* **Membership** is focus only: it puts a card on someone's overview and drives
  the "My Work Centers" filter. It grants no access and restricts no action —
  operating unit record rules and per-state rights stay authoritative.

Configuration
=============

Settings ▸ Work Center (group *Work Center Administrator*):

#. **Work Areas** — seeded by the bridge modules, together with the document
   models the area covers. A model may belong to only one area.
#. **Work Centers** — one per unit. Set an operating unit to keep the work
   center at unit level; leave it empty for a central work center.
#. **Work Center Routing Rules** — per document model, ordered; first match wins.
#. **Work Center Counters** — the numbers shown on every card of an area.

Adding a document type
======================

.. code-block:: python

    class MyDocument(models.Model):
        _name = "my.document"
        _inherit = ["my.document", "work.center.mixin"]

        @api.model
        def _work_center_routing_fields(self):
            # Rules are re-evaluated when one of these changes.
            return super()._work_center_routing_fields() + ["department_id"]

Override ``_work_center_is_routable`` when "draft" is not ``state == 'draft'``,
and whitelist ``work_center_id`` / ``work_center_manual`` in
``_get_under_validation_exceptions`` on models under ``tier.validation``.

Credits
=======

Authors
-------

* Aginix Technologies
