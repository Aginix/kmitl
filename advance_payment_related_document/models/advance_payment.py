from odoo import fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    related_document_ids = fields.One2many(
        comodel_name="advance.payment.related.document",
        inverse_name="advance_payment_id",
        string="เอกสารอ้างอิงเพิ่มเติม",
        copy=False,
    )
