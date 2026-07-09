===============
Base Assignment
===============

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
    :alt: License: LGPL-3
.. |badge3| image:: https://img.shields.io/badge/language-th-red.png
    :target: README.th.rst
    :alt: อ่านภาษาไทย

|badge1| |badge2| |badge3|

Reusable *Assigned Officer* mixin — auto-injects an alert (Assign to me /
Assign… / Unassign) above the sheet of any form whose model inherits it,
so consumers never touch view XML and the buttons stay out of the form's
own header workflow.

**Table of contents**

.. contents::
   :local:

Description
===========

Business documents often need to track a single **Assigned Officer**
(เจ้าหน้าที่ผู้รับผิดชอบ) — the person currently accountable for moving the
record forward. Without a shared foundation, every module that needs this
ends up copying the same three buttons (Assign to me / Assign… / Unassign),
the same reassignment wizard, and the same follow-up To-Do.

This module ships that foundation as a single ``AbstractModel``
(``assignment.mixin``) plus a QWeb template that Odoo auto-injects above
the ``<sheet>`` of any consuming form — mirroring the pattern used by
``base_tier_validation``. A consumer opts in with one ``_inherit`` line,
two group hooks, and the ``assigned_to`` field.

**Note:** This module provides no user-facing feature on its own. It is a
foundation for other modules to inherit from.

See ``procurement_assignment_kmitl`` (purchase.request, purchase.order) and
``disbursement`` (disbursement.request) in this repository as reference
implementations.

Configuration
=============

``base_assignment`` itself has no Settings UI. Each consumer owns its own
takeover toggle through the ``ir.config_parameter`` key returned by
``_assignment_takeover_param()``, and picks its own default with
``_assignment_takeover_default()``.

The toggle answers one question: **"When a document is already assigned to
someone, may another officer claim it via *Assign to me*?"**. When off,
takeover is a manager-only action (through *Assign…*). When on, any
officer in the user group can grab the document.

Reference implementations in this repository:

* ``procurement_assignment_kmitl`` — parameter
  ``procurement_assignment_kmitl.allow_takeover_assigned`` (default ``False``,
  conservative: manager-only reassignment). Exposed as a Settings toggle in
  the Purchase configuration page.

* ``disbursement`` — parameter ``disbursement.allow_takeover_assigned``
  (default ``True``, advisory: an officer may grab a mis-routed request out
  of the box).

Leave ``_assignment_takeover_param()`` returning ``None`` on your consumer
to drop the feature entirely — self-claim then works only on unassigned
records and any reassignment is manager-only.

Usage
=====

Adding assignment to a new document
-----------------------------------

#. Add ``base_assignment`` to your module's ``depends``.
#. Inherit ``assignment.mixin`` on the target model **together with**
   ``mail.activity.mixin`` (the mixin needs the chatter's ``activity_ids``
   and ``activity_schedule`` at runtime but does not inherit them itself —
   see the ADR for the MRO reason).
#. Declare the ``assigned_to`` field yourself so any existing field
   attributes (``tracking``, ``copy``, ``groups`` …) are preserved.
#. Set the two group hooks so the mixin knows who can claim and who can
   reassign.

Minimal consumer:

.. code-block:: python

    from odoo import fields, models


    class MyDoc(models.Model):
        _name = "my.doc"
        _inherit = ["my.doc", "mail.activity.mixin", "assignment.mixin"]

        _assign_user_group = "my_module.group_my_officer"
        _assign_manager_group = "my_module.group_my_manager"

        assigned_to = fields.Many2one(
            "res.users",
            string="Assigned Officer",
            tracking=True,
        )

That is enough to get an alert above the sheet with three buttons that all
respect the user / manager groups.

Extension points
----------------

Class attributes read at view-render time:

+-------------------------------------+-------------------+-----------------------------------------------------+
| Attribute                           | Default           | Purpose                                             |
+=====================================+===================+=====================================================+
| ``_assign_user_group``              | ``None`` (req'd)  | xmlid of the group that can self-claim              |
+-------------------------------------+-------------------+-----------------------------------------------------+
| ``_assign_manager_group``           | ``None`` (req'd)  | xmlid of the group that can reassign / unassign     |
+-------------------------------------+-------------------+-----------------------------------------------------+
| ``_assignment_manual_config``       | ``False``         | Set ``True`` to skip the auto-injected banner       |
+-------------------------------------+-------------------+-----------------------------------------------------+
| ``_assignment_alert_xpath``         | ``"/form/sheet"`` | Where in the form arch the alert is inserted        |
+-------------------------------------+-------------------+-----------------------------------------------------+
| ``_assignment_alert_position``      | ``"before"``      | ``"before"`` / ``"after"`` / ``"inside"``           |
+-------------------------------------+-------------------+-----------------------------------------------------+

Method hooks (override on the consumer, all optional):

+-----------------------------------------+---------------------------------------------------+
| Hook                                    | Default                                           |
+=========================================+===================================================+
| ``_assignment_activity_xmlid()``        | ``base_assignment.mail_activity_assignment``      |
+-----------------------------------------+---------------------------------------------------+
| ``_assignment_activity_summary()``      | ``_("Assigned as responsible officer")``          |
+-----------------------------------------+---------------------------------------------------+
| ``_assignment_takeover_param()``        | ``None`` — feature off                            |
+-----------------------------------------+---------------------------------------------------+
| ``_assignment_takeover_default()``      | ``False``                                         |
+-----------------------------------------+---------------------------------------------------+
| ``_assignment_on_assigned(new, old)``   | ``None`` — no-op lifecycle hook                   |
+-----------------------------------------+---------------------------------------------------+
| ``_assignment_on_unassigned(old)``      | ``None`` — no-op lifecycle hook                   |
+-----------------------------------------+---------------------------------------------------+

Moving the alert to another location
------------------------------------

Retarget the banner by overriding the two class attributes — no need to
override ``get_view``:

.. code-block:: python

    class MyDoc(models.Model):
        _inherit = ["my.doc", "mail.activity.mixin", "assignment.mixin"]
        _assignment_alert_xpath = "//div[@class='oe_title']"
        _assignment_alert_position = "before"

Disabling the auto-injected banner
----------------------------------

Set ``_assignment_manual_config = True`` when your form already renders its
own card, or has a non-standard structure the default xpath does not match.
The Python API (``action_assignment_assign_me``, ``action_assignment_unassign``,
``action_assignment_open_wizard``) is still available for header buttons or
RPC calls:

.. code-block:: python

    class MyDoc(models.Model):
        _inherit = ["my.doc", "mail.activity.mixin", "assignment.mixin"]
        _assignment_manual_config = True

Reacting to assignment changes
------------------------------

Override the lifecycle hooks to trigger side effects without rewriting the
action methods:

.. code-block:: python

    def _assignment_on_assigned(self, new_user, old_user):
        # Send email, transition a state, log, …
        self.message_post(
            body=_("Officer changed to %s") % new_user.display_name,
        )

    def _assignment_on_unassigned(self, old_user):
        self.message_post(body=_("Officer released."))

Both hooks fire on the record **after** the write, so ``self.assigned_to``
reflects the new value.

Customising the reassignment wizard
-----------------------------------

The generic wizard model is ``assign.officer.wizard``. To add fields
(e.g. a comment), inherit it in your module:

.. code-block:: python

    class AssignOfficerWizard(models.TransientModel):
        _inherit = "assign.officer.wizard"

        comment = fields.Text()

Known issues / Roadmap
======================

Known consumers
---------------

* ``procurement_assignment_kmitl`` — ``purchase.request`` and
  ``purchase.order``. Thin consumer: hook overrides only, no extra
  business rules on assignment.
* ``disbursement`` — ``disbursement.request``. Adds a routing-rule engine
  (``disbursement.assignment.rule``) on top of the mixin, plus a
  return-for-correction workflow specific to verification.

Companion module
----------------

* ``base_assignment_todo`` — data-only bridge. Tags the assignment
  activity type with a ``todo_category`` so notifications surface in the
  unified Todo inbox (``mail_activity_todo``).

Deferred / open work
--------------------

* **State gating.** A ``_assignment_allowed_states`` class attribute
  (mirroring ``base_tier_validation._state_from`` / ``_state_to``) is a
  natural next step so a consumer can declare "claiming is only valid in
  ``signed``". Today a consumer that needs this overrides
  ``action_assignment_assign_me`` and the wizard ``action_assign``.
* **Base tests.** The mixin has no direct unit tests; behaviour is covered
  by the two consumer test suites (``procurement_assignment_kmitl``,
  ``disbursement``). A dummy TransientModel test would let default hooks
  regress independently of the consumers.
* **Wizard field injection API.** Consumers can already
  ``_inherit = "assign.officer.wizard"`` to add fields (e.g. a mandatory
  comment). No dedicated API is provided.

Credits
=======

Authors
-------

* Aginix Technologies
* KMITL (King Mongkut's Institute of Technology Ladkrabang)

Contributors
------------

* Aginix Technologies
* KMITL (King Mongkut's Institute of Technology Ladkrabang)

Referenced work
---------------

* OCA ``base_tier_validation`` — the ``get_view`` template-injection pattern
* OCA ``base_state_leadtime`` — the ``base_*`` module naming convention
