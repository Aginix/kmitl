import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequestAttachment(models.Model):
    _name = "purchase.request.attachment"
    _description = "PurchaseRequestAttachment"

    name = fields.Char("Name")

    request_id = fields.Many2one("purchase.request", string="Purchase Request")
    attachment_type = fields.Selection(
        [
            ("tor", "ข้อกำหนดคุณลักษณะ (TOR)"),
            ("rfq", "ใบเสนอราคา"),
            ("etc", "อื่นๆ"),
        ]
    )
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")
