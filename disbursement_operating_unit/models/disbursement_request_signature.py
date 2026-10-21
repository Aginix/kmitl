from odoo import fields, models


class DisbursementRequestSignature(models.Model):
    _inherit = "disbursement.request.signature"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="request_id.operating_unit_id",
        string="Operating Unit",
    )
