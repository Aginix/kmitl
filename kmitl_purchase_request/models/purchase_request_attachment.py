from odoo import fields, models


class PurchaseRequestAttachment(models.Model):
    _name = "purchase.request.attachment"
    _description = "PurchaseRequestAttachment"

    request_id = fields.Many2one("purchase.request", string="Purchase Request")
    attachment_type = fields.Selection(
        [
            ("tor", "Specification (TOR)"),
            ("rfq", "quotation"),
            ("etc", "etc"),
        ],
    default="tor"
    )
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True, filename="file_name")
    description = fields.Char(string="Description")
