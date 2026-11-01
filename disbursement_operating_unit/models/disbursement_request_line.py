from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="request_id.operating_unit_id",
        string="Operating Unit",
    )
