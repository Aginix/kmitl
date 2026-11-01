from odoo import fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    # Nothing fills this in any more: the purchase request no longer copies
    # its loan onto a ใบเบิก, and which loan a ใบเบิก clears is decided with
    # the clearing link (advance_payment ADR-0028/0029).
    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="Advance Payment",
    )
