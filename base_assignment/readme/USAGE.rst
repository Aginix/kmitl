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
