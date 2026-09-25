from odoo import fields, models


class MailNotification(models.Model):
    _inherit = "mail.notification"

    notification_type = fields.Selection(
        selection_add=[("workflow", "Workflow Event")],
        ondelete={"workflow": "cascade"},
    )
