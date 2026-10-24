from odoo import fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    change_request_id = fields.Many2one(
        comodel_name="change.request",
        index=True,
        ondelete="cascade",
        help="The Change request this activity asks to answer or to check.",
    )
