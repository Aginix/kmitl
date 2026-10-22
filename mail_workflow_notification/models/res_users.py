from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    workflow_notification_enabled = fields.Boolean(
        string="Workflow Notifications",
        default=True,
        help="Receive systray notifications when workflow documents you created change state. "
        "Disable here to stop receiving these events.",
    )

    # Allow users to edit their own preference without needing Settings access.
    SELF_WRITEABLE_FIELDS = list(models.Model.SELF_WRITEABLE_FIELDS) + [
        "workflow_notification_enabled"
    ]
