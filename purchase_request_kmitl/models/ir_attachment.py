from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    attachment_type = fields.Selection(
        [
            ("tor", "Specification (TOR)"),
            ("rfq", "Quotation"),
            ("etc", "Etc"),
        ],
        string="Attachment Type",
    )
    sequence = fields.Integer(string="Sequence")
