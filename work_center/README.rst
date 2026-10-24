===========
Work Center
===========

.. |badge_devstat| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
   :target: https://odoo-community.org/page/development-status
   :alt: Beta
.. |badge_license| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :alt: LGPL-3

|badge_devstat| |badge_license|

A **work center** is a **station** (สถานี): a desk a document sits at while one
step of its handling is done, and leaves when that desk hands it on. A document
is at one station at a time. The station moves forward along a configured
**route**, or is **diverted** to another station of the same area, and every
move is written to an append-only **visit log** (สมุดเยี่ยม).

This module is the engine. It ships no document type and no work area of its
own: each **work area** (ระบบงาน — งานการเงิน, งานงบประมาณ, ใบขอเบิก …) arrives
as a bridge module that seeds the area, its stations and its route, puts the
mixin on its documents and adds the area's overview menu.

See ``CONTEXT.md`` for the glossary and ``docs/adr/`` for the decisions behind
the design (ADR-0002 supersedes the "owning unit" reading of ADR-0001).

How it works
============

* The pointer ``work_center_id`` only changes through the engine
  (``_work_center_enter``, ``_work_center_forward``, ``_work_center_divert``,
  ``_work_center_leave``), so the pointer and the visit log cannot disagree.
* The **standard route** is an ordered list of lines, each with one or more
  candidate stations. When a line has several (one per ส่วนงาน, say), the
  **routing rules** pick which takes the document. The route is read live: it
  is not copied onto the document.
* **Forward** hands the document to the next station. After a divert, "next"
  is the station after the last *on-route* station the document visited, read
  from the visit log. Forwarding out of the last station leaves the circuit.
* A station lists the **acts** it allows and requires. Forwarding without a
  required act needs a reason, which is logged together with the skipped acts.
  Diverting ignores required acts and needs a reason too.
* **Members** narrow who acts, they never grant: an act needs the role *and*,
  when the station has members, being one of them. A station without members
  is open to everyone holding the role. Members forward, divert and send back
  the documents at their station. Where nobody is responsible (the Unassigned
  card, or a station whose roles have no active holder) only the Station
  Administrators move the document.
* On arrival the visit freezes **who was responsible**. Who may act is still
  decided live, so the person who acted can be missing from that list: that is
  evidence the membership changed while the document was there, not a breach.
* One arrival Todo is scheduled per responsible user and closed when the
  document leaves.
* Each area has one synthetic **Unassigned** card counting the documents in
  the circuit that no rule placed at a station. **Counters** are configurable
  per area and counted with the viewer's own access rights.

Configuration
=============

Settings ▸ Stations (group *Station Administrator*):

#. **Work Areas** — seeded by the bridge modules, with the document models the
   area covers. A model may belong to only one area.
#. **Stations** — one per desk. Set an operating unit to keep the station at
   unit level; leave it empty for a central station. The *Acts* page lists the
   allowed acts, the required acts and the editable parts. A real station needs
   at least one allowed act or one member.
#. **Routes** — one active route per document model; each line holds the
   candidate stations.
#. **Station Routing Rules** — per document model, ordered; the first match
   chooses among the candidates of a line.
#. **Station Counters** — the numbers shown on every card of an area.
#. **Acts** — read-only: the code declares them. *Sync acts* runs the same
   reflection as a module upgrade.
#. **Visit Log** — every visit of every document.

Adding a document type
======================

.. code-block:: python

    class MyDocument(models.Model):
        _name = "my.document"  # mandatory with a list _inherit
        _inherit = [
            "my.document",
            "mail.thread",
            "mail.activity.mixin",
            "work.center.mixin",
        ]

        @api.model
        def _work_center_acts(self):
            return super()._work_center_acts() + [
                {
                    "code": "my.check",
                    "name": _lt("Check"),
                    "kind": "act",  # or "edit": a part of the document, never required
                    "group": "my_module.group_checker",
                    "sequence": 10,
                    "module": "my_module",
                }
            ]

        @api.model
        def _work_center_circuit_domain(self):
            return [("state", "=", "in_progress")]

#. Declare the acts in ``_work_center_acts``. The registry is reflected into
   records after an install or an upgrade; acts are archived, never deleted,
   when no longer declared.
#. Call ``_work_center_enter()`` when the document enters the circuit.
   After each act call ``_work_center_act_done(code)``, and guard it with
   ``_work_center_check_act(code)``; show it with ``_work_center_offers(code)``.
#. Implement the hooks: ``_work_center_on_arrival``,
   ``_work_center_on_departure``, ``_work_center_on_exit``,
   ``_work_center_on_send_back``, ``_work_center_act_applies``.
#. Embed the buttons ``action_work_center_forward`` / ``_divert`` /
   ``_send_back`` (pass ``{'expected_station': work_center_id}`` in the button
   context, so a move from a stale screen is refused) and the default tree of
   ``work_center_visit_ids``.
#. Add th.po entries for every mixin field under the consumer module's xmlid
   (``<consumer>.field_<model>__work_center_id`` …): Odoo 16 gives inherited
   fields the consumer's xmlid, so this module's own th.po never reaches them.
#. Under ``tier.validation``, whitelist only ``work_center_id``.

Credits
=======

Authors
-------

* Aginix Technologies
