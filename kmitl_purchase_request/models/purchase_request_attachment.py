from odoo import fields, models


class PurchaseRequestAttachment(models.Model):
    _name = "purchase.request.attachment"
    _description = "PurchaseRequestAttachment"

    name = fields.Char("Name")

    request_id = fields.Many2one("purchase.request", string="Purchase Request")
    attachment_type = fields.Selection(
        [
            ("tor", "Specification (TOR)"),
            ("rfq", "quotation"),
            ("etc", "etc"),
        ]
    )
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")
